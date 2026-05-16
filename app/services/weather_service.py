import httpx
from pydantic import BaseModel, field_validator

from app.config import settings
from app.repositories import weather_repository
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CoordsIn(BaseModel):
    lat: float
    lon: float

    @field_validator("lat")
    @classmethod
    def lat_range(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("lat debe estar en [-90, 90]")
        return v

    @field_validator("lon")
    @classmethod
    def lon_range(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("lon debe estar en [-180, 180]")
        return v


def generate_weather_impact(data: dict) -> dict | None:
    """
    Genera weather_impact según la tabla de RF-002.
    Devuelve None si el clima es normal.
    """
    current = data.get("current", {})
    weather_code = current.get("weather_code", 0)
    wind_speed = current.get("wind_speed_10m", 0)
    temperature = current.get("temperature_2m", 20)
    visibility = current.get("visibility", 10000)

    # WMO weather codes: https://open-meteo.com/en/docs
    # 95–99: tormenta / lluvia intensa
    if weather_code >= 95:
        return {"severity": "critical", "message": "Tormenta activa. Visibilidad reducida, riesgo elevado."}

    # 61–67, 80–82: lluvia leve/moderada
    if weather_code in range(61, 68) or weather_code in range(80, 83):
        return {"severity": "moderate", "message": "Lluvia leve. Considera aumentar la distancia de frenado."}

    # 45, 48: niebla
    if weather_code in (45, 48) or (visibility is not None and visibility < 1000):
        return {"severity": "high", "message": "Baja visibilidad por niebla. Reduce la velocidad."}

    # Viento fuerte: > 50 km/h
    if wind_speed and wind_speed > 50:
        return {"severity": "moderate", "message": "Vientos fuertes detectados. Precaución en vías expuestas."}

    # Calor extremo: > 35°C
    if temperature and temperature > 35:
        return {"severity": "moderate", "message": "Temperatura alta. El calor puede incrementar la fatiga."}

    return None


async def get_weather(lat: float, lon: float) -> dict:
    """
    Devuelve datos del clima con caché de 15 min.
    Fallback: último caché disponible + warning=True si la API falla.
    """
    coords = CoordsIn(lat=lat, lon=lon)

    cached = weather_repository.get_cached_weather(coords.lat, coords.lon)
    if cached:
        return cached

    params = {
        "latitude": coords.lat,
        "longitude": coords.lon,
        "current": "temperature_2m,wind_speed_10m,weather_code,visibility",
        "wind_speed_unit": "kmh",
    }

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.get(settings.WEATHER_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

        weather_repository.save_weather(
            coords.lat, coords.lon, data,
            ttl_minutes=settings.WEATHER_CACHE_TTL_MINUTES,
        )
        logger.info("Weather fetched from API lat=%.2f lon=%.2f", coords.lat, coords.lon)
        return data

    except Exception as exc:
        logger.error("Weather API failed: %s — using stale cache if available", type(exc).__name__)
        # Fallback: intentar caché expirado consultando directo (sin limpiar expirados)
        stale = _get_stale_cache(coords.lat, coords.lon)
        if stale:
            stale["warning"] = True
            return stale
        return {"warning": True}


def _get_stale_cache(lat: float, lon: float) -> dict | None:
    """Lee caché aunque esté expirado (solo para fallback)."""
    import json
    from app.db.database import get_connection
    from sqlalchemy import text

    key = f"{round(lat, 2)},{round(lon, 2)}"
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT weather_data_json FROM weather_cache WHERE coordinates_key = :key"),
            {"key": key},
        ).mappings().first()
    return json.loads(row["weather_data_json"]) if row else None
