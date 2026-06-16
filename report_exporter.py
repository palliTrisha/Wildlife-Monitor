"""
report_exporter.py — Export wildlife session data to CSV (and optional Excel)

Usage (standalone):
    from report_exporter import export_session_csv, export_all_animals_csv

Usage (Streamlit dashboard):
    from report_exporter import render_export_sidebar
    render_export_sidebar(animals, histories)
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import pandas as pd


# ── Core export functions ─────────────────────────────────────────────────────

def export_animal_csv(animal_id: str, df: pd.DataFrame) -> bytes:
    if df.empty:
        return b""
    out = df.copy()
    out.insert(0, "animal_id", animal_id)
    return out.to_csv(index=False).encode("utf-8")


def export_all_animals_csv(
    animals: list[dict],
    histories: dict[str, pd.DataFrame],
) -> bytes:
    frames = []
    for animal in animals:
        aid = animal["id"]
        name = animal.get("name", aid)
        df = histories.get(aid, pd.DataFrame())
        if df.empty:
            continue
        chunk = df.copy()
        if "animal_id" not in chunk.columns:
            chunk.insert(0, "animal_id", aid)
        if "animal_name" not in chunk.columns:
            chunk.insert(0, "animal_name", name)
        frames.append(chunk)

    if not frames:
        return b"animal_id,animal_name\n(no data)\n".encode()

    combined = pd.concat(frames, ignore_index=True)
    if "timestamp" in combined.columns:
        combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined.to_csv(index=False).encode("utf-8")


def export_alerts_csv(
    animals: list[dict],
    histories: dict[str, pd.DataFrame],
) -> bytes:
    frames = []
    alert_levels = {"WARNING", "ELEVATED", "CRITICAL", "POACHING"}

    for animal in animals:
        aid = animal["id"]
        name = animal.get("name", aid)
        df = histories.get(aid, pd.DataFrame())
        if df.empty or "level" not in df.columns:
            continue
        alerts = df[df["level"].isin(alert_levels)].copy()
        if alerts.empty:
            continue
        if "animal_id" not in alerts.columns:
            alerts.insert(0, "animal_id", aid)
        if "animal_name" not in alerts.columns:
            alerts.insert(0, "animal_name", name)
        frames.append(alerts)

    if not frames:
        empty_df = pd.DataFrame(columns=["animal_id", "animal_name", "timestamp", "level"])
        return empty_df.to_csv(index=False).encode("utf-8")

    combined = pd.concat(frames, ignore_index=True)
    if "timestamp" in combined.columns:
        combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined.to_csv(index=False).encode("utf-8")


def export_summary_csv(
    animals: list[dict],
    histories: dict[str, pd.DataFrame],
) -> bytes:
    rows = []
    for animal in animals:
        aid = animal["id"]
        name = animal.get("name", aid)
        df = histories.get(aid, pd.DataFrame())

        row: dict = {"animal_id": aid, "animal_name": name}

        if df.empty:
            row["readings"] = 0
            rows.append(row)
            continue

        row["readings"] = len(df)

        if "timestamp" in df.columns:
            row["session_start"] = df["timestamp"].iloc[0]
            row["session_end"]   = df["timestamp"].iloc[-1]

        for col in ["temperature", "heart_rate", "activity_level", "stress_level", "anomaly_score"]:
            if col in df.columns:
                row[f"{col}_mean"] = round(df[col].mean(), 2)
                row[f"{col}_max"]  = round(df[col].max(), 2)
                row[f"{col}_min"]  = round(df[col].min(), 2)

        if "level" in df.columns:
            counts = df["level"].value_counts()
            for level in ["SAFE", "WARNING", "ELEVATED", "CRITICAL", "POACHING"]:
                row[f"threat_{level.lower()}"] = int(counts.get(level, 0))

        if "zone_alert" in df.columns:
            row["zone_alerts_total"] = int(df["zone_alert"].notna().sum())

        rows.append(row)

    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def export_excel_report(
    animals: list[dict],
    histories: dict[str, pd.DataFrame],
) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.read_csv(io.BytesIO(export_summary_csv(animals, histories))).to_excel(
            writer, sheet_name="Summary", index=False)
        pd.read_csv(io.BytesIO(export_all_animals_csv(animals, histories))).to_excel(
            writer, sheet_name="All Readings", index=False)
        pd.read_csv(io.BytesIO(export_alerts_csv(animals, histories))).to_excel(
            writer, sheet_name="Alerts Only", index=False)
    return buf.getvalue()


# ── Filename helpers ──────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def session_filename(prefix: str, ext: str = "csv") -> str:
    return f"wildlife_monitor_{prefix}_{_ts()}.{ext}"


# ── Streamlit UI ──────────────────────────────────────────────────────────────

def render_export_section(
    animals: list[dict],
    histories: dict[str, pd.DataFrame],
) -> None:
    import streamlit as st

    st.subheader("📊 Historical Reports")
    st.caption("Export session data collected since the dashboard started.")

    total_readings = sum(len(h) for h in histories.values())
    total_alerts = sum(
        int(h["level"].isin({"WARNING", "ELEVATED", "CRITICAL", "POACHING"}).sum())
        for h in histories.values()
        if "level" in h.columns
    )
    active_animals = sum(1 for h in histories.values() if not h.empty)

    c1, c2, c3 = st.columns(3)
    c1.metric("Animals tracked", active_animals)
    c2.metric("Total readings", f"{total_readings:,}")
    c3.metric("Alert events", total_alerts)

    st.divider()
    st.markdown("#### Download options")

    col_a, col_b = st.columns(2)

    with col_a:
        st.download_button(
            label="📋 Session Summary (CSV)",
            data=export_summary_csv(animals, histories),
            file_name=session_filename("summary"),
            mime="text/csv",
            use_container_width=True,
        )
        st.download_button(
            label="🚨 Alerts Log (CSV)",
            data=export_alerts_csv(animals, histories),
            file_name=session_filename("alerts"),
            mime="text/csv",
            use_container_width=True,
        )

    with col_b:
        st.download_button(
            label="📦 Full Session Data (CSV)",
            data=export_all_animals_csv(animals, histories),
            file_name=session_filename("full"),
            mime="text/csv",
            use_container_width=True,
        )
        try:
            import openpyxl  # noqa: F401
            st.download_button(
                label="📗 Full Report (Excel)",
                data=export_excel_report(animals, histories),
                file_name=session_filename("report", "xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except ImportError:
            st.info("Install `openpyxl` for Excel export: `pip install openpyxl`")

    st.divider()
    st.markdown("#### Per-animal export")

    animal_options = {a.get("name", a["id"]): a["id"] for a in animals}

    if not animal_options:
        st.info("No animals configured.")
        return

    selected_name = st.selectbox("Choose animal", list(animal_options.keys()))
    selected_id = animal_options[selected_name]
    selected_df = histories.get(selected_id, pd.DataFrame())

    if selected_df.empty:
        st.warning(f"No data collected yet for {selected_name}.")
    else:
        st.write(f"**{len(selected_df):,} readings** collected this session")
        st.dataframe(selected_df.tail(10), use_container_width=True)
        st.download_button(
            label=f"⬇️ Download {selected_name} data (CSV)",
            data=export_animal_csv(selected_id, selected_df),
            file_name=session_filename(f"{selected_id}"),
            mime="text/csv",
            use_container_width=True,
        )