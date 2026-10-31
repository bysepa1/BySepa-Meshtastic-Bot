"""Comando /qrz; extrae identificación del nombre del nodo o usa configuración."""
import re

_CALL_RE = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{1,3}[0-9][A-Z0-9]{1,4}(?![A-Z0-9])", re.I)
_LOCATOR_RE = re.compile(r"(?<![A-Z0-9])[A-R]{2}[0-9]{2}(?:[A-X]{2})?(?![A-Z0-9])", re.I)

def station_identity(ctx):
    name = str(ctx.get("node_name", ""))
    call_match = _CALL_RE.search(name.upper())
    loc_match = _LOCATOR_RE.search(name.upper())
    call = call_match.group(0).upper() if call_match else (str(ctx.get("station_callsign", "")).strip().upper() or None)
    locator = loc_match.group(0).upper() if loc_match else (str(ctx.get("station_locator", "")).strip().upper() or None)
    return call, locator

def handle(args, ctx):
    if args:
        return "Uso: /qrz"
    call, locator = station_identity(ctx)
    if not call and not locator:
        return "Estación sin indicativo ni locator detectables. Configura STATION_CALLSIGN y STATION_LOCATOR."
    parts = [f"Estación: {call or 'sin indicativo'}"]
    if locator:
        parts.append(f"Locator: {locator}")
    parts.append(f"Nombre del nodo: {str(ctx.get('node_name', 'Nodo desconocido'))[:60]}")
    return "\n".join(parts)
