import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# ===============================================
# 1️⃣ Configuración Streamlit
# ===============================================
st.set_page_config(page_title="Planificador LRC", page_icon="🏉", layout="wide")

st.title("🏉 Planificador Luján Rugby Club")
st.caption("Versión debug – conexión a Google Sheets")

# ===============================================
# 2️⃣ Leer secrets (SHEET_ID y credenciales)
# ===============================================
try:
    secrets = st.secrets
    SHEET_ID = secrets["SHEET_ID"]
    WORKSHEET = secrets["WORKSHEET"]
    GOOGLE_CREDENTIALS = json.loads(secrets["GOOGLE_CREDENTIALS"])
    st.success("✅ Secrets cargados correctamente.")
except Exception as e:
    st.error(f"❌ Error al leer st.secrets: {e}")
    st.stop()

# ===============================================
# 3️⃣ Conexión segura a Google Sheets
# ===============================================
@st.cache_data(show_spinner=True)
def cargar_datos():
    try:
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
    except Exception as e:
        # Este error lo vas a ver en pantalla
        st.error(f"⚠️ Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

# ===============================================
# 4️⃣ Mostrar resultados
# ===============================================
df = cargar_datos()

if df.empty:
    st.warning("⚠️ No se encontraron datos en el repositorio o no se pudo conectar.")
else:
    st.success(f"✅ Datos cargados correctamente: {len(df)} ejercicios.")
    st.dataframe(df.head(10))

# ===============================================
# 5️⃣ Info de depuración
# ===============================================
with st.expander("🔍 Detalle técnico"):
    st.write("SHEET_ID:", SHEET_ID)
    st.write("WORKSHEET:", WORKSHEET)
