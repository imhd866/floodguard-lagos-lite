import json
from dataclasses import dataclass
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
EXPOSURE_PATH = DATA_DIR / "location_exposure.json"
BOUNDARY_PATH = DATA_DIR / "lagos_boundary.geojson"


@dataclass(frozen=True)
class ExposureData:
    elevation_m: float
    population_1_5km: int
    low_elevation: float
    population_exposure: float
    historical_water: float
    water_affected_pct: float
    water_valid_pixels: int
    water_retrieved_at: str
    retrieved_at: str
    elevation_source: str
    population_source: str
    water_source: str


def low_elevation_indicator(elevation_m: float) -> float:
    """Risk contribution falls linearly from 1 at sea level to 0 at 20 m."""
    return round(1.0 - min(max(float(elevation_m), 0.0) / 20.0, 1.0), 4)


def population_exposure_indicator(population: float) -> float:
    """Cap exposure at an estimated 100,000 people within the 1.5 km radius."""
    return round(min(max(float(population), 0.0) / 100_000.0, 1.0), 4)


def historical_water_indicator(water_affected_fraction: float) -> float:
    """Cap risk at 25% of valid pixels showing recurrent historical water."""
    return round(min(max(float(water_affected_fraction), 0.0) / 0.25, 1.0), 4)


def load_exposure(location_name: str, path: Path = EXPOSURE_PATH) -> ExposureData | None:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))["locations"][location_name]
        return ExposureData(**record)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def load_lagos_boundary(path: Path = BOUNDARY_PATH) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return None
