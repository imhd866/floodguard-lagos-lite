from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

import requests


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "FloodGuard-Lagos-Lite/0.2 (public-good prototype)"


class OSMServiceError(RuntimeError):
    """Raised when OpenStreetMap infrastructure data cannot be retrieved."""


@dataclass(frozen=True)
class OSMFeature:
    category: str
    name: str
    latitude: float
    longitude: float
    geometry: list[dict[str, float]]


@dataclass(frozen=True)
class InfrastructureSummary:
    features: list[OSMFeature]
    counts: dict[str, int]
    waterway_indicator: float
    infrastructure_indicator: float


def _query(latitude: float, longitude: float, radius_m: int) -> str:
    around = f"around:{radius_m},{latitude},{longitude}"
    return f"""[out:json][timeout:25];
way({around})[highway];out tags center geom 350;
nwr({around})[amenity=school];out tags center geom 100;
nwr({around})[amenity=marketplace];out tags center geom 50;
way({around})[waterway];out tags center geom 100;
way({around})[natural=water];out tags center geom 50;"""


def _category(tags: dict[str, str]) -> str | None:
    if "highway" in tags:
        return "road"
    if tags.get("amenity") == "school":
        return "school"
    if tags.get("amenity") == "marketplace":
        return "market"
    if "waterway" in tags or tags.get("natural") == "water":
        return "waterway"
    return None


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_000
    d_lat, d_lon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * earth_radius_m * asin(sqrt(a))


def _parse_feature(element: dict) -> OSMFeature | None:
    tags = element.get("tags", {})
    category = _category(tags)
    if category is None:
        return None
    geometry = [
        {"latitude": float(point["lat"]), "longitude": float(point["lon"])}
        for point in element.get("geometry", [])
        if "lat" in point and "lon" in point
    ]
    center = element.get("center", {})
    latitude = element.get("lat", center.get("lat"))
    longitude = element.get("lon", center.get("lon"))
    if latitude is None or longitude is None:
        if not geometry:
            return None
        latitude = sum(point["latitude"] for point in geometry) / len(geometry)
        longitude = sum(point["longitude"] for point in geometry) / len(geometry)
    return OSMFeature(category, tags.get("name", f"Unnamed {category}"),
                      float(latitude), float(longitude), geometry)


def fetch_infrastructure(latitude: float, longitude: float, radius_m: int = 1_500,
                         timeout: int = 35) -> InfrastructureSummary:
    try:
        response = requests.post(OVERPASS_URL, data={"data": _query(latitude, longitude, radius_m)},
                                 headers={"User-Agent": USER_AGENT}, timeout=timeout)
        response.raise_for_status()
        elements = response.json()["elements"]
    except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
        raise OSMServiceError("OpenStreetMap infrastructure is currently unavailable.") from exc

    features = [feature for element in elements if (feature := _parse_feature(element))]
    counts = {category: sum(f.category == category for f in features)
              for category in ("road", "school", "market", "waterway")}
    waterways = [f for f in features if f.category == "waterway"]
    nearest_water_m = min((_distance_m(latitude, longitude, f.latitude, f.longitude)
                           for f in waterways), default=float("inf"))
    waterway_indicator = 0.0 if not waterways else max(0.0, 1 - nearest_water_m / radius_m)
    infrastructure_indicator = min(1.0, counts["road"] / 300 * 0.5 +
                                   counts["school"] / 10 * 0.3 +
                                   counts["market"] / 5 * 0.2)
    return InfrastructureSummary(features, counts, round(waterway_indicator, 4),
                                 round(infrastructure_indicator, 4))
