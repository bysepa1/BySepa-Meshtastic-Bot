"""Comando /weather <ciudad>, usando Open-Meteo."""

import json
import time
import urllib.parse
import urllib.request

_CACHE = {}
CACHE_SECONDS = 600
USER_AGENT = "BySepa-Meshtastic-Bot/1.0"


def _get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=7) as response:
        return json.loads(response.read().decode("utf-8"))


def get_weather(city):
    key = city.casefold()
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1]

    geo_url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({
        "name": city, "count": 1, "language": "es", "format": "json",
    })
    geo = _get_json(geo_url)
    results = geo.get("results") or []
    if not results:
        return None

    place = results[0]
    query = {
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
        "timezone": "UTC",
        "forecast_days": 1,
    }
    weather_url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(query)
    data = _get_json(weather_url)
    result = (place, data.get("current", {}))
    _CACHE[key] = (now, result)
    return result


def handle(args, ctx):
    if not args:
        return "Uso: /weather <ciudad>"
    city = " ".join(args)
    try:
        result = get_weather(city)
        if result is None:
            return f"No encontré la ciudad: {city}"
        place, current = result
        name = place.get("name", city)
        country = place.get("country", "")
        temp = current.get("temperature_2m")
        feels = current.get("apparent_temperature")
        humidity = current.get("relative_humidity_2m")
        wind = current.get("wind_speed_10m")
        rain = current.get("precipitation")
        def fmt(value, suffix):
            return "N/D" if value is None else f"{value}{suffix}"
        location = f"{name}, {country}" if country else name
        return (
            f"Clima {location}\n"
            f"Temp: {fmt(temp, '°C')} (sens. {fmt(feels, '°C')})\n"
            f"Viento: {fmt(wind, ' km/h')} | Humedad: {fmt(humidity, '%')}\n"
            f"Precip.: {fmt(rain, ' mm')}"
        )
    except Exception:
        return "No pude consultar el clima. Inténtalo más tarde."
