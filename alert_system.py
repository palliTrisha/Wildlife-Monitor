from __future__ import annotations
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components


def init_alert_state() -> None:
    if "active_alerts" not in st.session_state:
        st.session_state.active_alerts = []
    if "alert_log" not in st.session_state:
        st.session_state.alert_log = []


def check_and_render_alerts(assessed: list[dict]) -> None:
    for animal in assessed:
        aid = animal["animal_id"]
        is_critical = animal.get("level") in ("CRITICAL", "POACHING")
        zone_critical = (animal.get("zone_alert", {}) or {}).get("level") == "CRITICAL"

        if is_critical or zone_critical:
            existing_ids = [a["animal_id"] for a in st.session_state.active_alerts]
            if aid not in existing_ids:
                alert = _build_alert(animal, zone_critical)
                st.session_state.active_alerts.append(alert)
                st.session_state.alert_log.insert(0, {**alert, "acknowledged": False})

    if st.session_state.active_alerts:
        _render_takeover(st.session_state.active_alerts)


def _build_alert(animal: dict, is_zone: bool) -> dict:
    zone = animal.get("zone_alert") or {}
    level = animal.get("level", "CRITICAL")
    if level == "POACHING":
        alert_type = "POACHING DETECTED"
    elif is_zone:
        alert_type = "ZONE BREACH"
    else:
        alert_type = "BIOSENSOR CRITICAL"

    return {
        "animal_id":   animal["animal_id"],
        "animal_name": animal["name"],
        "level":       level,
        "type":        alert_type,
        "message":     zone.get("message") or animal.get("message", "Critical threshold exceeded"),
        "action":      zone.get("action")  or animal.get("action", "Immediate ranger dispatch required"),
        "temperature": animal.get("temperature", "—"),
        "stress":      animal.get("stress_level", "—"),
        "heart_rate":  animal.get("heart_rate", "—"),
        "lat":         animal.get("latitude", "—"),
        "lon":         animal.get("longitude", "—"),
        "timestamp":   datetime.now().strftime("%H:%M:%S"),
        "date":        datetime.now().strftime("%Y-%m-%d"),
    }


