import streamlit as st
import pandas as pd
import time
from simulator import get_all_readings
from threat_engine import assess_all
from map_view import render_map
from streamlit_folium import st_folium
from zone_checker import check_all_zones
from report_exporter import render_export_section
from behavior_analysis import render_insight_cards, BehaviorAnalyzer
from alert_system import init_alert_state, check_and_render_alerts, render_alert_log

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Wildlife Monitor", page_icon="🐾", layout="wide")

st.title("🐾 Wildlife Monitoring System")
st.markdown("Real-time health and location tracking for animal conservation")

# ── Session state init ────────────────────────────────────────────────────────
init_alert_state()

if "history" not in st.session_state:
    st.session_state.history = {}
if "current_map" not in st.session_state:
    st.session_state.current_map = None
if "analyzer" not in st.session_state:
    st.session_state.analyzer = BehaviorAnalyzer()

# ── Live sensor readings ──────────────────────────────────────────────────────
readings = get_all_readings()
assessed = assess_all(readings)
assessed = check_all_zones(assessed)

for animal in assessed:
    aid = animal["animal_id"]
    if aid not in st.session_state.history:
        st.session_state.history[aid] = []
    st.session_state.history[aid].append(animal)
    if len(st.session_state.history[aid]) > 100:
        st.session_state.history[aid] = st.session_state.history[aid][-100:]

history_dfs = {
    aid: pd.DataFrame(rows)
    for aid, rows in st.session_state.history.items()
}
animals_list = [{"id": a["animal_id"], "name": a["name"], "species": a.get("species", "animal")} for a in assessed]

# ── Critical alert takeover ───────────────────────────────────────────────────
check_and_render_alerts(assessed)

# ── Mild alert banners ────────────────────────────────────────────────────────
for a in assessed:
    if a["level"] == "ELEVATED":
        st.warning(f"⚠️ ELEVATED: {a['message']} — {a['action']}")
    elif a["level"] == "WARNING":
        st.warning(f"🟡 WARNING: {a['message']} — {a['action']}")

for a in assessed:
    if a.get("zone_alert"):
        zone = a["zone_alert"]
        if zone["level"] != "CRITICAL":
            st.warning(f"⚠️ ZONE: {zone['message']} — {zone['action']}")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
live_tab, ai_tab, reports_tab, map_tab, alerts_tab = st.tabs([
    "📊 Live Data", "🤖 AI Analysis", "📊 Reports", "🗺️ Map", "🚨 Alert Log"
])

# ── Tab 1: Live Data ──────────────────────────────────────────────────────────
with live_tab:
    cols = st.columns(len(assessed))
    for i, animal in enumerate(assessed):
        with cols[i]:
            if animal["level"] == "POACHING":
                st.error(f"🟣 {animal['name']} ({animal.get('species_display', '')})")
            elif animal["level"] == "CRITICAL":
                st.error(f"🔴 {animal['name']} ({animal.get('species_display', '')})")
            elif animal["level"] == "ELEVATED":
                st.warning(f"🟠 {animal['name']} ({animal.get('species_display', '')})")
            elif animal["level"] == "WARNING":
                st.warning(f"🟡 {animal['name']} ({animal.get('species_display', '')})")
            else:
                st.success(f"🟢 {animal['name']} ({animal.get('species_display', '')})")

            st.metric("Movement", animal["movement"])
            st.metric("Temperature", f"{animal['temperature']}°C")
            st.metric("Heart Rate", f"{animal.get('heart_rate', '—')} bpm")
            st.metric("Stress", f"{animal.get('stress_level', '—')}%")
            st.metric("Activity", animal["activity"])

            score = animal.get("anomaly_score", 0)
            if score >= 75:
                bar_icon = "🔴"
            elif score >= 50:
                bar_icon = "🟠"
            elif score >= 25:
                bar_icon = "🟡"
            else:
                bar_icon = "🟢"
            st.caption(f"{bar_icon} Risk Score: {score}/100")
            st.progress(score / 100)

            st.caption(f"📍 {animal['latitude']}, {animal['longitude']}")
            st.caption(f"ℹ️ {animal['message']}")

    st.markdown("---")

    if assessed:
        st.subheader("🎯 Live Risk Scores")
        score_df = pd.DataFrame([{
            "Animal": a["name"],
            "Risk Score": a.get("anomaly_score", 0)
        } for a in assessed]).set_index("Animal")
        st.bar_chart(score_df, use_container_width=True)

    st.markdown("---")

    history_df_all = pd.concat(history_dfs.values(), ignore_index=True) if history_dfs else pd.DataFrame()

    if not history_df_all.empty:
        st.subheader("📈 Movement Over Time")
        for animal_id in history_df_all["animal_id"].unique():
            animal_df = history_df_all[history_df_all["animal_id"] == animal_id]
            st.line_chart(animal_df.set_index("timestamp")["movement"], use_container_width=True)

        st.subheader("🌡️ Temperature Over Time")
        for animal_id in history_df_all["animal_id"].unique():
            animal_df = history_df_all[history_df_all["animal_id"] == animal_id]
            st.line_chart(animal_df.set_index("timestamp")["temperature"], use_container_width=True)

        st.subheader("❤️ Heart Rate Over Time")
        for animal_id in history_df_all["animal_id"].unique():
            animal_df = history_df_all[history_df_all["animal_id"] == animal_id]
            if "heart_rate" in animal_df.columns:
                st.line_chart(animal_df.set_index("timestamp")["heart_rate"], use_container_width=True)

        st.subheader("😰 Stress Level Over Time")
        for animal_id in history_df_all["animal_id"].unique():
            animal_df = history_df_all[history_df_all["animal_id"] == animal_id]
            if "stress_level" in animal_df.columns:
                st.line_chart(animal_df.set_index("timestamp")["stress_level"], use_container_width=True)

# ── Tab 2: AI Analysis ────────────────────────────────────────────────────────
with ai_tab:
    render_insight_cards(
        animals=animals_list,
        histories=history_dfs,
        analyzer=st.session_state.analyzer,
    )

# ── Tab 3: Reports ────────────────────────────────────────────────────────────
with reports_tab:
    render_export_section(
        animals=animals_list,
        histories=history_dfs,
    )

# ── Tab 4: Map ────────────────────────────────────────────────────────────────
with map_tab:
    st.subheader("🗺️ Live Animal Tracking")
    if st.button("🔄 Refresh Map"):
        st.session_state.current_map = render_map(assessed)
    if st.session_state.current_map is None:
        st.session_state.current_map = render_map(assessed)
    st_folium(st.session_state.current_map, width=700, height=450, returned_objects=[])

# ── Tab 5: Alert Log ──────────────────────────────────────────────────────────
with alerts_tab:
    render_alert_log()

# ── Auto-refresh ──────────────────────────────────────────────────────────────
time.sleep(5)
st.rerun()