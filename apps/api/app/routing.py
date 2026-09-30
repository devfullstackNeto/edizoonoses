"""Saved route geometry. OSRM is optional; local geodesic legs remain usable offline."""

import httpx
from types import SimpleNamespace
from .core import distance_km
from .settings import settings


def calculate_route(points, start=None):
    routed_points = (
        [SimpleNamespace(latitude=start[0], longitude=start[1])] if start else []
    ) + list(points)
    coordinates = [[float(p.longitude), float(p.latitude)] for p in routed_points]
    legs = [
        round(distance_km((a.latitude, a.longitude), (b.latitude, b.longitude)), 2)
        for a, b in zip(routed_points, routed_points[1:])
    ]
    fallback = {
        "provider": "local",
        "geometry": coordinates,
        "legs_km": legs,
        "total_km": round(sum(legs), 2),
        "duration_min": None,
    }
    if len(routed_points) < 2 or not settings.osrm_base_url:
        return fallback
    try:
        coords = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
        response = httpx.get(
            f"{settings.osrm_base_url.rstrip('/')}/route/v1/driving/{coords}",
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            timeout=4.0,
        )
        response.raise_for_status()
        route = response.json()["routes"][0]
        road_legs = [round(x["distance"] / 1000, 2) for x in route["legs"]]
        road_geometry = route["geometry"]["coordinates"]
        if len(road_legs) != len(legs) or len(road_geometry) < 2:
            return fallback
        return {
            "provider": "osrm",
            "geometry": road_geometry,
            "legs_km": road_legs,
            "total_km": round(route["distance"] / 1000, 2),
            "duration_min": round(route["duration"] / 60, 1)
            if "duration" in route
            else None,
        }
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return fallback
