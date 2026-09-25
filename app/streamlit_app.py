import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ai.advisory import DISCLAIMER, build_advisory
from src.ai.nim_client import NIMServiceError, rewrite_advisory
from src.data.exposure import load_exposure, load_lagos_boundary
from src.data.locations import PILOT_LOCATIONS
from src.data.osm import OSMServiceError, fetch_infrastructure
from src.data.reports import (CITIZENS_GATE_URL, CITIZENS_GATE_WHATSAPP_URL,
                              EMERGENCY_NUMBERS, NON_EMERGENCY_PHONE,
                              CommunityFloodReport, build_report_text)
from src.data.weather import WeatherServiceError, fetch_rainfall
from src.risk.scoring import calculate_risk, rainfall_indicator

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

st.set_page_config(page_title="FloodGuard Lagos Lite", page_icon="🌧️", layout="wide")
st.title("FloodGuard Lagos Lite")
st.caption("Indicative flood disruption risk for planning - not flood prediction")
location_name = st.selectbox("Pilot area", list(PILOT_LOCATIONS))
location = PILOT_LOCATIONS[location_name]
exposure = load_exposure(location_name)
lagos_boundary = load_lagos_boundary()
st.caption(f"10 pilot areas available · map radius: 1.5 km around {location_name}")

nim_api_key = os.getenv("NVIDIA_API_KEY", "")
nim_base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
nim_model = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")
nim_configured = bool(nim_api_key and nim_model)
use_nim = st.checkbox("Improve advisory wording with NVIDIA NIM",
                      value=nim_configured, disabled=not nim_configured)
if not nim_configured:
    st.caption("Optional AI rewriting is off. Add NVIDIA_API_KEY to .env to enable it; "
               "risk scoring and advisories still work without AI.")

if st.button("Check live risk", type="primary", use_container_width=True):
    try:
        with st.spinner("Fetching the 72-hour rainfall forecast..."):
            forecast = fetch_rainfall(location["latitude"], location["longitude"])
    except WeatherServiceError as exc:
        st.error(str(exc))
    else:
        infrastructure = None
        try:
            with st.spinner("Loading nearby OpenStreetMap infrastructure..."):
                infrastructure = fetch_infrastructure(location["latitude"], location["longitude"])
        except OSMServiceError as exc:
            st.warning(f"{exc} Using the documented prototype baselines for this result.")

        rain = rainfall_indicator(forecast.next_24h_mm, forecast.peak_hourly_mm)
        factors = {k: v for k, v in location.items() if k not in {"latitude", "longitude"}}
        if exposure is not None:
            factors["low_elevation"] = exposure.low_elevation
            factors["population_exposure"] = exposure.population_exposure
        if infrastructure is not None:
            factors["waterway_proximity"] = infrastructure.waterway_indicator
            factors["infrastructure_exposure"] = infrastructure.infrastructure_indicator
        risk = calculate_risk(rainfall=rain, **factors)
        left, middle, right = st.columns(3)
        left.metric("Risk level", risk.label)
        middle.metric("Risk score", f"{risk.score}/100")
        right.metric("Next 24h rainfall", f"{forecast.next_24h_mm:.1f} mm")
        st.subheader("72-hour rainfall")
        chart = pd.DataFrame(forecast.hourly).set_index("time")
        st.bar_chart(chart, y="precipitation_mm", x_label="Forecast time", y_label="Rainfall (mm)")

        if infrastructure is not None:
            st.subheader("Nearby OpenStreetMap infrastructure")
            map_left, map_right = st.columns([3, 1])
            paths = []
            point_rows = []
            colors = {"road": [100, 116, 139], "waterway": [14, 165, 233],
                      "school": [250, 204, 21], "market": [249, 115, 22]}
            for feature in infrastructure.features:
                if len(feature.geometry) >= 2:
                    paths.append({"path": [[p["longitude"], p["latitude"]]
                                           for p in feature.geometry],
                                  "color": colors[feature.category], "name": feature.name,
                                  "category": feature.category.title()})
                if feature.category in {"school", "market"}:
                    point_rows.append({"longitude": feature.longitude,
                                       "latitude": feature.latitude,
                                       "name": feature.name,
                                       "category": feature.category.title(),
                                       "color": colors[feature.category]})
            layers = []
            if lagos_boundary is not None:
                layers.append(pdk.Layer("GeoJsonLayer", lagos_boundary, stroked=True,
                                        filled=False, get_line_color=[16, 185, 129, 180],
                                        line_width_min_pixels=2, pickable=False))
            layers.append(pdk.Layer("PathLayer", paths, get_path="path", get_color="color",
                                    width_min_pixels=2, pickable=True))
            if point_rows:
                layers.append(pdk.Layer("ScatterplotLayer", point_rows,
                                        get_position="[longitude, latitude]", get_fill_color="color",
                                        get_radius=45, radius_min_pixels=4, pickable=True))
            deck = pdk.Deck(layers=layers,
                            initial_view_state=pdk.ViewState(latitude=location["latitude"],
                                                             longitude=location["longitude"],
                                                             zoom=13.5),
                            tooltip={"text": "{category}: {name}"})
            map_left.pydeck_chart(deck, use_container_width=True)
            count_table = pd.DataFrame({"Feature": ["Roads", "Schools", "Markets", "Waterways"],
                                        "Mapped count": [infrastructure.counts[key]
                                                         for key in ("road", "school", "market", "waterway")]})
            map_right.dataframe(count_table, hide_index=True, use_container_width=True)
            map_right.caption("© OpenStreetMap contributors · queried live via Overpass")

        st.subheader("Why this result")
        components = pd.DataFrame({"Factor": list(risk.components),
                                   "Indicator (0-1)": list(risk.components.values())})
        st.dataframe(components, hide_index=True, use_container_width=True)
        if infrastructure is None:
            if exposure is None:
                st.info("Non-rainfall factors are explicit prototype baselines and require dataset validation.")
            else:
                st.info("Elevation and population use the cached measured datasets below. "
                        "Waterway, infrastructure, and historical-water factors are explicit "
                        "prototype fallbacks because the live OSM query was unavailable.")
        else:
            if exposure is None:
                st.info("Waterway and infrastructure indicators are derived from the live OSM query. "
                        "Elevation, historical-water, and population factors remain prototype baselines.")
            else:
                st.info("Waterway and infrastructure indicators are derived from live OSM data. "
                        "Elevation and population use the cached measured datasets below; only "
                        "historical-water recurrence remains a prototype baseline.")
        if exposure is not None:
            st.subheader("Measured exposure data")
            measured = pd.DataFrame({
                "Measure": ["Surface elevation", "Estimated population within 1.5 km"],
                "Value": [f"{exposure.elevation_m:.1f} m",
                          f"{exposure.population_1_5km:,}"],
                "Source": [exposure.elevation_source, exposure.population_source],
            })
            st.dataframe(measured, hide_index=True, use_container_width=True)
            st.caption(f"Cached {exposure.retrieved_at} · Lagos boundary: geoBoundaries CC BY 4.0 · "
                       "DEM is a surface model, not a surveyed terrain height.")
        st.subheader("Copy-ready advisory")
        draft_advisory = build_advisory(location_name, risk, forecast.next_24h_mm)
        advisory = draft_advisory
        advisory_source = "Verified rule-based advisory"
        if use_nim:
            try:
                advisory = rewrite_advisory(draft_advisory, location_name, risk.score,
                                            api_key=nim_api_key, base_url=nim_base_url,
                                            model=nim_model)
                advisory_source = f"NVIDIA NIM wording · verified facts · {nim_model}"
            except NIMServiceError:
                st.warning("AI rewriting was unavailable or failed verification. "
                           "Showing the verified rule-based advisory instead.")
        st.code(advisory, language=None)
        st.caption(advisory_source)

