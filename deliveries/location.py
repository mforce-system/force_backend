from math import radians, sin, cos, sqrt, atan2
from typing import Tuple


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad, lon1_rad = radians(lat1), radians(lon1)
    lat2_rad, lon2_rad = radians(lat2), radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def estimate_eta(distance_km: float, avg_speed_kmh: float = 30) -> int:
    """
    Estimate arrival time in minutes.
    Default average speed is 30 km/h for urban delivery.
    """
    if distance_km <= 0:
        return 0
    
    hours = distance_km / avg_speed_kmh
    return int(hours * 60)


def parse_coordinates(location_str: str) -> Tuple[float, float]:
    """
    Parse location string "lat,lon" into tuple.
    """
    try:
        lat, lon = location_str.split(',')
        return float(lat.strip()), float(lon.strip())
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid location format: {location_str}")

