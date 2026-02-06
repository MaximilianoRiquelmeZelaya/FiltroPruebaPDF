import streamlit as st
import pandas as pd
import re
from collections import Counter
import io
import openpyxl
import PyPDF2

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Filtro de Pallets PDF", page_icon="📊", layout="wide")

# --- LISTA DE CAMPOS PREFERIDOS (Para sugerir por defecto) ---
CAMPOS_SUGERIDOS = [
    "Contenedor - Folio", "Folio", "N° Semana", "Fecha Análisis", "Fecha Etiqueta", "Analista", 
    "Turno", "Lote", "Cliente", "Tipo de producto", "Condición GF/convencional", 
    "Espesor inferior", "Espesor superrior", "% Humedad inferior FT", "% Humedad superior FT", 
    "Hora", "Cantidad sacos/maxisaco", "Peso saco/maxisaco", "Kilos producidos", "Humedad", 
    "Temperatura producto", "Enzimática", "Peso hectolitro", "Filamentos", "Cáscaras", 
    "Semillas Extrañas", "Gelatinas", "Quemadas", "Granos sin aplastar", 
    "Granos Parcialmente Aplastados", "Trigos", "Cebada", "Centeno", "Materiales extraños", 
    "Retención malla 7", "Bajo malla 25", "Espesor 1", "Espesor 2", "Espesor 3", 
    "Espesor 4", "Espesor 5", "Espesor 6", "Espesor 7", "Espesor 8", "Espesor 9", 
    "Espesor 10", "Promedio espesor", "Sacos detector de metales", 
    "Verificación de patrones PCC", "ESTADO", "Motivo Retención"
]

# --- FUNCIONES AUXILIARES ---
def extraer_info_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    texto_completo = ""
    for page in reader.pages:
        texto_completo += page.extract_text() + "\n"
    match_contenedor = re.search(r"([A-Z]{4}\d{6,7}(?:-\d)?)", texto_completo)
    contenedor_encontrado = match_contenedor.group(1) if match_contenedor else None
    return contenedor_encontrado, texto_completo

def detectar_patron_inteligente(texto_sucio):
    texto_sin_fechas = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', texto_sucio)
    candidatos_sanos = re.findall(r'\b\d{10,14}\b', texto_sin_fechas)
    if not candidatos_sanos: return None, None
    
    prefijos = [c[:4] for c in candidatos_sanos]
    sufijos = [c[-2:] for c in candidatos_sanos]
    comun_prefix = Counter(prefijos).most_common(1)[0][0]
    comun_suffix = Counter(sufijos).most_common(1)[0][0]
    
    patron_generado = rf"{comun_prefix}([\d\s]+?){comun_suffix}"
    return patron_generado, len(candidatos_sanos)

# --- INTERFAZ DE USUARIO ---
st.title("📊 Generador de Reportes de Hojuela (Vía PDF)")
st.markdown("Sube el archivo Excel maestro y el PDF de transporte para cruzar la información.")

# 1. CARGA DE ARCHIVOS
col1, col2 = st.columns(2)
with col1:
    archivo_maestro = st.file_uploader("1️⃣ Cargar Excel Maestro", type=["xlsx"])
with col2:
    archivo_pdf = st.file_uploader("2️⃣ Cargar PDF de Transporte", type=["pdf"])

# 2. CONFIGURACIÓN DINÁMICA
nombre_hoja_seleccionada = None
columnas_seleccionadas = []

if archivo_maestro:
    try:
        excel_file = pd.ExcelFile(archivo_maestro)
        nombres_hojas = excel_file.sheet_names
        
        st.divider()
        st.subheader("⚙️ Configuración del Reporte")
        c1, c2 = st.columns([1, 2])
        
        with c1:
            # A) SELECCIÓN DE HOJA
            nombre_hoja_seleccionada = st.selectbox(
                "Selecciona la Hoja de Trabajo:",
                nombres_hojas,
                index=0,
                help="Elige la pestaña del Excel donde están los datos."
            )
        
        # B) LECTURA DE COLUMNAS DE LA HOJA SELECCIONADA
        # Leemos solo los encabezados (nrows=0) para ser rápidos
        if nombre_hoja_seleccionada:
            df_cols = pd.read_excel(
                archivo_maestro, 
                sheet_name=nombre_hoja_seleccionada, 
                header=1, 
                nrows=0
            )
            columnas_reales = df_cols.columns.tolist()
            
            # Calculamos cuáles de nuestras columnas sugeridas existen realmente en esta hoja
            defaults_validos = [c for c in CAMPOS_SUGERIDOS if c in columnas_reales]
            
            with c2:
                # C) SELECTOR DE COLUMNAS ACTUALIZADO
                columnas_seleccionadas = st.multiselect(
                    f"Selecciona las columnas de '{nombre_hoja_seleccionada}':",
                    options=columnas_reales,    # Opciones reales de la hoja
                    default=defaults_validos,   # Preselección inteligente
                    help="Estas son las columnas que se encontraron en la hoja seleccionada."
                )
                
    except Exception as e:
        st.error(f"Error al leer la estructura del Excel: {e}")

