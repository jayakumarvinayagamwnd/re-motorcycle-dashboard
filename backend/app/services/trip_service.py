import random


def get_current_trip() -> dict:
    # Random current trip data
    distance_km = round(random.uniform(0.0, 50.0), 2)
    duration_min = random.randint(0, 120)
    avg_speed_kmh = round(random.uniform(20.0, 80.0), 2)
    return {
        "distance_km": distance_km,
        "duration_min": duration_min,
        "avg_speed_kmh": avg_speed_kmh,
    }