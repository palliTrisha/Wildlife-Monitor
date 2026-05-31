import folium
from streamlit_folium import st_folium
import streamlit as st
from zone_checker import get_zones

location_history = {}

def update_location_history(assessed_readings):
    for animal in assessed_readings:
        animal_id = animal["animal_id"]
        if animal_id not in location_history:
            location_history[animal_id] = []
        location_history[animal_id].append({
            "lat": animal["latitude"],
            "lon": animal["longitude"],
            "level": animal["level"]
        })
        if len(location_history[animal_id]) > 50:
            location_history[animal_id].pop(0)

def render_map(assessed_readings):
    update_location_history(assessed_readings)

    avg_lat = sum(a["latitude"] for a in assessed_readings) / len(assessed_readings)
    avg_lon = sum(a["longitude"] for a in assessed_readings) / len(assessed_readings)

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

    zones = get_zones()
    for zone in zones:
        color = "red" if zone["type"] == "danger" else "green"
        folium.Circle(
            location=[zone["lat"], zone["lon"]],
            radius=zone["radius_meters"],
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.15,
            tooltip=f"{zone['name']} ({zone['type'].upper()})"
        ).add_to(m)
        folium.Marker(
            location=[zone["lat"], zone["lon"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:11px;color:{color};font-weight:bold;">{zone["name"]}</div>'
            )
        ).add_to(m)

    color_map = {
        "CRITICAL": "red",
        "ELEVATED": "orange",
        "WARNING": "yellow",
        "SAFE": "green"
    }

    for animal in assessed_readings:
        animal_id = animal["animal_id"]
        color = color_map[animal["level"]]
        history = location_history.get(animal_id, [])

        if len(history) > 1:
            trail_coords = [[h["lat"], h["lon"]] for h in history]
            folium.PolyLine(
                trail_coords,
                color=color,
                weight=2.5,
                opacity=0.6
            ).add_to(m)

        folium.CircleMarker(
            location=[animal["latitude"], animal["longitude"]],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=f"{animal['name']} — {animal['level']}",
            popup=folium.Popup(
                f"""
                <b>{animal['name']}</b><br>
                Status: {animal['level']}<br>
                Movement: {animal['movement']}<br>
                Temperature: {animal['temperature']}°C<br>
                Activity: {animal['activity']}<br>
                {animal['message']}
                """,
                max_width=200
            )
        ).add_to(m)

    return m