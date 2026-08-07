from pydantic import BaseModel


class GPSPoint(BaseModel):
    lat: float
    lon: float
    altitude_m: float
