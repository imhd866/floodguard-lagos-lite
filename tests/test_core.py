from src.ai.advisory import DISCLAIMER, build_advisory
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
