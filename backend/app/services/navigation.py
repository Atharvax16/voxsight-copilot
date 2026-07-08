"""Walking navigation: geocoding + foot-routing behind the NavigationService protocol.

Two providers, same swap-in-.env pattern as the AI services:
  mock             — canned route near the user's location; fully offline, no key,
                     used for demo/replay and the test suite.
  openrouteservice — live walking directions + geocoding via ORS (free API key).

Turn-by-turn steps come from the routing engine, never the LLM: that keeps
navigation cheap (no per-tick model calls), reliable, and offline-cacheable.
"""

import math
from dataclasses import dataclass

import httpx

from app.config import settings

ORS_BASE = "https://api.openrouteservice.org"


@dataclass
class RouteStep:
    instruction: str  # "Turn left onto Dawson Street"
    distance_m: float  # length of this step
    lat: float  # maneuver point (where this instruction takes effect)
    lng: float


@dataclass
class Route:
    destination: str
    steps: list[RouteStep]
    total_distance_m: float


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres between two lat/lng points."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


class MockNavigation:
    """Offline navigation — a short canned route anchored at the user's position,
    so `NAV_PROVIDER=mock` gives a full walk-through with zero API calls."""

    async def geocode(
        self, text: str, near: tuple[float, float] | None = None
    ) -> tuple[float, float] | None:
        # Pretend the destination is a few hundred metres away from `near`.
        lat, lng = near or (53.3403, -6.2601)  # central Dublin fallback
        return (lat + 0.0016, lng + 0.0009)

    async def reverse_geocode(self, lat: float, lng: float) -> str:
        return "Dawson Street, Dublin 2"

    async def route(
        self,
        start: tuple[float, float],
        dest: tuple[float, float],
        destination_label: str,
    ) -> Route:
        lat, lng = start
        dlat, dlng = dest
        steps = [
            RouteStep("Head north along the footpath.", 40, lat, lng),
            RouteStep("Turn left onto Nassau Street.", 70, lat + 0.0007, lng),
            RouteStep(
                f"Arrive at {destination_label}, on your right.", 0, dlat, dlng
            ),
        ]
        total = sum(s.distance_m for s in steps)
        return Route(destination_label, steps, total)


class OpenRouteServiceNavigation:
    """Live walking directions + geocoding via OpenRouteService (free tier).

    Geocoding uses the /geocode endpoints (Pelias); directions use
    /v2/directions/foot-walking. The maneuver point for each step is the route
    geometry coordinate at the step's starting waypoint.
    """

    def __init__(self) -> None:
        self.key = settings.openrouteservice_api_key

    async def geocode(
        self, text: str, near: tuple[float, float] | None = None
    ) -> tuple[float, float] | None:
        params = {"api_key": self.key, "text": text, "size": 1}
        if near:
            # Bias results toward the user so "the pharmacy" resolves nearby.
            params["focus.point.lat"] = near[0]
            params["focus.point.lon"] = near[1]
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{ORS_BASE}/geocode/search", params=params)
            resp.raise_for_status()
            feats = resp.json().get("features", [])
        if not feats:
            return None
        lon, lat = feats[0]["geometry"]["coordinates"]
        return (lat, lon)

    async def reverse_geocode(self, lat: float, lng: float) -> str:
        params = {"api_key": self.key, "point.lat": lat, "point.lon": lng, "size": 1}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{ORS_BASE}/geocode/reverse", params=params)
            resp.raise_for_status()
            feats = resp.json().get("features", [])
        if not feats:
            return "an unknown location"
        return feats[0]["properties"].get("label", "an unknown location")

    async def route(
        self,
        start: tuple[float, float],
        dest: tuple[float, float],
        destination_label: str,
    ) -> Route:
        # ORS wants [lon, lat] order.
        body = {
            "coordinates": [[start[1], start[0]], [dest[1], dest[0]]],
            "instructions": True,
        }
        headers = {"Authorization": self.key}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ORS_BASE}/v2/directions/foot-walking/geojson",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            feat = resp.json()["features"][0]

        coords = feat["geometry"]["coordinates"]  # list of [lon, lat]
        steps: list[RouteStep] = []
        for seg in feat["properties"].get("segments", []):
            for st in seg.get("steps", []):
                wp = st.get("way_points", [0])[0]
                lon, lat = coords[min(wp, len(coords) - 1)]
                steps.append(
                    RouteStep(
                        instruction=st.get("instruction", "Continue.").strip(),
                        distance_m=float(st.get("distance", 0.0)),
                        lat=lat,
                        lng=lon,
                    )
                )
        total = float(feat["properties"].get("summary", {}).get("distance", 0.0))
        return Route(destination_label, steps, total)
