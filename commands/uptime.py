"""Comando /uptime."""

from commands.common import uptime_text


def handle(args, ctx):
    if args:
        return "Uso: /uptime"
    return f"Bot activo: {uptime_text(ctx['start_time'])}"
