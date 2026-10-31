"""Comando /solar y cliente de datos Kp de NOAA SWPC."""
import json
import urllib.request

URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
USER_AGENT = "BySepa-Meshtastic-Bot/1.1"

def latest_kp():
    request = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=7) as response:
        rows = json.loads(response.read().decode("utf-8"))
    if len(rows) < 2:
        return None
    record = dict(zip(rows[0], rows[-1]))
    kp = record.get("Kp")
    stamp = record.get("time_tag", "")
    return (kp, stamp) if kp is not None else None

def handle(args, ctx):
    if args:
        return "Uso: /solar"
    try:
        result = latest_kp()
        if not result:
            return "No hay datos geomagnéticos disponibles."
        kp, stamp = result
        return f"Índice geomagnético Kp: {kp}\nDato UTC: {stamp}\nNo es una predicción de propagación."
    except Exception:
        return "No pude consultar los datos geomagnéticos. Inténtalo más tarde."
