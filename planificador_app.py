import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# ===============================================
# 1️⃣ Configuración Streamlit
# ===============================================
st.set_page_config(page_title="Planificador LRC", page_icon="🏉", layout="wide")

# 🔐 Leemos credenciales desde secrets
secrets = st.secrets
SHEET_ID = secrets["SHEET_ID"]
WORKSHEET = secrets["WORKSHEET"]
GOOGLE_CREDENTIALS = json.loads(secrets["GOOGLE_CREDENTIALS"])

# ===============================================
# 2️⃣ Conexión segura a Google Sheets
# ===============================================
@st.cache_data(show_spinner=False)
def cargar_datos():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

df = cargar_datos()
