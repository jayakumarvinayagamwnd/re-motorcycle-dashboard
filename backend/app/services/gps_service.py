import random


def get_latest_gps() -> dict:
    # Random GPS coordinates around a plausible location (e.g., Bengaluru, India)
    lat = round(12.9716 + random.uniform(-0.05, 0.05), 6)
    lon = round(77.5946 + random.uniform(-0.05, 0.05), 6)
    altitude_m = round(random.uniform(800.0, 1000.0), 2)
    return {
        "lat": lat,
        "lon": lon,
        "altitude_m": altitude_m,
    }