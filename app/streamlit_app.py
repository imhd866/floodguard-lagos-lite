import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ai.advisory import DISCLAIMER, build_advisory
from src.data.locations import PILOT_LOCATIONS
from src.data.weather import WeatherServiceError, fetch_rainfall
from src.risk.scoring import calculate_risk, rainfall_indicator

st.set_page_config(page_title="FloodGuard Lagos Lite", page_icon="🌧️", layout="wide")
st.title("FloodGuard Lagos Lite")
st.caption("Indicative flood disruption risk for planning - not flood prediction")
location_name = st.selectbox("Pilot area", list(PILOT_LOCATIONS))
location = PILOT_LOCATIONS[location_name]

if st.button("Check live risk", type="primary", use_container_width=True):
    try:
        with st.spinner("Fetching the 72-hour rainfall forecast..."):
            forecast = fetch_rainfall(location["latitude"], location["longitude"])
    except WeatherServiceError as exc:
        st.error(str(exc))
    else:
        rain = rainfall_indicator(forecast.next_24h_mm, forecast.peak_hourly_mm)
        factors = {k: v for k, v in location.items() if k not in {"latitude", "longitude"}}
        risk = calculate_risk(rainfall=rain, **factors)
        left, middle, right = st.columns(3)
        left.metric("Risk level", risk.label)
        middle.metric("Risk score", f"{risk.score}/100")
        right.metric("Next 24h rainfall", f"{forecast.next_24h_mm:.1f} mm")
        st.subheader("72-hour rainfall")
        chart = pd.DataFrame(forecast.hourly).set_index("time")
        st.bar_chart(chart, y="precipitation_mm", x_label="Forecast time", y_label="Rainfall (mm)")
        st.subheader("Why this result")
        components = pd.DataFrame({"Factor": list(risk.components),
                                   "Indicator (0-1)": list(risk.components.values())})
        st.dataframe(components, hide_index=True, use_container_width=True)
        st.info("Non-rainfall factors are explicit prototype baselines and require dataset validation.")
        st.subheader("Copy-ready advisory")
        st.code(build_advisory(location_name, risk, forecast.next_24h_mm), language=None)

st.divider()
st.warning(DISCLAIMER)
