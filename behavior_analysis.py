from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd
import streamlit as st

from ai_backend import get_backend, AIBackend


@dataclass
class BehaviorInsight:
    animal_id: str
    animal_name: str
    generated_at: datetime
    summary: str
    activity_pattern: str
    health_indicators: str
    risk_assessment: str
    recommendations: list[str]
    confidence: str
    backend_used: str
    error: Optional[str] = None


@dataclass
class AnalysisCache:
    _store: dict[str, tuple[BehaviorInsight, float]] = field(default_factory=dict)
    ttl_seconds: int = 120

    def get(self, key: str) -> Optional[BehaviorInsight]:
        if key not in self._store:
            return None
        insight, ts = self._store[key]
        if time.time() - ts > self.ttl_seconds:
            del self._store[key]
            return None
        return insight

    def set(self, key: str, insight: BehaviorInsight) -> None:
        self._store[key] = (insight, time.time())

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


def get_system_prompt(species: str = "animal") -> str:
    return f"""You are an expert wildlife behaviorist and conservation data analyst.
You receive telemetry data from GPS/sensor collars on wild {species}s and produce concise,
actionable insights for field rangers who may have limited connectivity.

Rules:
- Be specific — reference actual numbers from the data
- Use plain English — rangers are not data scientists
- Flag genuine anomalies only — avoid crying wolf
- Keep recommendations practical and field-actionable
- Consider normal {species} behaviour patterns when interpreting data
- Response must be valid JSON matching the schema provided"""


def build_prompt(animal_id: str, animal_name: str, df: pd.DataFrame, species: str = "animal") -> str:
    if df.empty:
        return f"No data available for {animal_name} ({animal_id})."

    recent = df.tail(30).copy()

    stats: dict = {}
    for col in ["temperature", "heart_rate", "activity_level", "stress_level"]:
        if col in recent.columns:
            stats[col] = {
                "mean": round(float(recent[col].mean()), 2),
                "min":  round(float(recent[col].min()), 2),
                "max":  round(float(recent[col].max()), 2),
                "last": round(float(recent[col].iloc[-1]), 2),
            }

    threat_counts = (
        recent["level"].value_counts().to_dict()
        if "level" in recent.columns else {}
    )

    zone_alerts = (
        recent[recent["zone_alert"].notna()]["zone_alert"].tolist()
        if "zone_alert" in recent.columns else []
    )

    gps_rows = recent[["latitude", "longitude"]].dropna() if "latitude" in recent.columns else pd.DataFrame()
    gps_summary = ""
    if not gps_rows.empty:
        gps_summary = (
            f"GPS range — lat [{gps_rows['latitude'].min():.4f}, {gps_rows['latitude'].max():.4f}], "
            f"lon [{gps_rows['longitude'].min():.4f}, {gps_rows['longitude'].max():.4f}]"
        )

    time_range = ""
    if "timestamp" in recent.columns:
        time_range = f"{recent['timestamp'].iloc[0]}  →  {recent['timestamp'].iloc[-1]}"

    prompt = f"""Analyze the following telemetry data for **{species.title()}** named **{animal_name}** (ID: {animal_id}).

Time window: {time_range or 'unknown'}
Data points: {len(recent)} readings

Sensor statistics (last 30 readings):
{stats}

Threat level distribution: {threat_counts}
Zone alerts triggered: {zone_alerts if zone_alerts else 'None'}
{gps_summary}

Respond ONLY with a JSON object (no markdown, no preamble) using this exact schema:
{{
  "summary": "<one sentence headline about this animal right now>",
  "activity_pattern": "<2-3 sentences about movement, rest cycles, GPS range>",
  "health_indicators": "<2-3 sentences about temperature, heart rate, stress>",
  "risk_assessment": "<2-3 sentences interpreting threat levels and zone alerts>",
  "recommendations": ["<action 1>", "<action 2>", "<action 3>"],
  "confidence": "High" | "Medium" | "Low"
}}"""
    return prompt


