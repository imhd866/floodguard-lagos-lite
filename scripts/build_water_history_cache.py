"""Add Digital Earth Africa WOfS recurrence metrics to the exposure cache."""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
import requests
from rasterio.windows import from_bounds
from rasterio.warp import transform

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.exposure import DATA_DIR, EXPOSURE_PATH, historical_water_indicator
from src.data.locations import PILOT_LOCATIONS


WOFS_FREQUENCY_URL = (
    "https://deafrica-services.s3.af-south-1.amazonaws.com/"
    "wofs_ls_summary_alltime/1-0-0/x184/y085/1984--P42Y/"
    "wofs_ls_summary_alltime_x184y085_1984--P42Y_frequency.tif"
)
RADIUS_M = 1_500
RECURRENCE_THRESHOLD = 0.05


def download_raster(session: requests.Session, destination: Path) -> None:
    with session.get(WOFS_FREQUENCY_URL, timeout=180, stream=True) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for chunk in response.iter_content(1024 * 1024):
                output.write(chunk)


def summarize_circle(dataset: rasterio.io.DatasetReader, latitude: float,
                     longitude: float) -> tuple[float, int]:
    xs, ys = transform("EPSG:4326", dataset.crs, [longitude], [latitude])
    center_x, center_y = xs[0], ys[0]
    window = from_bounds(center_x - RADIUS_M, center_y - RADIUS_M,
                         center_x + RADIUS_M, center_y + RADIUS_M,
                         transform=dataset.transform).round_offsets().round_lengths()
    values = dataset.read(1, window=window, masked=True)
    window_transform = dataset.window_transform(window)
    rows, cols = np.indices(values.shape)
    pixel_x = window_transform.c + (cols + 0.5) * window_transform.a
    pixel_y = window_transform.f + (rows + 0.5) * window_transform.e
    inside = ((pixel_x - center_x) ** 2 + (pixel_y - center_y) ** 2) <= RADIUS_M ** 2
    valid = inside & ~np.ma.getmaskarray(values) & np.isfinite(values.filled(np.nan))
    valid_values = values.data[valid]
    if valid_values.size == 0:
        raise RuntimeError("No valid WOfS observations in analysis circle")
    affected_fraction = float(np.count_nonzero(valid_values >= RECURRENCE_THRESHOLD)
                              / valid_values.size)
    return affected_fraction, int(valid_values.size)


def main() -> None:
    payload = json.loads(EXPOSURE_PATH.read_text(encoding="utf-8"))
    session = requests.Session()
    session.headers["User-Agent"] = "FloodGuard-Lagos-Lite/1.0"
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with tempfile.TemporaryDirectory(prefix="floodguard-wofs-") as temporary:
        raster_path = Path(temporary) / "wofs-frequency.tif"
        download_raster(session, raster_path)
        with rasterio.open(raster_path) as dataset:
            for name, location in PILOT_LOCATIONS.items():
                fraction, valid_pixels = summarize_circle(
                    dataset, location["latitude"], location["longitude"])
                record = payload["locations"][name]
                record.update({
                    "historical_water": historical_water_indicator(fraction),
                    "water_affected_pct": round(fraction * 100, 1),
                    "water_valid_pixels": valid_pixels,
                    "water_retrieved_at": retrieved_at,
                    "water_source": "Digital Earth Africa WOfS all-time summary (1984–2026)",
                })
                print(f"{name}: {fraction:.1%} recurrent-water pixels; "
                      f"indicator {record['historical_water']:.3f}")

    payload["retrieved_at"] = retrieved_at
    payload["transformations"]["historical_water"] = (
        "clamp(fraction of valid 1.5 km pixels with WOfS frequency >= 5% / 0.25, 0, 1)"
    )
    payload["water_history"] = {
        "source": "Digital Earth Africa Water Observations from Space All-Time Summary",
        "source_url": WOFS_FREQUENCY_URL,
        "license": "CC BY 4.0",
        "spatial_resolution_m": 30,
        "temporal_range": "1984–2026",
        "retrieved_at": retrieved_at,
    }
    EXPOSURE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
