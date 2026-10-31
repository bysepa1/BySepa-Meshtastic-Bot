"""Comando /version."""
VERSION = "1.1.0"
def handle(args, ctx):
    if args:
        return "Uso: /version"
    return f"BySepa Meshtastic Bot v{VERSION}"
