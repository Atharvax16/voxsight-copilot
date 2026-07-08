"""Active-route state for one navigation session.

Held per WebSocket connection (the Orchestrator is created per connection). As
location updates stream in, `update()` decides — purely from geometry, no API or
model calls — when the user is close enough to the next maneuver to announce it,
and when they've arrived. This is what makes turn-by-turn cost nothing per tick.
"""

from app.config import settings
from app.services.navigation import Route, haversine


class NavState:
    def __init__(self) -> None:
        self.route: Route | None = None
        self.idx = 0  # index of the NEXT maneuver still to announce

    def active(self) -> bool:
        return self.route is not None

    def start(self, route: Route) -> None:
        self.route = route
        # Step 0 is spoken immediately via first_instruction(); updates handle the rest.
        self.idx = 1

    def clear(self) -> None:
        self.route = None
        self.idx = 0

    def first_instruction(self) -> str:
        if not self.route or not self.route.steps:
            return "I couldn't find a walking route there."
        return (
            f"Starting navigation to {self.route.destination}. "
            f"{self.route.steps[0].instruction}"
        )

    def update(self, lat: float, lng: float) -> str | None:
        """Return the next thing to say (a maneuver or arrival), or None if the
        user isn't close enough to any change yet."""
        if not self.route or not self.route.steps:
            return None
        steps = self.route.steps

        # Arrival: within range of the final maneuver and nothing left to announce.
        last = steps[-1]
        if (
            self.idx >= len(steps)
            and haversine(lat, lng, last.lat, last.lng) <= settings.nav_arrive_m
        ):
            dest = self.route.destination
            self.clear()
            return f"You've arrived at {dest}."

        # Announce the next maneuver once the user comes within range of it.
        if self.idx < len(steps):
            nxt = steps[self.idx]
            if haversine(lat, lng, nxt.lat, nxt.lng) <= settings.nav_announce_m:
                self.idx += 1
                return nxt.instruction
        return None
