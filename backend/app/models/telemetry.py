from pydantic import BaseModel


class Telemetry(BaseModel):
    speed_kmh: float
    engine_rpm: int
    fuel_percent: int