class BehaviorAnalyzer:
    def __init__(self, backend: Optional[AIBackend] = None):
        self._backend = backend or get_backend()
        self._cache = AnalysisCache()

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def analyze(
        self,
        animal_id: str,
        animal_name: str,
        history: pd.DataFrame,
        species: str = "animal",
        force_refresh: bool = False,
    ) -> BehaviorInsight:
        cache_key = f"{animal_id}:{len(history)}"
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        prompt = build_prompt(animal_id, animal_name, history, species)
        system = get_system_prompt(species)

        try:
            raw = self._backend.complete(prompt, system=system)
            parsed = _parse_ai_response(raw)
            insight = BehaviorInsight(
                animal_id=animal_id,
                animal_name=animal_name,
                generated_at=datetime.now(),
                backend_used=self._backend.name,
                **parsed,
            )
        except Exception as exc:
            insight = BehaviorInsight(
                animal_id=animal_id,
                animal_name=animal_name,
                generated_at=datetime.now(),
                backend_used=self._backend.name,
                summary="Analysis failed — see error below.",
                activity_pattern="—",
                health_indicators="—",
                risk_assessment="—",
                recommendations=[],
                confidence="Low",
                error=str(exc),
            )

        self._cache.set(cache_key, insight)
        return insight

    def analyze_all(
        self,
        animals: list[dict],
        histories: dict[str, pd.DataFrame],
        force_refresh: bool = False,
    ) -> list[BehaviorInsight]:
        results = []
        for animal in animals:
            aid = animal["id"]
            name = animal.get("name", aid)
            species = animal.get("species", "animal")
            hist = histories.get(aid, pd.DataFrame())
            results.append(self.analyze(aid, name, hist, species, force_refresh))
        return results


def _parse_ai_response(raw: str) -> dict:
    import json, re
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in AI response:\n{raw[:300]}")
    data = json.loads(match.group())
    return {
        "summary":           data.get("summary", "No summary."),
        "activity_pattern":  data.get("activity_pattern", "—"),
        "health_indicators": data.get("health_indicators", "—"),
        "risk_assessment":   data.get("risk_assessment", "—"),
        "recommendations":   data.get("recommendations", []),
        "confidence":        data.get("confidence", "Low"),
    }


_CONFIDENCE_COLOR = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}


def render_insight_card(insight: BehaviorInsight) -> None:
    confidence_dot = _CONFIDENCE_COLOR.get(insight.confidence, "⚪")
    label = f"🐾 **{insight.animal_name}** — {insight.summary}"

    with st.expander(label, expanded=True):
        if insight.error:
            st.error(f"Analysis error: {insight.error}")
            return

        col1, col2, col3 = st.columns(3)
        col1.metric("Confidence", f"{confidence_dot} {insight.confidence}")
        col2.metric("Backend", insight.backend_used.split("(")[0].strip())
        col3.metric("Generated", insight.generated_at.strftime("%H:%M:%S"))

        st.divider()

        st.markdown("##### 🏃 Activity Pattern")
        st.write(insight.activity_pattern)

        st.markdown("##### 🩺 Health Indicators")
        st.write(insight.health_indicators)

        st.markdown("##### ⚠️ Risk Assessment")
        st.write(insight.risk_assessment)

        if insight.recommendations:
            st.markdown("##### 📋 Ranger Recommendations")
            for rec in insight.recommendations:
                st.markdown(f"- {rec}")


def render_insight_cards(
    animals: list[dict],
    histories: dict[str, pd.DataFrame],
    analyzer: Optional[BehaviorAnalyzer] = None,
) -> None:
    if analyzer is None:
        analyzer = BehaviorAnalyzer()

    col_title, col_btn = st.columns([4, 1])
    with col_title:
        st.subheader("🤖 AI Behavioral Analysis")
        st.caption(f"Powered by **{analyzer.backend_name}** · updates every 2 min")
    with col_btn:
        st.write("")
        force = st.button("🔄 Refresh All", use_container_width=True)

    st.divider()

    if not animals:
        st.info("No animals configured. Add entries to config.json.")
        return

    insights_key = "behavior_insights"
    if force or insights_key not in st.session_state:
        progress = st.progress(0, text="Analyzing animal behaviors…")
        results: list[BehaviorInsight] = []
        for i, animal in enumerate(animals):
            aid = animal["id"]
            name = animal.get("name", aid)
            species = animal.get("species", "animal")
            hist = histories.get(aid, pd.DataFrame())
            results.append(analyzer.analyze(aid, name, hist, species, force_refresh=force))
            progress.progress((i + 1) / len(animals), text=f"Analyzed {name}…")
        progress.empty()
        st.session_state[insights_key] = results
    else:
        results = st.session_state[insights_key]

    for insight in results:
        render_insight_card(insight)
        st.write("")


if __name__ == "__main__":
    print("behavior_analysis.py loaded successfully.")