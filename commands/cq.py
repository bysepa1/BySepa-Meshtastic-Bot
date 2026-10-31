"""Comando /cq."""
from commands.qrz import station_identity

def handle(args, ctx):
    if args:
        return "Uso: /cq"
    call, locator = station_identity(ctx)
    station = call or "estación sin indicativo configurado"
    loc = f" | Locator {locator}" if locator else ""
    return f"CQ CQ CQ de {station}{loc}. ¿Alguna estación copia?"
