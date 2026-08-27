from src.ai.advisory import DISCLAIMER, build_advisory
from src.data.locations import PILOT_LOCATIONS
from src.data.osm import fetch_infrastructure
from src.risk.scoring import RiskResult, calculate_risk, rainfall_indicator

def test_rainfall_indicator_is_bounded():
    assert rainfall_indicator(-5, -1) == 0
    assert rainfall_indicator(500, 100) == 1

def test_risk_labels_match_guide_thresholds():
    zeros = {name: 0 for name in ("rainfall", "low_elevation", "waterway_proximity",
             "historical_water", "infrastructure_exposure", "population_exposure")}
    ones = {name: 1 for name in zeros}
    assert (calculate_risk(**zeros).score, calculate_risk(**zeros).label) == (0, "Low")
    assert (calculate_risk(**ones).score, calculate_risk(**ones).label) == (100, "High")

def test_inputs_are_clamped():
    result = calculate_risk(rainfall=2, low_elevation=-1, waterway_proximity=0,
                            historical_water=0, infrastructure_exposure=0,
                            population_exposure=0)
    assert result.score == 35

def test_advisory_contains_safety_language():
    advisory = build_advisory("Ojota / Ketu", RiskResult(55, "Moderate", {}), 21.4)
    assert "Moderate (55/100)" in advisory
    assert "Human review is required" in advisory
    assert DISCLAIMER in advisory

def test_guide_has_all_ten_pilot_locations():
    assert list(PILOT_LOCATIONS) == [
        "Ojota / Ketu", "Lekki", "Ajah", "Victoria Island", "Ikorodu",
        "Yaba", "Surulere", "Agege", "Lagos Island", "Ikoyi",
    ]

def test_osm_summary_parses_features_and_builds_indicators(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"elements": [
                {"type": "way", "tags": {"highway": "primary", "name": "Test Road"},
                 "center": {"lat": 6.5868, "lon": 3.3834},
                 "geometry": [{"lat": 6.5867, "lon": 3.3833},
                              {"lat": 6.5869, "lon": 3.3835}]},
                {"type": "node", "lat": 6.5870, "lon": 3.3835,
                 "tags": {"amenity": "school", "name": "Test School"}},
                {"type": "way", "tags": {"waterway": "canal"},
                 "center": {"lat": 6.5871, "lon": 3.3836},
                 "geometry": [{"lat": 6.5870, "lon": 3.3835},
                              {"lat": 6.5872, "lon": 3.3837}]},
            ]}

    monkeypatch.setattr("src.data.osm.requests.post", lambda *args, **kwargs: FakeResponse())
    summary = fetch_infrastructure(6.5867, 3.3833)
    assert summary.counts == {"road": 1, "school": 1, "market": 0, "waterway": 1}
    assert 0 < summary.waterway_indicator <= 1
    assert 0 < summary.infrastructure_indicator <= 1
