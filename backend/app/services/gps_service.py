def get_latest_gps() -> dict:
    """Return the dashboard's default GPS position."""
    lat = 13.0481
    lon = 80.2214
    altitude_m = 6.0
    return {
        "lat": lat,
        "lon": lon,
        "altitude_m": altitude_m,
    }
