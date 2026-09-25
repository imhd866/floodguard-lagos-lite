from datetime import datetime

import pytest

from src.ai.advisory import DISCLAIMER, build_advisory
from src.ai.nim_client import NIMServiceError, rewrite_advisory
from src.data.locations import PILOT_LOCATIONS
from src.data.exposure import (load_exposure, low_elevation_indicator,
                               population_exposure_indicator)
from src.data.osm import fetch_infrastructure
from src.data.reports import CommunityFloodReport, build_report_text
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

def test_measured_exposure_cache_covers_all_locations():
    for name in PILOT_LOCATIONS:
        exposure = load_exposure(name)
        assert exposure is not None
        assert 0 <= exposure.low_elevation <= 1
        assert 0 <= exposure.population_exposure <= 1
        assert exposure.population_1_5km > 0

def test_exposure_transformations_are_bounded():
    assert low_elevation_indicator(-2) == 1
    assert low_elevation_indicator(10) == .5
    assert low_elevation_indicator(40) == 0
    assert population_exposure_indicator(-1) == 0
    assert population_exposure_indicator(50_000) == .5
    assert population_exposure_indicator(200_000) == 1

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

def test_community_report_is_reviewable_and_warns_about_emergencies():
    text = build_report_text(CommunityFloodReport(
        area="Ikoyi",
        incident_type="Flooded road",
        severity="Moderate",
        location_description="Near Example Market",
        details="Water is covering one traffic lane.",
        observed_at=datetime(2026, 9, 1, 14, 30),
    ))
    assert "REVIEW BEFORE SENDING" in text
    assert "Ikoyi" in text
    assert "112 or 767" in text
    assert "not been independently verified" in text

def test_nim_rewrite_accepts_only_fact_preserving_output(monkeypatch):
    draft = build_advisory("Ikoyi", RiskResult(55, "Moderate", {}), 21.4)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": draft}}]}

    monkeypatch.setattr("src.ai.nim_client.requests.post", lambda *args, **kwargs: FakeResponse())
    assert rewrite_advisory(draft, "Ikoyi", 55, api_key="test", base_url="https://example.test/v1",
                            model="test/model") == draft

def test_nim_rewrite_rejects_changed_facts(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Everything is safe."}}]}

    monkeypatch.setattr("src.ai.nim_client.requests.post", lambda *args, **kwargs: FakeResponse())
    with pytest.raises(NIMServiceError):
        rewrite_advisory("draft", "Ikoyi", 55, api_key="test",
                         base_url="https://example.test/v1", model="test/model")

def test_nim_rewrite_rejects_changed_rainfall_number(monkeypatch):
    draft = build_advisory("Ikoyi", RiskResult(55, "Moderate", {}), 21.4)
    changed = draft.replace("21.4 mm", "8.0 mm")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": changed}}]}

    monkeypatch.setattr("src.ai.nim_client.requests.post", lambda *args, **kwargs: FakeResponse())
    with pytest.raises(NIMServiceError):
        rewrite_advisory(draft, "Ikoyi", 55, api_key="test",
                         base_url="https://example.test/v1", model="test/model")
