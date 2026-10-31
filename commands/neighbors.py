"""Nodos escuchados recientemente; no implica que sean vecinos directos."""
import database

def handle(args, ctx):
    if args:
        return "Uso: /neighbors"
    rows = database.get_recent_nodes(recent_minutes=15, limit=4)
    if not rows:
        return "No hay nodos observados en los últimos 15 min."
    lines = ["NODOS ESCUCHADOS (15 min)"]
    for row in rows:
        snr = "N/D" if row["last_snr"] is None else f"{row['last_snr']} dB"
        rssi = "N/D" if row["last_rssi"] is None else f"{row['last_rssi']} dBm"
        lines.append(f"{row['node_name'][:18]}: SNR {snr}, RSSI {rssi}")
    lines.append("Escuchados; no confirma enlace directo.")
    return "\n".join(lines)
