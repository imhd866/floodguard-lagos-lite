import sys
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ai.advisory import DISCLAIMER, build_advisory
from src.data.locations import PILOT_LOCATIONS
from src.data.osm import OSMServiceError, fetch_infrastructure
from src.data.weather import WeatherServiceError, fetch_rainfall
from src.risk.scoring import calculate_risk, rainfall_indicator

st.set_page_config(page_title="FloodGuard Lagos Lite", page_icon="🌧️", layout="wide")
st.title("FloodGuard Lagos Lite")
st.caption("Indicative flood disruption risk for planning - not flood prediction")
location_name = st.selectbox("Pilot area", list(PILOT_LOCATIONS))
location = PILOT_LOCATIONS[location_name]
st.caption(f"10 pilot areas available · map radius: 1.5 km around {location_name}")

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
            layers = [pdk.Layer("PathLayer", paths, get_path="path", get_color="color",
                                width_min_pixels=2, pickable=True)]
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
            st.info("Non-rainfall factors are explicit prototype baselines and require dataset validation.")
        else:
            st.info("Waterway and infrastructure indicators are derived from the live OSM query. "
                    "Elevation, historical-water, and population factors remain prototype baselines.")
        st.subheader("Copy-ready advisory")
        st.code(build_advisory(location_name, risk, forecast.next_24h_mm), language=None)

st.divider()
st.warning(DISCLAIMER)
