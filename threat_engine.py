from datetime import datetime

# Store history for each animal
animal_history = {}

# Track poaching suspect status per animal
poaching_suspects = {}

def update_history(reading):
    animal_id = reading["animal_id"]
    if animal_id not in animal_history:
        animal_history[animal_id] = []
    animal_history[animal_id].append(reading)
    if len(animal_history[animal_id]) > 10:
        animal_history[animal_id].pop(0)

def check_temperature_trend(animal_id):
    history = animal_history.get(animal_id, [])
    if len(history) < 3:
        return False
    temps = [r["temperature"] for r in history[-3:]]
    return temps[0] < temps[1] < temps[2]

def check_movement_trend(animal_id):
    history = animal_history.get(animal_id, [])
    if len(history) < 3:
        return False
    return all(r["movement"] < 0.15 for r in history[-3:])

def check_heart_rate_trend(animal_id):
    history = animal_history.get(animal_id, [])
    if len(history) < 3:
        return False
    rates = [r.get("heart_rate", 0) for r in history[-3:]]
    return rates[0] > rates[1] > rates[2]

def check_stress_trend(animal_id):
    history = animal_history.get(animal_id, [])
    if len(history) < 3:
        return False
    return all(r.get("stress_level", 0) > 70 for r in history[-3:])


# ── Poaching detection ────────────────────────────────────────────────────────

def check_gps_frozen(animal_id):
    """GPS hasn't moved meaningfully in last 4 readings — possible snare."""
    history = animal_history.get(animal_id, [])
    if len(history) < 4:
        return False
    lats = [r.get("latitude", 0) for r in history[-4:]]
    lons = [r.get("longitude", 0) for r in history[-4:]]
    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)
    return lat_range < 0.0001 and lon_range < 0.0001


def check_instant_stress_spike(animal_id):
    """
    Stress jumped from normal to critical in ONE reading.
    Natural predator encounters cause gradual stress — snares and darts don't.
    """
    history = animal_history.get(animal_id, [])
    if len(history) < 2:
        return False
    prev_stress = history[-2].get("stress_level", 0)
    curr_stress = history[-1].get("stress_level", 0)
    return prev_stress < 40 and curr_stress > 85


def check_heart_rate_collapse(animal_id):
    """Heart rate dropped more than 20% in last 3 readings — serious."""
    history = animal_history.get(animal_id, [])
    if len(history) < 3:
        return False
    rates = [r.get("heart_rate", 70) for r in history[-3:]]
    if rates[0] == 0:
        return False
    drop = (rates[0] - rates[-1]) / rates[0]
    return drop > 0.20


def check_wrong_time_activity(animal_id, reading):
    """
    Animal is completely still during its normal active hours —
    or sprinting during normal rest hours. Unnatural behaviour.
    """
    import json
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        profiles = config.get("species_profiles", {})
        species = reading.get("species", "default")
        profile = profiles.get(species, profiles.get("default", {}))
    except Exception:
        return False

    hour = datetime.now().hour
    movement = reading.get("movement", 0.5)

    # Should be active but completely still
    for window in profile.get("active_hours", []):
        if window[0] <= hour <= window[1]:
            if movement < 0.05:
                return True

    # Should be resting but sprinting
    for window in profile.get("rest_hours", []):
        if window[0] <= hour <= window[1]:
            if movement > 0.9:
                return True

    return False


def detect_poaching(animal_id, reading):
    """
    Returns a poaching confidence level: None, 'SUSPECTED', or 'LIKELY'.

    LIKELY   — 3+ signals match the snare/dart signature
    SUSPECTED — 2 signals match
    None     — not enough evidence
    """
    signals = {
        "instant_stress_spike":  check_instant_stress_spike(animal_id),
        "gps_frozen":            check_gps_frozen(animal_id),
        "heart_rate_collapse":   check_heart_rate_collapse(animal_id),
        "wrong_time_activity":   check_wrong_time_activity(animal_id, reading),
        "movement_frozen":       check_movement_trend(animal_id),
    }

    triggered = [k for k, v in signals.items() if v]
    count = len(triggered)

    if count >= 3:
        poaching_suspects[animal_id] = {
            "confidence": "LIKELY",
            "signals": triggered,
            "detected_at": datetime.now().strftime("%H:%M:%S"),
        }
        return "LIKELY", triggered
    elif count >= 2:
        poaching_suspects[animal_id] = {
            "confidence": "SUSPECTED",
            "signals": triggered,
            "detected_at": datetime.now().strftime("%H:%M:%S"),
        }
        return "SUSPECTED", triggered
    else:
        # Clear if animal recovers
        if animal_id in poaching_suspects and count == 0:
            del poaching_suspects[animal_id]
        return None, []


def get_poaching_suspects():
    """Return current poaching suspects — used by dashboard."""
    return poaching_suspects


# ── Anomaly scoring ───────────────────────────────────────────────────────────

