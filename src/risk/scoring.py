from dataclasses import dataclass

WEIGHTS = {"rainfall": .35, "low_elevation": .20, "waterway_proximity": .15,
           "historical_water": .15, "infrastructure_exposure": .10,
           "population_exposure": .05}

@dataclass(frozen=True)
class RiskResult:
    score: int
    label: str
    components: dict[str, float]

def rainfall_indicator(total_24h_mm: float, peak_hourly_mm: float) -> float:
    accumulation = min(max(total_24h_mm, 0.0) / 80.0, 1.0)
    intensity = min(max(peak_hourly_mm, 0.0) / 20.0, 1.0)
    return round(.7 * accumulation + .3 * intensity, 4)

def calculate_risk(**inputs: float) -> RiskResult:
    missing = set(WEIGHTS) - set(inputs)
    if missing:
        raise ValueError(f"Missing risk inputs: {sorted(missing)}")
    bounded = {name: min(max(float(inputs[name]), 0.0), 1.0) for name in WEIGHTS}
    score = round(sum(bounded[name] * weight for name, weight in WEIGHTS.items()) * 100)
    label = "Low" if score <= 39 else "Moderate" if score <= 69 else "High"
    return RiskResult(score, label, bounded)
