"""Live air readings from Open-Meteo, with an EPA-style PM2.5 fallback."""

from __future__ import annotations

import httpx

from hearthline import store

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# US EPA PM2.5 breakpoints, micrograms per cubic meter to AQI.
_PM25_BREAKS = (
    (0.0, 12.0, 0, 50),
    (12.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
)


def band_for(aqi: int) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def pm25_to_us_aqi(pm25: float) -> int:
    value = max(0.0, min(500.4, pm25))
    for low_c, high_c, low_i, high_i in _PM25_BREAKS:
        if value <= high_c:
            if high_c == low_c:
                return low_i
            scaled = (high_i - low_i) / (high_c - low_c) * (value - low_c) + low_i
            return int(round(scaled))
    return 500


def parse_geocode(payload: dict, query: str) -> dict | None:
    results = payload.get("results") or []
    if not results:
        return None
    row = results[0]
    parts = [row.get("name") or query]
    if row.get("admin1"):
        parts.append(row["admin1"])
    if row.get("country"):
        parts.append(row["country"])
    return {
        "query": query,
        "label": ", ".join(parts),
        "latitude": row["latitude"],
        "longitude": row["longitude"],
    }


def parse_air(payload: dict, place: dict) -> dict | None:
    current = payload.get("current") or {}
    pm25 = current.get("pm2_5")
    us_aqi = current.get("us_aqi")
    basis = "us_aqi"
    if us_aqi is None and pm25 is not None:
        us_aqi = pm25_to_us_aqi(float(pm25))
        basis = "pm2_5_estimate"
    if us_aqi is None:
        return None
    aqi = int(round(float(us_aqi)))
    reading = {
        "ok": True,
        "city": place.get("query") or place.get("label"),
        "place_label": place.get("label") or place.get("query"),
        "latitude": place.get("latitude"),
        "longitude": place.get("longitude"),
        "us_aqi": aqi,
        "band": band_for(aqi),
        "pm2_5": None if pm25 is None else round(float(pm25), 1),
        "pm10": _round(current.get("pm10")),
        "nitrogen_dioxide": _round(current.get("nitrogen_dioxide")),
        "ozone": _round(current.get("ozone")),
        "observed_at": current.get("time"),
        "source": "open-meteo",
        "aqi_basis": basis,
        "cached": False,
    }
    return reading


def _round(value) -> float | None:
    if value is None:
        return None
    return round(float(value), 1)


async def geocode(client: httpx.AsyncClient, city: str) -> dict | None:
    response = await client.get(
        GEOCODE_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
    )
    response.raise_for_status()
    return parse_geocode(response.json(), city)


async def read_air(city: str) -> dict:
    query = city.strip()
    if not query:
        return {"ok": False, "error": "No city to check.", "speech": "Tell me which city this home is in."}
    timeout = httpx.Timeout(8.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            place = await geocode(client, query)
            if place is None:
                return {
                    "ok": False,
                    "error": f"Could not find {query}.",
                    "speech": f"I couldn't find a place called {query}. Try the city name on its own, like Ajmer or Seattle.",
                }
            response = await client.get(
                AIR_URL,
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "us_aqi,pm2_5,pm10,nitrogen_dioxide,ozone",
                    "timezone": "auto",
                },
            )
            response.raise_for_status()
            reading = parse_air(response.json(), place)
    except httpx.HTTPError as exc:
        reading = None
        cached = store.load_air_cache()
        if cached and _same_city(cached, query):
            cached = dict(cached)
            cached["cached"] = True
            cached["source"] = "cached-open-meteo"
            cached["speech"] = (
                f"The live air service didn't answer ({exc.__class__.__name__}). "
                f"This is the last saved reading for {cached.get('place_label', query)}."
            )
            return cached
        return {
            "ok": False,
            "error": str(exc),
            "speech": "The air service didn't answer just now. Try the brief again in a moment.",
        }
    if reading is None:
        return {
            "ok": False,
            "error": "Air payload had no AQI.",
            "speech": f"I found {query}, but the air service sent no AQI for it.",
        }
    store.save_air_cache(reading)
    return reading


def _same_city(cached: dict, query: str) -> bool:
    haystack = f"{cached.get('city', '')} {cached.get('place_label', '')}".casefold()
    return query.casefold() in haystack or haystack.split(",")[0].strip() == query.casefold()
