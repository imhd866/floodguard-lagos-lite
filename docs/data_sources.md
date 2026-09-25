# Data sources

| Source | MVP use | Status |
|---|---|---|
| Open-Meteo | Hourly precipitation forecast | Implemented live |
| OpenStreetMap/Overpass | Live roads, schools, markets, waterways within 1.5 km | Implemented live |
| geoBoundaries gbOpen NGA ADM1 (2022 boundary) | Lagos State boundary overlay | Implemented cached, CC BY 4.0 |
| Copernicus DEM GLO-30 | Surface elevation at each pilot-area point | Implemented cached |
| WorldPop Global per-country 2020 | Estimated population within 1.5 km | Implemented cached |
| Digital Earth Africa WOfS or JRC | Historical surface water | Phase 3 |

Each integration must preserve provider attribution, license notes, retrieval date, and a failure state. Missing data must never silently become zero risk.

Run `python scripts/build_exposure_cache.py` to refresh the measured-data cache. The script
downloads the public Copernicus DEM tile temporarily, samples the ten coordinates, queries
WorldPop for each 1.5 km circle, and keeps only the small derived JSON records. Elevation risk
falls linearly from 1.0 at sea level to 0 at 20 metres. Population exposure is capped at 1.0
at an estimated 100,000 people within the radius. These transparent prototype transforms must
be calibrated before operational use.
