import json
import random
from datetime import datetime

# ── Load config ───────────────────────────────────────────────────────────────
with open("config.json", "r") as f:
    config = json.load(f)

animals = config["animals"]
species_profiles = config.get("species_profiles", {})


def get_profile(animal: dict) -> dict:
    species = animal.get("species", "default")
    return species_profiles.get(species, species_profiles["default"])


def get_time_factor(profile: dict) -> float:
    hour = datetime.now().hour
    for window in profile.get("active_hours", []):
        if window[0] <= hour <= window[1]:
            return profile.get("active_factor", 1.5)
    for window in profile.get("rest_hours", []):
        if window[0] <= hour <= window[1]:
            return profile.get("rest_factor", 0.5)
    return 1.0


def generate_reading(animal: dict) -> dict:
    profile = get_profile(animal)
    time_factor = get_time_factor(profile)

    movement = round(random.gauss(profile["movement_baseline"] * time_factor, 0.15), 2)
    movement = max(0.0, min(1.0, movement))

    temp = round(random.gauss(profile["temp_baseline"], profile["temp_std"]), 1)

    heart_rate = round(random.gauss(profile["heart_rate_baseline"], profile["heart_rate_std"]))
    heart_rate = max(10, heart_rate)

    stress_level = round(random.gauss(20, 10))
    stress_level = max(0, min(100, stress_level))

    # Random stress spike
    if random.random() < profile.get("stress_chance", 0.05):
        movement = round(random.uniform(0.8, 1.0), 2)
        temp = round(temp + random.uniform(0.5, 1.5), 1)
        heart_rate = round(heart_rate * random.uniform(1.2, 1.5))
        stress_level = random.randint(70, 100)

    # Random inactivity spike (possible injury)
    if random.random() < profile.get("injury_chance", 0.03):
        movement = round(random.uniform(0.0, 0.05), 2)
        heart_rate = round(heart_rate * random.uniform(0.6, 0.8))
        stress_level = random.randint(60, 90)

    new_lat = animal["starting_lat"] + random.uniform(-0.0002, 0.0002)
    new_lon = animal["starting_lon"] + random.uniform(-0.0002, 0.0002)
    animal["starting_lat"] = new_lat
    animal["starting_lon"] = new_lon

    if movement < 0.2:
        activity = "resting"
    elif movement < 0.4:
        activity = "low"
    elif movement < 0.6:
        activity = "medium"
    elif movement < 0.8:
        activity = "high"
    else:
        activity = "sprinting"

    return {
        "animal_id":       animal["id"],
        "name":            animal["name"],
        "species":         animal.get("species", "unknown"),
        "species_display": animal.get("species_display", animal.get("species", "Unknown").title()),
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latitude":        round(new_lat, 6),
        "longitude":       round(new_lon, 6),
        "movement":        movement,
        "temperature":     temp,
        "heart_rate":      heart_rate,
        "stress_level":    stress_level,
        "activity":        activity,
    }


def get_all_readings() -> list[dict]:
    return [generate_reading(animal) for animal in animals]