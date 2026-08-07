import random


def get_latest_telemetry() -> dict:
    return {
        "speed_kmh": round(random.uniform(0.0, 200.0), 1),
        "engine_rpm": random.randint(0, 12000),
        "fuel_percent": random.randint(0, 100),
    }
