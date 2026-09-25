# FloodGuard Lagos Lite

FloodGuard Lagos Lite is a free-first decision-support prototype for indicative flood disruption risk in selected Lagos communities. It combines live Open-Meteo forecasts with transparent, replaceable risk factors and produces a calm, copy-ready advisory.

> FloodGuard Lagos Lite is a decision-support and planning tool. It does not replace official emergency alerts or human judgment.

## Phase 1 scope

- Selector for all 10 pilot locations from the project guide
- Live 72-hour rainfall forecast from Open-Meteo
- Live OpenStreetMap roads, waterways, schools, and markets within 1.5 km
- Explainable weighted risk score
- Rule-based advisory that works without an LLM
- Optional NVIDIA NIM rewrite when credentials are configured
- Tests for scoring and advisory behavior
- Optional NVIDIA NIM wording with fact-preservation checks and automatic fallback
- Local community-report preparation with official Lagos State handoff links
- Cached Copernicus DEM elevation and WorldPop population exposure for all 10 areas
- Lagos State boundary overlay from geoBoundaries
- Historical surface-water recurrence from Digital Earth Africa WOfS (1984–2026)

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

The live weather and OpenStreetMap calls need internet access. Weather failure stops the result; OSM failure is clearly reported and the risk model uses documented fallbacks for those OSM factors. Elevation, population, and historical-water recurrence are read from a small reproducible cache built by `scripts/build_exposure_cache.py`.

## Configuration

Copy `.env.example` to `.env`. NVIDIA credentials are optional; the deterministic advisory is the default and keeps the app functional without paid services.

Community reports are prepared locally for review. The prototype does not transmit reports or claim receipt by Lagos State. Immediate emergencies are directed to 112 or 767; non-emergency handoff links point to Lagos State Citizens Gate.

## Risk model

The score follows the project guide's weights: rainfall 35%, elevation 20%, waterway proximity 15%, historical water recurrence 15%, nearby infrastructure 10%, and population exposure 5%. Rainfall and OpenStreetMap factors are live; Copernicus elevation, WorldPop population, and Digital Earth Africa WOfS recurrence are cached measured inputs. The transformations remain prototype screening assumptions that require local calibration.

## Roadmap

See [docs/model_plan.md](docs/model_plan.md) and [docs/data_sources.md](docs/data_sources.md).

## License

Apache-2.0. Data providers retain their respective licenses and attribution requirements.
