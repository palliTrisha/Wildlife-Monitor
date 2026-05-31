import streamlit as st
import pandas as pd
import time
from simulator import get_all_readings
from threat_engine import assess_all
from map_view import render_map
from streamlit_folium import st_folium
from zone_checker import check_all_zones
from report_exporter import render_export_section

ai_tab, reports_tab, map_tab, alerts_tab = st.tabs([
    "🤖 AI Analysis", "📊 Reports", "🗺️ Map", "🚨 Alerts"
])

with reports_tab:
    render_export_section(
        animals=config["animals"],
        histories=st.session_state.history,
    )
st.set_page_config(
    page_title="Wildlife Monitor",
    page_icon="🐆",
    layout="wide"
)

st.title("🐆 Jaguar Wildlife Monitoring System")
st.markdown("Real-time health and location tracking for jaguar conservation")

if "history" not in st.session_state:
    st.session_state.history = []

readings = get_all_readings()
assessed = assess_all(readings)
assessed = check_all_zones(assessed)

st.session_state.history.extend(assessed)
if len(st.session_state.history) > 100:
    st.session_state.history = st.session_state.history[-100:]

# Alert Banner
critical = [a for a in assessed if a["level"] == "CRITICAL"]
elevated = [a for a in assessed if a["level"] == "ELEVATED"]

if critical:
    for a in critical:
        st.error(f"🚨 CRITICAL: {a['message']} — {a['action']}")
elif elevated:
    for a in elevated:
        st.warning(f"⚠️ ELEVATED: {a['message']} — {a['action']}")

for a in assessed:
    if a.get("zone_alert"):
        zone = a["zone_alert"]
        if zone["level"] == "CRITICAL":
            st.error(f"🚨 ZONE: {zone['message']} — {zone['action']}")
        else:
            st.warning(f"⚠️ ZONE: {zone['message']} — {zone['action']}")

st.markdown("---")

tab1, tab2 = st.tabs(["📊 Live Data", "🗺️ Map"])

with tab1:
    cols = st.columns(len(assessed))
    for i, animal in enumerate(assessed):
        with cols[i]:
            if animal["level"] == "CRITICAL":
                st.error(f"🔴 {animal['name']}")
            elif animal["level"] == "ELEVATED":
                st.warning(f"🟠 {animal['name']}")
            elif animal["level"] == "WARNING":
                st.warning(f"🟡 {animal['name']}")
            else:
                st.success(f"🟢 {animal['name']}")

            st.metric("Movement", animal["movement"])
            st.metric("Temperature", f"{animal['temperature']}°C")
            st.metric("Activity", animal["activity"])
            st.caption(f"📍 {animal['latitude']}, {animal['longitude']}")
            st.caption(f"ℹ️ {animal['message']}")

    st.markdown("---")
    history_df = pd.DataFrame(st.session_state.history)

    if not history_df.empty:
        st.subheader("📈 Movement Over Time")
        for animal_id in history_df["animal_id"].unique():
            animal_df = history_df[history_df["animal_id"] == animal_id]
            st.line_chart(animal_df.set_index("timestamp")["movement"],
                         use_container_width=True)

        st.subheader("🌡️ Temperature Over Time")
        for animal_id in history_df["animal_id"].unique():
            animal_df = history_df[history_df["animal_id"] == animal_id]
            st.line_chart(animal_df.set_index("timestamp")["temperature"],
                         use_container_width=True)

with tab2:
    st.subheader("🗺️ Live Animal Tracking")
    if st.button("🔄 Refresh Map"):
        st.session_state.current_map = render_map(assessed)

    if "current_map" not in st.session_state:
        st.session_state.current_map = render_map(assessed)

    st_folium(st.session_state.current_map, width=700, height=450, returned_objects=[])

time.sleep(5)
st.rerun()