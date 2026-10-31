"""Resumen de actividad geomagnética; no pretende ser un pronóstico de banda."""
from commands.solar import latest_kp

def handle(args, ctx):
    if args:
        return "Uso: /propagation"
    try:
        result = latest_kp()
    except Exception:
        result = None
    if not result:
        return "No pude consultar la actividad geomagnética. Inténtalo más tarde."
    kp, stamp = result
    return f"Kp geomagnético: {kp}\nDato UTC: {stamp}\nKp orienta sobre actividad geomagnética; no predice por sí solo la propagación de una banda."
