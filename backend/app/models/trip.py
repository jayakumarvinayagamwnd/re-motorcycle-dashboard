from pydantic import BaseModel


class Trip(BaseModel):
    distance_km: float
    duration_min: int
    avg_speed_kmh: float
