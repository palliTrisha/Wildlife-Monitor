import json
import random
import math
from datetime import datetime

# Read the config file
with open("config.json", "r") as f:
    config = json.load(f)

animals = config["animals"]
baseline_temp = config["simulation"]["temperature_baseline"]
baseline_movement = config["simulation"]["movement_baseline"]

def get_time_of_day_factor():
    """Jaguars are more active at dawn and dusk"""
    hour = datetime.now().hour
    if 5 <= hour <= 8 or 18 <= hour <= 22:
        return 1.5
    elif 10 <= hour <= 16:
        return 0.5
    else:
        return 1.0

def generate_reading(animal):
    """Generate one sensor reading for an animal"""
    time_factor = get_time_of_day_factor()

    # Movement (0.0 to 1.0)
    movement = round(random.gauss(baseline_movement * time_factor, 0.15), 2)
    movement = max(0.0, min(1.0, movement))

    # Temperature
    temp = round(random.gauss(baseline_temp, 0.3), 1)

    # Random stress spike (5% chance)
    if random.random() < 0.05:
        movement = round(random.uniform(0.8, 1.0), 2)
        temp = round(temp + random.uniform(0.5, 1.5), 1)

    # Random inactivity spike (3% chance - possible injury)
    if random.random() < 0.03:
        movement = round(random.uniform(0.0, 0.05), 2)

    # Simulate GPS movement
    new_lat = animal["starting_lat"] + random.uniform(-0.0002, 0.0002)
    new_lon = animal["starting_lon"] + random.uniform(-0.0002, 0.0002)
    animal["starting_lat"] = new_lat
    animal["starting_lon"] = new_lon

    # Activity level
    if movement < 0.2:
        activity = "low"
    elif movement < 0.6:
        activity = "medium"
    else:
        activity = "high"

    return {
        "animal_id": animal["id"],
        "name": animal["name"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latitude": round(new_lat, 6),
        "longitude": round(new_lon, 6),
        "movement": movement,
        "temperature": temp,
        "activity": activity
    }

def get_all_readings():
    """Get one reading for every animal"""
    return [generate_reading(animal) for animal in animals]