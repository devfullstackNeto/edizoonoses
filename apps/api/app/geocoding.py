"""Address search adapters. The database provider works offline on synthetic records."""

import json
from typing import Protocol
import httpx
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Occurrence
from .settings import settings


class GeocoderProvider(Protocol):
    def search(self, query: str) -> list[dict]: ...


class NominatimProvider:
    def __init__(self, base_url: str, user_agent: str):
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent

    def search(self, query: str) -> list[dict]:
        response = httpx.get(
            f"{self.base_url}/search",
            params={"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 5},
            headers={"User-Agent": self.user_agent, "Accept-Language": "pt-BR"},
            timeout=5.0,
        )
        response.raise_for_status()
        return [
            {
                "label": str(item["display_name"])[:300],
                "latitude": float(item["lat"]),
                "longitude": float(item["lon"]),
                "source": "nominatim",
                "reference": f"{item.get('osm_type', '')}:{item.get('osm_id', '')}",
            }
            for item in response.json()[:5]
        ]


def search_addresses(db: Session, query: str, actor_id: str | None = None) -> dict:
    stmt = select(Occurrence).where(
        Occurrence.deleted_at.is_(None),
        Occurrence.latitude.is_not(None),
        Occurrence.address.ilike(f"%{query}%"),
    )
    if actor_id:
        stmt = stmt.where(Occurrence.assigned_to == actor_id)
    rows = db.scalars(stmt.limit(5)).all()
    local = [
        {
            "label": f"{o.address} · {o.protocol} (sintético)",
            "latitude": o.latitude,
            "longitude": o.longitude,
            "source": "database-demo",
            "reference": o.id,
        }
        for o in rows
    ]
    if not settings.geocoder_base_url:
        return {
            "items": local,
            "provider": "database-demo",
            "external_available": False,
        }
    redis = Redis.from_url(settings.redis_url)
    cache_key = "geocode:" + query.lower().strip()
    cached = redis.get(cache_key)
    if cached:
        external = json.loads(cached)
    elif redis.set("geocode:rate", "1", nx=True, ex=1):
        try:
            external = NominatimProvider(
                settings.geocoder_base_url, settings.geocoder_user_agent
            ).search(query)
            redis.setex(cache_key, 86400, json.dumps(external))
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            external = []
    else:
        external = []
    return {
        "items": local + external,
        "provider": "nominatim" if external else "database-demo",
        "external_available": bool(external),
    }