# --- BOTÓN DE PROCESAR ---
st.divider()
if st.button("🚀 Procesar y Generar Excel", type="primary"):
    if not archivo_maestro:
        st.error("⚠️ Falta el archivo Excel maestro.")
    elif not archivo_pdf:
        st.error("⚠️ Falta el archivo PDF de transporte.")
    elif not nombre_hoja_seleccionada:
        st.error("⚠️ No se ha seleccionado una hoja del Excel.")
    elif not columnas_seleccionadas:
        st.error("⚠️ Debes seleccionar al menos una columna para el reporte.")
    else:
        try:
            # A) Leer PDF
            with st.spinner('Extrayendo información del PDF...'):
                contenedor, pallets_texto = extraer_info_pdf(archivo_pdf)
            
            if not contenedor:
                st.warning("⚠️ No se encontró contenedor válido. Se usará 'DESCONOCIDO'.")
                contenedor = "DESCONOCIDO"
            else:
                st.info(f"📦 Contenedor detectado: **{contenedor}**")

            # B) Leer Excel Maestro (Completo esta vez)
            with st.spinner(f'Leyendo datos de "{nombre_hoja_seleccionada}"...'):
                df_hojuelaavena = pd.read_excel(archivo_maestro, sheet_name=nombre_hoja_seleccionada, header=1)
            
            # C) Detectar Patrón
            patron, num_candidatos_sanos = detectar_patron_inteligente(pallets_texto)
            
            if patron:
                st.success(f"✅ Patrón detectado (Basado en {num_candidatos_sanos} lecturas limpias).")
                
                # Extracción y limpieza
                hallazgos_crudos = re.findall(patron, pallets_texto)
                lista_limpia = [x.replace(" ", "").replace("\n", "") for x in hallazgos_crudos]
                
                lista_int = []
                for x in lista_limpia:
                    if x.isdigit():
                        lista_int.append(int(x))
                lista_int.sort()
                
                filas_encontradas = []
                coincidencias = 0
                barra = st.progress(0)
                total_items = len(lista_int)

                if total_items == 0:
                     st.warning("Se detectó el patrón pero no se extrajeron números válidos.")
                else:
                    for idx, folio_buscado in enumerate(lista_int):
                        # Validación de existencia de columna Folio
                        if "Folio" in df_hojuelaavena.columns:
                            fila_match = df_hojuelaavena[df_hojuelaavena["Folio"] == folio_buscado]
                            if not fila_match.empty:
                                coincidencias += 1
                                datos_fila = fila_match.iloc[0].to_dict()
                                datos_fila["Contenedor - Folio"] = f"{contenedor} - {folio_buscado}"
                                filas_encontradas.append(datos_fila)
                        else:
                            st.error(f"La hoja '{nombre_hoja_seleccionada}' no tiene una columna llamada 'Folio'.")
                            break
                        
                        barra.progress((idx + 1) / total_items)
                    
                    st.write(f"**Resultados:** {coincidencias} coincidencias de {total_items} códigos buscados.")

                    if filas_encontradas:
                        df_exportar = pd.DataFrame(filas_encontradas)
                        
                        # Usar SOLO las columnas seleccionadas por el usuario
                        df_final = df_exportar.reindex(columns=columnas_seleccionadas)
                        
                        st.subheader("📋 Vista Previa de Datos")
                        st.dataframe(df_final)

                        # Cálculo de Promedios (Dinámico)
                        st.subheader("📈 Promedios")
                        try:
                            # Detectar columnas numéricas dentro de la selección
                            # Buscamos columnas típicas de calidad para promediar
                            # O simplemente promediamos todo lo que sea numérico en la selección
                            
                            # Filtramos las columnas seleccionadas que sean numéricas
                            df_numerico = df_final.select_dtypes(include=['float64', 'int64'])
                            
                            # Opcional: Filtrar solo si el nombre contiene ciertas palabras clave si prefieres ser estricto
                            # Palabras clave: Humedad, Espesor, Peso, etc.
                            keywords = ["Humedad", "Espesor", "Peso"]
                            cols_a_promediar = [c for c in df_numerico.columns if any(k in c for k in keywords)]
                            
                            if cols_a_promediar:
                                df_rango = df_final[cols_a_promediar]
                                promedios = df_rango.mean()
                                promedios_validos = promedios.dropna()
                                
                                if not promedios_validos.empty:
                                    st.dataframe(promedios_validos.to_frame(name="Promedio").round(2).T)
                                else:
                                    st.info("No hay datos suficientes para calcular promedios.")
                            else:
                                st.info("No se seleccionaron columnas de Humedad o Espesor para promediar.")
                                
                        except Exception as e:
                            st.warning(f"No se pudieron calcular promedios: {e}")

                        # Generar Excel
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_final.to_excel(writer, index=False, sheet_name='Reporte')
                            worksheet = writer.sheets['Reporte']
                            worksheet.auto_filter.ref = worksheet.dimensions
                            worksheet.freeze_panes = 'B2'
                            
                            for column in worksheet.columns:
                                max_length = 0
                                column_letter = column[0].column_letter
                                for cell in column:
                                    try:
                                        if len(str(cell.value)) > max_length:
                                            max_length = len(str(cell.value))
                                    except: pass
                                adjusted_width = (max_length + 2)
                                worksheet.column_dimensions[column_letter].width = adjusted_width
                        
                        st.download_button(
                            label="📥 Descargar Reporte Excel",
                            data=output.getvalue(),
                            file_name=f"Reporte_Contenedor_{contenedor}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.warning("No se encontraron coincidencias en la hoja seleccionada.")
            else:
                st.error("No se pudieron detectar pallets válidos en el PDF.")
                
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
