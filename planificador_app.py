import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from fpdf import FPDF
import math
from fpdf.errors import FPDFException

# ===============================================
# 1️⃣ Configuración Streamlit
# ===============================================
st.set_page_config(page_title="Planificador LRC", page_icon="🏉", layout="wide")

st.title("🏉 Planificador Luján Rugby Club – Plantel Superior")
st.caption("Filtrá ejercicios, seleccioná los que quieras y generá un PDF con la sesión.")

# ===============================================
# 2️⃣ Leer secrets (SHEET_ID y credenciales)
# ===============================================
try:
    secrets = st.secrets
    SHEET_ID = secrets["SHEET_ID"]
    WORKSHEET = secrets["WORKSHEET"]
    GOOGLE_CREDENTIALS = json.loads(secrets["GOOGLE_CREDENTIALS"])
except Exception as e:
    st.error(f"❌ Error al leer st.secrets: {e}")
    st.stop()

# ===============================================
# 3️⃣ Conexión segura a Google Sheets
# ===============================================
@st.cache_data(show_spinner=True)
def cargar_datos():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    return df

df = cargar_datos()

if df.empty:
    st.warning("⚠️ No se encontraron datos en el repositorio o no se pudo conectar al Sheet.")
    st.stop()

# ===============================================
# 4️⃣ Filtros en sidebar
# ===============================================
st.sidebar.header("🎛 Filtros")

fases = ["(Todas)"] + sorted(df["fase_juego"].dropna().unique().tolist())
intensidades = ["(Todas)"] + sorted(df["intensidad"].dropna().unique().tolist())
subtemas = ["(Todos)"] + sorted(df["subtema"].dropna().unique().tolist())

fase_sel = st.sidebar.selectbox("Fase de juego", fases)
intensidad_sel = st.sidebar.selectbox("Intensidad", intensidades)
subtema_sel = st.sidebar.selectbox("Subtema", subtemas)
duracion_max = st.sidebar.slider("Duración máxima por ejercicio (min)", 5, 40, 20)

df_filtrado = df.copy()

if fase_sel != "(Todas)":
    df_filtrado = df_filtrado[df_filtrado["fase_juego"] == fase_sel]

if intensidad_sel != "(Todas)":
    df_filtrado = df_filtrado[df_filtrado["intensidad"] == intensidad_sel]

if subtema_sel != "(Todos)":
    df_filtrado = df_filtrado[df_filtrado["subtema"] == subtema_sel]

df_filtrado = df_filtrado[df_filtrado["duracion_min"] <= duracion_max]

st.subheader("📋 Ejercicios filtrados")
st.write(f"Se encontraron **{len(df_filtrado)}** ejercicios con los filtros actuales.")

if df_filtrado.empty:
    st.warning("Ajustá los filtros para ver ejercicios.")
    st.stop()

# ===============================================
# 5️⃣ Selección de ejercicios con data_editor
# ===============================================
df_seleccion = df_filtrado.copy()
if "Seleccionar" not in df_seleccion.columns:
    df_seleccion["Seleccionar"] = False

st.markdown("Marcá la columna **Seleccionar** en los ejercicios que quieras incluir en el PDF.")

edited_df = st.data_editor(
    df_seleccion,
    hide_index=True,
    column_config={
        "Seleccionar": st.column_config.CheckboxColumn("Seleccionar"),
        "id_ejercicio": "ID",
        "nombre": "Nombre",
        "fase_juego": "Fase",
        "subtema": "Subtema",
        "duracion_min": "Duración (min)",
        "intensidad": "Intensidad",
    },
    disabled=[],
    num_rows="dynamic",
)

seleccionados = edited_df[edited_df["Seleccionar"] == True]

st.write(f"✅ Ejercicios seleccionados: **{len(seleccionados)}**")



def limpiar_texto_pdf(texto, max_word_len=40):
    """Normaliza texto para el PDF: quita saltos raros y parte palabras MUY largas."""
    if texto is None or (isinstance(texto, float) and math.isnan(texto)):
        return ""
    if not isinstance(texto, str):
        texto = str(texto)

    # Quitar saltos de línea y caracteres raros
    texto = texto.replace("\r", " ").replace("\n", " ")

    # Dividir en palabras y partir las que sean demasiado largas
    palabras = texto.split(" ")
    palabras_limpias = []
    for w in palabras:
        if len(w) > max_word_len:
            for i in range(0, len(w), max_word_len):
                palabras_limpias.append(w[i:i+max_word_len])
        else:
            palabras_limpias.append(w)

    return " ".join(palabras_limpias)


def safe_multicell(pdf, w, h, txt):
    """Wrapper para multi_cell que nunca revienta aunque el texto sea raro."""
    txt = limpiar_texto_pdf(txt)
    if not txt.strip():
        return
    try:
        pdf.multi_cell(w, h, txt)
    except FPDFException:
        # Si aún así falla, truncamos fuerte para evitar romper el PDF
        pdf.multi_cell(w, h, txt[:80])

# ===============================================
# 6️⃣ Función para generar PDF
# ===============================================
def generar_pdf(df_ej):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Plan de Entrenamiento - Lujan Rugby Club", ln=True)
    pdf.ln(4)

    total_minutos = 0
    contenido = df_ej.copy()

    for _, row in contenido.iterrows():
        nombre = f"{row['id_ejercicio']} - {row['nombre']} ({row['duracion_min']} min)"
        fase = f"Fase: {row['fase_juego']} | Intensidad: {row['intensidad']}"
        objetivo = f"Objetivo: {row['objetivo_principal']}"
        espacio = f"Espacio: {row.get('espacio', '')}"
        jugadores = f"Jugadores: {row.get('jugadores_min', '')} - {row.get('jugadores_max', '')}"

        # Título del ejercicio
        pdf.set_font("Arial", "B", 12)
        safe_multicell(pdf, 180, 7, nombre)

        pdf.set_font("Arial", "", 11)
        safe_multicell(pdf, 180, 6, fase)
        safe_multicell(pdf, 180, 6, objetivo)

        esp_limpio = limpiar_texto_pdf(espacio)
        if esp_limpio:
            safe_multicell(pdf, 180, 6, esp_limpio)

        jug_limpio = limpiar_texto_pdf(jugadores)
        if jug_limpio:
            safe_multicell(pdf, 180, 6, jug_limpio)

        desc = limpiar_texto_pdf(row.get("descripcion_paso_a_paso", ""))
        if desc:
            pdf.set_font("Arial", "I", 10)
            safe_multicell(pdf, 180, 5, f"Descripción: {desc}")

        coaching = limpiar_texto_pdf(row.get("coaching_points", ""))
        if coaching:
            pdf.set_font("Arial", "I", 10)
            safe_multicell(pdf, 180, 5, f"Coaching points: {coaching}")

        pdf.ln(3)

        try:
            total_minutos += int(row.get("duracion_min", 0))
        except Exception:
            pass

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, f"Duración total estimada: {total_minutos} minutos", ln=True)

    # Devolver bytes del PDF
    pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
    return pdf_bytes