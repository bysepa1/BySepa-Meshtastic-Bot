"""Validador y explicación de locator Maidenhead de 4 o 6 caracteres."""
import re
_LOCATOR_RE = re.compile(r"^[A-R]{2}[0-9]{2}(?:[A-X]{2})?$", re.I)
def handle(args, ctx):
    if len(args) != 1:
        return "Uso: /maidenhead <locator> (4 o 6 caracteres)"
    loc = args[0].upper()
    if not _LOCATOR_RE.fullmatch(loc):
        return "Locator no válido. Ejemplos: JN01 o JN01AB."
    precision = "campo de 4 caracteres" if len(loc) == 4 else "subcuadrícula de 6 caracteres"
    return f"Locator {loc} válido ({precision}). Es una referencia geográfica aproximada."
