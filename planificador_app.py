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
    """Wrapper inteligente para multi_cell con ancho adaptativo y protección total."""
    txt = limpiar_texto_pdf(txt)
    if not txt.strip():
        return

    # Ancho útil real (dinámico)
    page_width = pdf.w
    left_margin = pdf.l_margin
    right_margin = pdf.r_margin
    max_width = page_width - left_margin - right_margin

    # Si no se define un ancho, usar el total disponible
    if not w or w == 0:
        w = max_width

    # Intentar imprimir normalmente
    try:
        pdf.multi_cell(w, h, txt)
    except Exception:
        # Si FPDF falla, dividimos manualmente las líneas
        palabras = txt.split(" ")
        linea = ""
        for palabra in palabras:
            # Medir la longitud de la palabra en mm
            palabra_ancho = pdf.get_string_width(palabra + " ")

            # Si la línea actual + palabra excede el ancho, imprimir y bajar una línea
            if pdf.get_string_width(linea + palabra + " ") > w:
                pdf.multi_cell(w, h, linea.strip())
                linea = palabra + " "
            else:
                linea += palabra + " "

        # Imprimir la última línea si quedó algo pendiente
        if linea.strip():
            pdf.multi_cell(w, h, linea.strip())



# ===============================================
# 6️⃣ Función para generar PDF
# ===============================================
def generar_pdf(df_ej):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)

    pdf.add_page()

    # ============================
    # Encabezado
    # ============================
    pdf.set_font("Arial", "B", 16)
    safe_multicell(pdf, 0, 10, "Plan de Entrenamiento - Luján Rugby Club")
    pdf.ln(4)

    contenido = df_ej.copy()

    # Resumen general
    try:
        total_minutos = int(contenido["duracion_min"].fillna(0).sum())
    except Exception:
        total_minutos = 0

    pdf.set_font("Arial", "", 11)
    safe_multicell(pdf, 0, 6, f"Cantidad de ejercicios: {len(contenido)}")
    safe_multicell(pdf, 0, 6, f"Duración total estimada: {total_minutos} minutos")
    pdf.ln(6)

    # ============================
    # Ejercicio por ejercicio
    # ============================
    for idx, (_, row) in enumerate(contenido.iterrows(), start=1):

        # Separador entre ejercicios
        if idx > 1:
            pdf.ln(2)
            pdf.set_draw_color(180, 180, 180)
            pdf.set_line_width(0.3)
            y = pdf.get_y()
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(4)
            pdf.set_draw_color(0, 0, 0)

        # -------------------------
        # Encabezado del ejercicio
        # -------------------------
        nombre = f"{idx}. {row['id_ejercicio']} - {row['nombre']} ({row['duracion_min']} min)"
        safe_multicell(pdf, 0, 6, nombre)
        pdf.ln(1)

        # Línea de fase / subtema / intensidad
        fase = limpiar_texto_pdf(row.get("fase_juego", ""))
        subtema = limpiar_texto_pdf(row.get("subtema", ""))
        intensidad = limpiar_texto_pdf(row.get("intensidad", ""))

        meta_partes = []
        if fase:
            meta_partes.append(f"Fase: {fase}")
        if subtema:
            meta_partes.append(f"Subtema: {subtema}")
        if intensidad:
            meta_partes.append(f"Intensidad: {intensidad}")

        meta_line = " | ".join(meta_partes)
        safe_multicell(pdf, 0, 5, meta_line)
        pdf.ln(1)

        # -------------------------
        # Objetivo
        # -------------------------
        objetivo = limpiar_texto_pdf(row.get("objetivo_principal", ""))
        if objetivo:
            pdf.set_font("Arial", "B", 10)
            safe_multicell(pdf, 0, 5, "Objetivo:")
            pdf.set_font("Arial", "", 10)
            safe_multicell(pdf, 0, 5, objetivo)
            pdf.ln(1)

        # -------------------------
        # Logística
        # -------------------------
        espacio = limpiar_texto_pdf(row.get("espacio", ""))
        jugadores_min = limpiar_texto_pdf(row.get("jugadores_min", ""))
        jugadores_max = limpiar_texto_pdf(row.get("jugadores_max", ""))

        if espacio or jugadores_min or jugadores_max:
            pdf.set_font("Arial", "B", 10)
            safe_multicell(pdf, 0, 5, "Logística:")
            pdf.set_font("Arial", "", 10)
            if espacio:
                safe_multicell(pdf, 0, 5, f"- Espacio: {espacio}")
            if jugadores_min or jugadores_max:
                jug_text = f"- Jugadores: {jugadores_min}"
                if jugadores_max:
                    jug_text += f" - {jugadores_max}"
                safe_multicell(pdf, 0, 5, jug_text)
            pdf.ln(1)

        # -------------------------
        # Descripción
        # -------------------------
        desc = limpiar_texto_pdf(row.get("descripcion_paso_a_paso", ""))
        if desc:
            pdf.set_font("Arial", "B", 10)
            safe_multicell(pdf, 0, 5, "Descripción:")
            pdf.set_font("Arial", "", 10)
            safe_multicell(pdf, 0, 5, desc)
            pdf.ln(1)

        # -------------------------
        # Coaching points
        # -------------------------
        coaching = limpiar_texto_pdf(row.get("coaching_points", ""))
        if coaching:
            pdf.set_font("Arial", "B", 10)
            safe_multicell(pdf, 0, 5, "Coaching points:")
            pdf.set_font("Arial", "", 10)
            safe_multicell(pdf, 0, 5, coaching)
            pdf.ln(2)

    # ============================
    # Salida como bytes
    # ============================
    pdf_output = pdf.output(dest="S")
    if isinstance(pdf_output, str):
        pdf_bytes = pdf_output.encode("latin-1", "ignore")
    else:
        pdf_bytes = bytes(pdf_output)

    return pdf_bytes



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