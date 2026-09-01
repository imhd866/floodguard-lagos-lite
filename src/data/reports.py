from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


CITIZENS_GATE_URL = "https://citizensgate.lagosstate.gov.ng/"
CITIZENS_GATE_WHATSAPP_URL = "https://wa.me/2349040513849"
NON_EMERGENCY_PHONE = "+2348000024842"
EMERGENCY_NUMBERS = ("112", "767")


@dataclass(frozen=True)
class CommunityFloodReport:
    area: str
    incident_type: str
    severity: str
    location_description: str
    details: str
    observed_at: datetime


def build_report_text(report: CommunityFloodReport) -> str:
    required = (report.area, report.incident_type, report.severity,
                report.location_description, report.details)
    if any(not value.strip() for value in required):
        raise ValueError("Complete all required report fields.")
    return (
        "COMMUNITY FLOOD REPORT - REVIEW BEFORE SENDING\n\n"
        f"Pilot area: {report.area}\n"
        f"Incident type: {report.incident_type}\n"
        f"Observed severity: {report.severity}\n"
        f"Observed at: {report.observed_at:%Y-%m-%d %H:%M}\n"
        f"Address / landmark: {report.location_description.strip()}\n\n"
        f"Details:\n{report.details.strip()}\n\n"
        "This community observation has not been independently verified by FloodGuard Lagos Lite. "
        "For immediate danger, call Lagos emergency services on 112 or 767."
    )
