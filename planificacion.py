import gspread
from google.oauth2.service_account import Credentials

# 1️⃣ Conectar con Google Sheets usando el ID
def conectar_sheet(sheet_id: str, worksheet_name: str = "repositorio_ejercicios"):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    creds_path = r"C:\Users\ad651985\Downloads\backUp_telefonica\Salvador\rugby\LRC\planificacion_entreanamientos\credentials.json"

    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
    return sheet

# 2️⃣ Leer los registros
def leer_repositorio(sheet):
    registros = sheet.get_all_records()
    return registros

# =====================================================
# 2️⃣ Leer el repositorio completo
# =====================================================
def leer_repositorio(sheet):
    registros = sheet.get_all_records()
    return registros


# =====================================================
# 3️⃣ Filtro de ejercicios
# =====================================================
def filtrar_ejercicios(ejercicios, fase=None, intensidad=None, duracion_max=None, subtema=None):
    filtrados = []
    for e in ejercicios:
        if fase and e["fase_juego"].strip().lower() != fase.lower():
            continue
        if intensidad and e["intensidad"].strip().lower() != intensidad.lower():
            continue
        if duracion_max and int(e["duracion_min"]) > duracion_max:
            continue
        if subtema and subtema.lower() not in e["subtema"].lower():
            continue
        filtrados.append(e)
    return filtrados


# =====================================================
# 4️⃣ Formatear mensaje tipo WhatsApp
# =====================================================
def formatear_mensaje(ejercicios, fase=None, intensidad=None):
    if not ejercicios:
        return "⚠️ No se encontraron ejercicios con esos criterios."

    encabezado = f"🏉 *Ejercicios sugeridos*"
    if fase:
        encabezado += f" — {fase.capitalize()}"
    if intensidad:
        encabezado += f" ({intensidad.lower()})"
    encabezado += "\n\n"

    mensaje = encabezado
    for e in ejercicios[:5]:  # muestra los primeros 5
        mensaje += (
            f"🔥 *{e['nombre']}* ({e['duracion_min']} min)\n"
            f"🎯 {e['objetivo_principal']}\n"
            f"📍 {e['espacio']}\n"
        )

        # Coaching points
        if e["coaching_points"]:
            mensaje += f"🗣️ {e['coaching_points']}\n"

        # Video link si existe
        if e["video_link"]:
            mensaje += f"🎥 {e['video_link']}\n"

        mensaje += "—" * 25 + "\n"

    return mensaje


# =====================================================
# 5️⃣ Ejemplo de uso
# =====================================================
if __name__ == "__main__":
    SHEET_ID = "1uo3iAGXa8OanvFKLUfCm192PidE4KB-yIXbROwfFVU4"
    sheet = conectar_sheet(SHEET_ID)
    ejercicios = leer_repositorio(sheet)

    # ⚙️ Ejemplo: defensa + alta intensidad + duración máxima 20 min
    seleccion = filtrar_ejercicios(
        ejercicios,
        fase="Defensa",
        intensidad="alta",
        duracion_max=20
    )

    texto = formatear_mensaje(seleccion, fase="Defensa", intensidad="Alta")
    print(texto)