from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherServiceError(RuntimeError):
    """Raised when live forecast data cannot be retrieved or validated."""


@dataclass(frozen=True)
class RainfallSummary:
    next_24h_mm: float
    next_72h_mm: float
    peak_hourly_mm: float
    hourly: list[dict[str, object]]


def fetch_rainfall(latitude: float, longitude: float, timeout: int = 15) -> RainfallSummary:
    params = {"latitude": latitude, "longitude": longitude, "hourly": "precipitation",
              "forecast_days": 3, "timezone": "Africa/Lagos"}
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        times = payload["hourly"]["time"]
        precipitation = payload["hourly"]["precipitation"]
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        raise WeatherServiceError("Live rainfall forecast is currently unavailable.") from exc
    if not times or len(times) != len(precipitation):
        raise WeatherServiceError("The weather service returned an incomplete forecast.")
    values = [max(0.0, float(value or 0.0)) for value in precipitation[:72]]
    rows = [{"time": datetime.fromisoformat(time), "precipitation_mm": value}
            for time, value in zip(times[:72], values)]
    return RainfallSummary(round(sum(values[:24]), 1), round(sum(values), 1),
                           round(max(values, default=0.0), 1), rows)
