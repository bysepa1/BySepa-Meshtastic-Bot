"""Comando /forecast <ciudad>, previsión resumida de las próximas 24 h."""

import json
import urllib.parse
import urllib.request

USER_AGENT = "BySepa-Meshtastic-Bot/1.0"


def _get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=7) as response:
        return json.loads(response.read().decode("utf-8"))


def handle(args, ctx):
    if not args:
        return "Uso: /forecast <ciudad>"
    city = " ".join(args)
    try:
        geo_url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({
            "name": city, "count": 1, "language": "es", "format": "json",
        })
        results = _get_json(geo_url).get("results") or []
        if not results:
            return f"No encontré la ciudad: {city}"
        place = results[0]
        params = {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "hourly": "temperature_2m,precipitation_probability",
            "forecast_days": 2,
            "timezone": "UTC",
        }
        url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)
        data = _get_json(url).get("hourly", {})
        times = data.get("time", [])
        temps = data.get("temperature_2m", [])
        rain = data.get("precipitation_probability", [])
        if not temps:
            return "La API no devolvió datos de previsión."
        # The hourly API returns UTC values; take the next 24 entries from current UTC hour.
        from datetime import datetime, timezone
        now_hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
        start = next((i for i, value in enumerate(times) if value >= now_hour), 0)
        window_t = [x for x in temps[start:start + 24] if x is not None]
        window_r = [x for x in rain[start:start + 24] if x is not None]
        if not window_t:
            return "No hay datos suficientes para la previsión."
        name = place.get("name", city)
        return (
            f"Previsión 24h {name}\n"
            f"Mín/Máx: {min(window_t):.0f}/{max(window_t):.0f}°C\n"
            f"Prob. lluvia máx: {max(window_r) if window_r else 'N/D'}%"
        )
    except Exception:
        return "No pude consultar la previsión. Inténtalo más tarde."
