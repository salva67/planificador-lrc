# =====================================================
# 🧠 Motor de ejercicios - Entrenador Bot
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
    for e in ejercicios[:5]:
        mensaje += (
            f"🔥 *{e['nombre']}* ({e['duracion_min']} min)\n"
            f"🎯 {e['objetivo_principal']}\n"
            f"📍 {e['espacio']}\n"
        )
        if e["coaching_points"]:
            mensaje += f"🗣️ {e['coaching_points']}\n"
        if e["video_link"]:
            mensaje += f"🎥 {e['video_link']}\n"
        mensaje += "—" * 25 + "\n"

    return mensaje