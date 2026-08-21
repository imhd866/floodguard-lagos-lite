from src.risk.scoring import RiskResult

DISCLAIMER = ("FloodGuard Lagos Lite is a decision-support and planning tool. "
              "It does not replace official emergency alerts or human judgment.")

def build_advisory(location: str, result: RiskResult, rainfall_24h_mm: float) -> str:
    action = {
        "Low": "Continue routine monitoring and check official weather updates.",
        "Moderate": "Monitor rainfall closely and confirm road access before travel or classes.",
        "High": "Escalate for human review, verify access routes, and consider precautionary schedule changes.",
    }[result.label]
    return (f"FloodGuard advisory for {location}\n\n"
            f"Indicative disruption risk: {result.label} ({result.score}/100)\n"
            f"Forecast rainfall in the next 24 hours: {rainfall_24h_mm:.1f} mm\n\n"
            f"Suggested action: {action}\n\n"
            "Uncertainty: Non-rainfall indicators are prototype area baselines pending validation "
            "with elevation, OSM, population, and historical-water datasets. Human review is required.\n\n"
            f"{DISCLAIMER}")
