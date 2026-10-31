"""Comando /time."""

from commands.common import utc_time


def handle(args, ctx):
    if args:
        return "Uso: /time"
    return f"Hora actual: {utc_time()}"
