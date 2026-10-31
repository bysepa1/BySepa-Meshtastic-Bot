"""Comando /distance <locator1> <locator2> para Maidenhead de 4 o 6 caracteres."""

import math
import re

_LOCATOR_RE = re.compile(r"^[A-Ra-r]{2}[0-9]{2}(?:[A-Xa-x]{2})?$")


def locator_center(locator):
    loc = locator.upper()
    if not _LOCATOR_RE.fullmatch(loc):
        raise ValueError("Locator inválido")
    lon = -180.0 + (ord(loc[0]) - ord("A")) * 20.0
    lat = -90.0 + (ord(loc[1]) - ord("A")) * 10.0
    lon += int(loc[2]) * 2.0
    lat += int(loc[3]) * 1.0
    lon_size, lat_size = 2.0, 1.0
    if len(loc) == 6:
        lon += (ord(loc[4]) - ord("A")) * (2.0 / 24.0)
        lat += (ord(loc[5]) - ord("A")) * (1.0 / 24.0)
        lon_size, lat_size = 2.0 / 24.0, 1.0 / 24.0
    return lat + lat_size / 2, lon + lon_size / 2


def distance_km(a, b):
    lat1, lon1 = map(math.radians, locator_center(a))
    lat2, lon2 = map(math.radians, locator_center(b))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    hav = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(hav)))


def handle(args, ctx):
    if len(args) != 2:
        return "Uso: /distance <LOCATOR1> <LOCATOR2>\nEj.: /distance JN01AB JN00AA"
    try:
        km = distance_km(args[0], args[1])
        return f"Distancia {args[0].upper()}–{args[1].upper()}: {km:.1f} km (aprox.)"
    except ValueError:
        return "Locator inválido. Usa Maidenhead de 4 o 6 caracteres, ej. JN01AB."
