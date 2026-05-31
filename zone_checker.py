import json
import math

with open("config.json", "r") as f:
    config = json.load(f)

zones = config.get("zones", [])

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two GPS coordinates"""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def check_zones(animal):
    """Check if an animal is inside any zone"""
    alerts = []
    in_safe_zone = False

    for zone in zones:
        distance = haversine_distance(
            animal["latitude"], animal["longitude"],
            zone["lat"], zone["lon"]
        )
        if distance <= zone["radius_meters"]:
            if zone["type"] == "danger":
                alerts.append({
                    "level": "CRITICAL",
                    "color": "red",
                    "message": f"🚨 {animal['name']} has entered danger zone: {zone['name']}!",
                    "action": "Dispatch ranger immediately."
                })
            elif zone["type"] == "safe":
                in_safe_zone = True

    if not in_safe_zone and not alerts:
        alerts.append({
            "level": "WARNING",
            "color": "yellow",
            "message": f"⚠️ {animal['name']} has left all safe zones.",
            "action": "Monitor closely."
        })

    return alerts

def check_all_zones(assessed_readings):
    """Check zones for all animals and add zone alerts"""
    for animal in assessed_readings:
        zone_alerts = check_zones(animal)
        if zone_alerts:
            critical = [a for a in zone_alerts if a["level"] == "CRITICAL"]
            if critical:
                animal["zone_alert"] = critical[0]
            else:
                animal["zone_alert"] = zone_alerts[0]
        else:
            animal["zone_alert"] = None
    return assessed_readings

def get_zones():
    """Return all zones for map rendering"""
    return zones