import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from fpdf import FPDF

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

    for _, row in df_ej.iterrows():
        nombre = f"{row['id_ejercicio']} - {row['nombre']} ({row['duracion_min']} min)"
        fase = f"Fase: {row['fase_juego']} | Intensidad: {row['intensidad']}"
        objetivo = f"Objetivo: {row['objetivo_principal']}"
        espacio = f"Espacio: {row.get('espacio', '')}"
        jugadores = f"Jugadores: {row.get('jugadores_min', '')} - {row.get('jugadores_max', '')}"

        pdf.set_font("Arial", "B", 12)
        pdf.multi_cell(0, 7, nombre)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, fase)
        pdf.multi_cell(0, 6, objetivo)
        if espacio.strip():
            pdf.multi_cell(0, 6, espacio)
        if jugadores.strip():
            pdf.multi_cell(0, 6, jugadores)

        desc = str(row.get("descripcion_paso_a_paso", "") or "").strip()
        if desc:
            pdf.set_font("Arial", "I", 10)
            pdf.multi_cell(0, 5, f"Descripción: {desc}")

        coaching = str(row.get("coaching_points", "") or "").strip()
        if coaching:
            pdf.set_font("Arial", "I", 10)
            pdf.multi_cell(0, 5, f"Coaching points: {coaching}")

        pdf.ln(3)
        total_minutos += int(row.get("duracion_min", 0))

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, f"Duración total estimada: {total_minutos} minutos", ln=True)

    # Devolver bytes del PDF
    pdf_bytes = pdf.output(dest="S").encode("latin-1", "ignore")
    return pdf_bytes

# ===============================================
# 7️⃣ Botón para generar y descargar PDF
# ===============================================
st.subheader("📄 Exportar sesión")

if len(seleccionados) == 0:
    st.info("Seleccioná al menos un ejercicio en la tabla para habilitar el PDF.")
else:
    if st.button("📄 Generar PDF con ejercicios seleccionados"):
        pdf_bytes = generar_pdf(seleccionados)
        st.success("✅ PDF generado. Podés descargarlo abajo.")
        st.download_button(
            "⬇️ Descargar plan de entrenamiento (PDF)",
            data=pdf_bytes,
            file_name="plan_entrenamiento_LRC.pdf",
            mime="application/pdf",
        )
