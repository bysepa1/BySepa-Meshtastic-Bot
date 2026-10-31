"""Comando /ping."""

from commands.common import utc_time


def handle(args, ctx):
    if args:
        return "Uso: /ping"
    rssi = ctx["rssi"]
    snr = ctx["snr"]
    rssi_text = "N/D" if rssi is None else f"{rssi} dBm"
    snr_text = "N/D" if snr is None else f"{snr} dB"
    return (
        "/pong\n"
        f"Origen: {ctx['source_name']}\n"
        f"Nodo: {ctx['node_name']} | {ctx['bot_author']}\n"
        f"Saltos: {ctx['hops']}\n"
        f"Hora GMT: {utc_time().replace(' UTC', ' GMT')}\n"
        f"SNR: {snr_text}\n"
        f"RSSI: {rssi_text}\n"
        f"Ubicación: {ctx['location']}"
    )
