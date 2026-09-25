"""Build small, reviewable caches from geoBoundaries, Copernicus DEM, and WorldPop."""

import json
import math
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import rasterio
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.exposure import (DATA_DIR, low_elevation_indicator,
                               population_exposure_indicator)
from src.data.locations import PILOT_LOCATIONS


BOUNDARY_METADATA_URL = "https://www.geoboundaries.org/api/current/gbOpen/NGA/ADM1/"
COPERNICUS_TILE_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_N06_00_E003_00_DEM/"
    "Copernicus_DSM_COG_10_N06_00_E003_00_DEM.tif"
)
WORLDPOP_STATS_URL = "https://api.worldpop.org/v1/services/stats"


def circle_feature(latitude: float, longitude: float, radius_km: float = 1.5) -> dict:
    coordinates = []
    for degree in range(0, 361, 15):
        angle = math.radians(degree)
        lat = latitude + radius_km * math.sin(angle) / 110.574
        lon = longitude + radius_km * math.cos(angle) / (111.320 * math.cos(math.radians(latitude)))
        coordinates.append([round(lon, 6), round(lat, 6)])
    return {"type": "Feature", "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [coordinates]}}


def fetch_lagos_boundary(session: requests.Session) -> dict:
    metadata_response = session.get(BOUNDARY_METADATA_URL, timeout=30)
    metadata_response.raise_for_status()
    metadata = metadata_response.json()
    boundary_response = session.get(metadata["simplifiedGeometryGeoJSON"], timeout=60)
    boundary_response.raise_for_status()
    boundary = boundary_response.json()
    matches = [feature for feature in boundary["features"]
               if feature.get("properties", {}).get("shapeName", "").casefold() == "lagos"]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one Lagos boundary; found {len(matches)}")
    feature = matches[0]
    feature["properties"].update({
        "source": "geoBoundaries gbOpen NGA ADM1",
        "license": metadata["boundaryLicense"],
        "boundary_year": metadata["boundaryYearRepresented"],
        "source_url": metadata["gjDownloadURL"],
    })
    return {"type": "FeatureCollection", "features": [feature]}


def fetch_population(session: requests.Session, latitude: float, longitude: float) -> int:
    response = session.get(WORLDPOP_STATS_URL, params={
        "dataset": "wpgppop", "year": 2020,
        "geojson": json.dumps(circle_feature(latitude, longitude), separators=(",", ":")),
        "runasync": "false",
    }, timeout=120)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error") or "total_population" not in payload.get("data", {}):
        raise RuntimeError(f"WorldPop query failed: {payload.get('error_message') or payload}")
    return round(float(payload["data"]["total_population"]))


def download_dem(session: requests.Session, destination: Path) -> None:
    with session.get(COPERNICUS_TILE_URL, timeout=180, stream=True) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for chunk in response.iter_content(1024 * 1024):
                output.write(chunk)


def main() -> None:
    session = requests.Session()
    session.headers["User-Agent"] = "FloodGuard-Lagos-Lite/1.0"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    boundary = fetch_lagos_boundary(session)
    (DATA_DIR / "lagos_boundary.geojson").write_text(
        json.dumps(boundary, separators=(",", ":")), encoding="utf-8")

    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with tempfile.TemporaryDirectory(prefix="floodguard-dem-") as temporary:
        dem_path = Path(temporary) / "copernicus-dem.tif"
        download_dem(session, dem_path)
        with rasterio.open(dem_path) as dataset:
            samples = dataset.sample((item["longitude"], item["latitude"])
                                     for item in PILOT_LOCATIONS.values())
            elevations = [float(value[0]) for value in samples]

    records = {}
    for (name, location), elevation in zip(PILOT_LOCATIONS.items(), elevations):
        population = fetch_population(session, location["latitude"], location["longitude"])
        records[name] = {
            "elevation_m": round(elevation, 1),
            "population_1_5km": population,
            "low_elevation": low_elevation_indicator(elevation),
            "population_exposure": population_exposure_indicator(population),
            "retrieved_at": retrieved_at,
            "elevation_source": "Copernicus DEM GLO-30 (public AWS mirror)",
            "population_source": "WorldPop Global per-country 2020 (100 m)",
        }
        print(f"{name}: {elevation:.1f} m; {population:,} people")

    payload = {
        "schema_version": 1,
        "retrieved_at": retrieved_at,
        "transformations": {
            "low_elevation": "1 - clamp(elevation metres / 20, 0, 1)",
            "population_exposure": "clamp(population within 1.5 km / 100000, 0, 1)",
        },
        "locations": records,
    }
    (DATA_DIR / "location_exposure.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    from scripts.build_water_history_cache import main as build_water_history_cache
    build_water_history_cache()


if __name__ == "__main__":
    main()
