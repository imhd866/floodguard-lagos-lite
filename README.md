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

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

The live weather and OpenStreetMap calls need internet access. Weather failure stops the result; OSM failure is clearly reported and the risk model uses the documented prototype baselines instead.

## Configuration

Copy `.env.example` to `.env`. NVIDIA credentials are optional; the deterministic advisory is the default and keeps the app functional without paid services.

Community reports are prepared locally for review. The prototype does not transmit reports or claim receipt by Lagos State. Immediate emergencies are directed to 112 or 767; non-emergency handoff links point to Lagos State Citizens Gate.

## Risk model

The score follows the project guide's weights: rainfall 35%, elevation 20%, waterway proximity 15%, historical water recurrence 15%, nearby infrastructure 10%, and population exposure 5%. Phase 1 uses documented pilot-area baseline indicators for all factors except live rainfall. These are prototype assumptions—not measured claims—and the UI labels them accordingly.

## Roadmap

See [docs/model_plan.md](docs/model_plan.md) and [docs/data_sources.md](docs/data_sources.md).

## License

Apache-2.0. Data providers retain their respective licenses and attribution requirements.
