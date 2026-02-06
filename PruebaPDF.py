import streamlit as st
import pandas as pd
import re
from collections import Counter
import io
import openpyxl
import PyPDF2

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Filtro de Pallets PDF", page_icon="📊", layout="wide")

# --- LISTA DE CAMPOS ---
campos = [
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

# --- FUNCIÓN DE EXTRACCIÓN DE PDF ---
def extraer_info_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    texto_completo = ""
    for page in reader.pages:
        texto_completo += page.extract_text() + "\n"
    
    # 1. Buscar Contenedor (Patrón: 4 letras mayúsculas, 6-7 dígitos, opcional guion y dígito)
    match_contenedor = re.search(r"([A-Z]{4}\d{6,7}(?:-\d)?)", texto_completo)
    contenedor_encontrado = match_contenedor.group(1) if match_contenedor else None
    
    return contenedor_encontrado, texto_completo

# --- FUNCIÓN DE DETECCIÓN INTELIGENTE ---
def detectar_patron_inteligente(texto_sucio):
    texto_sin_fechas = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4}', '', texto_sucio)
    candidatos = re.findall(r'\b\d{10,14}\b', texto_sin_fechas)
    
    if not candidatos:
        return None, None
    
    prefijos = [c[:4] for c in candidatos]
    sufijos = [c[-2:] for c in candidatos]

    comun_prefix = Counter(prefijos).most_common(1)[0][0]
    comun_suffix = Counter(sufijos).most_common(1)[0][0]

    patron_generado = rf"{comun_prefix
