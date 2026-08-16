import random
from datetime import datetime, timedelta


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


def get_trip_history() -> list:
    """Return mock trip history data."""
    trim_names = [
        "Morning Commute", "Weekend Ride", "Highway Cruise",
        "City Run", "Mountain Trail", "Evening Blast",
        "Grocery Run", "Night Cruise", "Coastal Drive",
        "Service Visit"
    ]
    history = []
    for i in range(10):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        history.append({
            "id": i + 1,
            "trim_name": trim_names[i],
            "distance_km": round(random.uniform(5.0, 150.0), 1),
            "date": date,
        })
    return history