st.divider()
st.warning(DISCLAIMER)

st.header("Report flooding or blocked drainage")
st.error("Immediate danger or rescue needed? Call 112 or 767. Do not wait for an online report.")
emergency_left, emergency_right = st.columns(2)
emergency_left.link_button(f"Call {EMERGENCY_NUMBERS[0]}", "tel:112",
                           use_container_width=True, type="primary")
emergency_right.link_button(f"Call {EMERGENCY_NUMBERS[1]}", "tel:767",
                            use_container_width=True, type="primary")

st.subheader("Prepare a non-emergency community report")
st.caption("FloodGuard prepares the text in the current session for your review. It does not "
           "send it, save it to a database, or claim that Lagos State has received it.")
with st.form("community_report_form"):
    report_area = st.selectbox("Area", list(PILOT_LOCATIONS), key="report_area")
    report_type = st.selectbox("Incident type", ["Flooded road", "Blocked drainage",
                                                  "Flooded home/business", "Unsafe access route",
                                                  "Other"])
    report_severity = st.selectbox("Observed severity", ["Minor", "Moderate", "Severe"])
    observed_date = st.date_input("Date observed")
    observed_time = st.time_input("Time observed")
    location_description = st.text_input("Address or nearby landmark *",
                                         placeholder="Street, bus stop, school, market, or landmark")
    report_details = st.text_area("What did you observe? *",
                                  placeholder="Describe water depth, affected access, people at risk, or blockage")
    prepare_report = st.form_submit_button("Prepare report for review", type="primary",
                                           use_container_width=True)

if prepare_report:
    try:
        report = CommunityFloodReport(
            area=report_area,
            incident_type=report_type,
            severity=report_severity,
            location_description=location_description,
            details=report_details,
            observed_at=datetime.combine(observed_date, observed_time),
        )
        st.session_state["prepared_report"] = build_report_text(report)
    except ValueError as exc:
        st.error(str(exc))

if prepared_report := st.session_state.get("prepared_report"):
    st.success("Report prepared. Review it before choosing an official reporting channel.")
    st.code(prepared_report, language=None)
    st.download_button("Download report as text", prepared_report,
                       file_name="floodguard-community-report.txt", mime="text/plain")

st.subheader("Official Lagos State reporting channels")
channel_left, channel_middle, channel_right = st.columns(3)
channel_left.link_button("Open Citizens Gate", CITIZENS_GATE_URL, use_container_width=True)
channel_middle.link_button("Citizens Gate WhatsApp", CITIZENS_GATE_WHATSAPP_URL,
                          use_container_width=True)
channel_right.link_button(f"Call {NON_EMERGENCY_PHONE}", f"tel:{NON_EMERGENCY_PHONE}",
                         use_container_width=True)
st.caption("Official channels verified from Lagos State Citizens Gate. Contact details can change; "
           "confirm them on the official site before public deployment.")