def compute_anomaly_score(reading, animal_id):
    score = 0

    temp = reading.get("temperature", 38.0)
    movement = reading.get("movement", 0.5)
    heart_rate = reading.get("heart_rate", 70)
    stress = reading.get("stress_level", 20)

    if temp > 40.0:       score += 20
    elif temp > 39.5:     score += 12
    elif temp > 39.0:     score += 6
    if check_temperature_trend(animal_id): score += 10

    if movement < 0.05:   score += 20
    elif movement < 0.1:  score += 12
    elif movement < 0.2:  score += 6
    if check_movement_trend(animal_id):    score += 10

    if heart_rate < 40:   score += 15
    elif heart_rate < 50: score += 8
    if check_heart_rate_trend(animal_id):  score += 10

    if stress > 85:       score += 15
    elif stress > 70:     score += 8
    if check_stress_trend(animal_id):      score += 10

    # Poaching signals push score up
    if check_instant_stress_spike(animal_id): score += 15
    if check_gps_frozen(animal_id):           score += 10
    if check_heart_rate_collapse(animal_id):  score += 15

    return min(score, 100)


# ── Main threat assessment ────────────────────────────────────────────────────

def assess_threat(reading):
    update_history(reading)

    animal_id = reading["animal_id"]
    name = reading["name"]
    movement = reading["movement"]
    temp = reading["temperature"]
    heart_rate = reading.get("heart_rate", 70)
    stress = reading.get("stress_level", 20)

    temp_rising    = check_temperature_trend(animal_id)
    movement_stuck = check_movement_trend(animal_id)
    heart_dropping = check_heart_rate_trend(animal_id)
    stress_sustained = check_stress_trend(animal_id)
    anomaly_score  = compute_anomaly_score(reading, animal_id)

    # ── Poaching check (highest priority) ────────────────────────────────────
    poaching_level, signals = detect_poaching(animal_id, reading)

    if poaching_level == "LIKELY":
        signals_str = ", ".join(signals).replace("_", " ")
        return _result("POACHING", "purple", anomaly_score,
            f"🚨 {name}: POACHING LIKELY — {signals_str}.",
            "URGENT: Dispatch anti-poaching ranger. Contact authorities.")

    if poaching_level == "SUSPECTED":
        signals_str = ", ".join(signals).replace("_", " ")
        return _result("POACHING", "purple", anomaly_score,
            f"⚠️ {name}: Poaching suspected — {signals_str}.",
            "Dispatch ranger immediately. Monitor closely.")

    # ── CRITICAL ─────────────────────────────────────────────────────────────
    if movement < 0.1 and temp > 39.5 and heart_rate < 50:
        return _result("CRITICAL", "red", anomaly_score,
            f"{name}: No movement, high temp, dropping heart rate. Possible injury.",
            "Dispatch ranger immediately.")

    if movement < 0.1 and temp > 39.5:
        return _result("CRITICAL", "red", anomaly_score,
            f"{name}: No movement + high temperature. Possible injury or heat stress.",
            "Dispatch ranger immediately.")

    if movement_stuck and temp > 39.0:
        return _result("CRITICAL", "red", anomaly_score,
            f"{name}: Prolonged inactivity + elevated temperature.",
            "Dispatch ranger immediately.")

    if stress_sustained and heart_dropping:
        return _result("CRITICAL", "red", anomaly_score,
            f"{name}: Sustained high stress + falling heart rate.",
            "Dispatch ranger immediately.")

    # ── ELEVATED ─────────────────────────────────────────────────────────────
    if temp_rising and movement < 0.3:
        return _result("ELEVATED", "orange", anomaly_score,
            f"{name}: Temperature rising, movement declining.",
            "Monitor closely. Prepare to dispatch ranger.")

    if heart_dropping and stress > 60:
        return _result("ELEVATED", "orange", anomaly_score,
            f"{name}: Heart rate dropping with elevated stress.",
            "Monitor closely. Could indicate injury or threat.")

    if anomaly_score >= 50:
        return _result("ELEVATED", "orange", anomaly_score,
            f"{name}: Multiple anomalous signals detected (score: {anomaly_score}/100).",
            "Monitor closely.")

    # ── WARNING ──────────────────────────────────────────────────────────────
    if movement < 0.1:
        return _result("WARNING", "yellow", anomaly_score,
            f"{name}: Very low movement detected.",
            "Monitor for next few readings.")

    if temp > 39.5:
        return _result("WARNING", "yellow", anomaly_score,
            f"{name}: Elevated temperature detected.",
            "Monitor temperature trend.")

    if stress > 70:
        return _result("WARNING", "yellow", anomaly_score,
            f"{name}: High stress level ({stress}%).",
            "Watch for further stress signals.")

    if temp_rising:
        return _result("WARNING", "yellow", anomaly_score,
            f"{name}: Temperature trending upward.",
            "Watch for further increases.")

    if anomaly_score >= 25:
        return _result("WARNING", "yellow", anomaly_score,
            f"{name}: Mild anomaly detected (score: {anomaly_score}/100).",
            "Monitor readings.")

    # ── SAFE ─────────────────────────────────────────────────────────────────
    return _result("SAFE", "green", anomaly_score,
        f"{name}: All vitals normal.",
        "No action needed.")


def _result(level, color, anomaly_score, message, action):
    return {
        "level": level,
        "color": color,
        "anomaly_score": anomaly_score,
        "message": message,
        "action": action,
    }


def assess_all(readings):
    results = []
    for reading in readings:
        threat = assess_threat(reading)
        results.append({**reading, **threat})
    return results