def _render_takeover(alerts: list[dict]) -> None:
    cards_html = ""
    for i, alert in enumerate(alerts):
        is_poaching = alert.get("level") == "POACHING"
        border_color = "#aa00ff" if is_poaching else "#ff2222"
        type_color = "#cc44ff" if is_poaching else "#ff4444"

        cards_html += f"""
        <div class="alert-card" id="card-{i}">
            <div class="alert-header">
                <span class="alert-type" style="color:{type_color}">{alert['type']}</span>
                <span class="alert-time">{alert['date']} {alert['timestamp']}</span>
            </div>
            <div class="animal-name">🐾 {alert['animal_name']}</div>
            <div class="alert-message">{alert['message']}</div>
            <div class="vitals">
                <div class="vital"><span class="vital-label">TEMP</span><span class="vital-value">{alert['temperature']}°C</span></div>
                <div class="vital"><span class="vital-label">HEART</span><span class="vital-value">{alert['heart_rate']} bpm</span></div>
                <div class="vital"><span class="vital-label">STRESS</span><span class="vital-value">{alert['stress']}%</span></div>
            </div>
            <div class="gps">📍 {alert['lat']}, {alert['lon']}</div>
            <div class="action-text">⚡ {alert['action']}</div>
        </div>
        """

    alert_count = len(alerts)
    plural = "ALERTS" if alert_count > 1 else "ALERT"
    has_poaching = any(a.get("level") == "POACHING" for a in alerts)
    title_color = "#cc44ff" if has_poaching else "#ff1111"
    title_text = "POACHING DETECTED" if has_poaching else f"CRITICAL {plural}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@400;700;900&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Barlow Condensed', sans-serif; background: #000; overflow: hidden; }}
        .overlay {{ position: fixed; inset: 0; background: #0a0000; z-index: 9999; display: flex; flex-direction: column; align-items: center; justify-content: center; animation: bgpulse 1s ease-in-out infinite alternate; }}
        @keyframes bgpulse {{ from {{ background: #0a0000; }} to {{ background: #1a0000; }} }}
        .scanline {{ position: fixed; inset: 0; background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,0,0,0.03) 2px, rgba(255,0,0,0.03) 4px); pointer-events: none; z-index: 10000; }}
        .header {{ text-align: center; margin-bottom: 24px; }}
        .critical-label {{ font-family: 'Share Tech Mono', monospace; font-size: 11px; letter-spacing: 6px; color: #ff3333; text-transform: uppercase; margin-bottom: 8px; animation: blink 0.6s step-end infinite; }}
        @keyframes blink {{ 50% {{ opacity: 0; }} }}
        .main-title {{ font-size: 72px; font-weight: 900; color: {title_color}; letter-spacing: 8px; line-height: 1; text-shadow: 0 0 40px rgba(255,0,0,0.8), 0 0 80px rgba(255,0,0,0.4); }}
        .alert-count {{ font-family: 'Share Tech Mono', monospace; font-size: 13px; color: #ff6666; letter-spacing: 4px; margin-top: 8px; }}
        .cards-container {{ display: flex; gap: 16px; max-width: 960px; width: 100%; padding: 0 24px; overflow-x: auto; justify-content: center; }}
        .alert-card {{ background: rgba(180,0,0,0.12); border: 1px solid rgba(255,50,50,0.4); border-top: 3px solid #ff2222; border-radius: 4px; padding: 20px; min-width: 280px; flex: 1; max-width: 400px; }}
        .alert-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .alert-type {{ font-family: 'Share Tech Mono', monospace; font-size: 10px; letter-spacing: 3px; background: rgba(255,0,0,0.15); padding: 3px 8px; border-radius: 2px; }}
        .alert-time {{ font-family: 'Share Tech Mono', monospace; font-size: 10px; color: #884444; }}
        .animal-name {{ font-size: 32px; font-weight: 900; color: #ffffff; letter-spacing: 2px; margin-bottom: 8px; }}
        .alert-message {{ font-size: 15px; color: #ffaaaa; margin-bottom: 16px; line-height: 1.4; }}
        .vitals {{ display: flex; gap: 12px; margin-bottom: 12px; }}
        .vital {{ flex: 1; background: rgba(255,0,0,0.08); border: 1px solid rgba(255,0,0,0.2); border-radius: 3px; padding: 8px; text-align: center; }}
        .vital-label {{ display: block; font-family: 'Share Tech Mono', monospace; font-size: 9px; color: #884444; letter-spacing: 2px; margin-bottom: 4px; }}
        .vital-value {{ display: block; font-size: 20px; font-weight: 700; color: #ff6666; }}
        .gps {{ font-family: 'Share Tech Mono', monospace; font-size: 11px; color: #666; margin-bottom: 12px; }}
        .action-text {{ font-size: 13px; font-weight: 700; color: #ffdd44; letter-spacing: 1px; text-transform: uppercase; border-top: 1px solid rgba(255,100,0,0.3); padding-top: 12px; }}
    </style>
    </head>
    <body>
    <div class="overlay">
        <div class="scanline"></div>
        <div class="header">
            <div class="critical-label">⚠ wildlife monitor system ⚠</div>
            <div class="main-title">{title_text}</div>
            <div class="alert-count">{alert_count} UNACKNOWLEDGED EVENT{'S' if alert_count > 1 else ''} — IMMEDIATE ACTION REQUIRED</div>
        </div>
        <div class="cards-container">{cards_html}</div>
    </div>
    <script>
        (function() {{
            try {{
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                function beep(freq, start, duration) {{
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.frequency.value = freq;
                    osc.type = 'square';
                    gain.gain.setValueAtTime(0.3, ctx.currentTime + start);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + duration);
                    osc.start(ctx.currentTime + start);
                    osc.stop(ctx.currentTime + start + duration);
                }}
                for (let i = 0; i < 4; i++) {{
                    beep(880, i * 0.5, 0.2);
                    beep(660, i * 0.5 + 0.25, 0.2);
                }}
            }} catch(e) {{}}
        }})();
    </script>
    </body>
    </html>
    """

    components.html(html, height=600, scrolling=False)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("✅ ACKNOWLEDGED — DISPATCHING RANGER", type="primary", use_container_width=True, key="ack_btn_main"):
            _acknowledge_all()
            st.rerun()


def _acknowledge_all() -> None:
    now = datetime.now().strftime("%H:%M:%S")
    acked_ids = [a["animal_id"] for a in st.session_state.active_alerts]
    for entry in st.session_state.alert_log:
        if entry["animal_id"] in acked_ids and not entry["acknowledged"]:
            entry["acknowledged"] = True
            entry["acknowledged_at"] = now
    st.session_state.active_alerts = []


def render_alert_log() -> None:
    st.subheader("🚨 Alert Log")
    log = st.session_state.get("alert_log", [])

    if not log:
        st.info("No alerts this session. All animals are safe. 🟢")
        return

    total = len(log)
    acked = sum(1 for e in log if e["acknowledged"])
    pending = total - acked

    c1, c2, c3 = st.columns(3)
    c1.metric("Total alerts", total)
    c2.metric("Acknowledged", acked)
    c3.metric("Pending", pending)

    st.divider()

    for entry in log:
        status = "✅ Acknowledged" if entry["acknowledged"] else "🔴 PENDING"
        ack_time = f" at {entry.get('acknowledged_at', '')}" if entry["acknowledged"] else ""
        with st.expander(f"{status}{ack_time} — 🐾 {entry['animal_name']} — {entry['type']} — {entry['date']} {entry['timestamp']}", expanded=not entry["acknowledged"]):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Animal:** {entry['animal_name']}")
                st.markdown(f"**Type:** {entry['type']}")
                st.markdown(f"**Message:** {entry['message']}")
                st.markdown(f"**Action:** {entry['action']}")
            with col2:
                st.markdown(f"**Temperature:** {entry['temperature']}°C")
                st.markdown(f"**Heart rate:** {entry['heart_rate']} bpm")
                st.markdown(f"**Stress:** {entry['stress']}%")
                st.markdown(f"**GPS:** {entry['lat']}, {entry['lon']}")