"""Phase (navigation) tests — all offline (mock providers), zero API credits.

Covers: the companion parses the navigation side-effect; NavState announces
maneuvers and arrival purely from geometry; and a full "take me to..." turn plus
walk-mode location ticks route end to end through the orchestrator on mocks.
"""

import asyncio
import importlib
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import companion  # noqa: E402
from app.nav_state import NavState  # noqa: E402
from app.services.navigation import Route, RouteStep  # noqa: E402


def test_parse_navigation_start():
    r = companion.parse(
        '{"intent":"navigate","spoken":"Okay.","memory_add":null,"reminder":null,'
        '"navigation":{"action":"start","destination":"the pharmacy"}}'
    )
    assert r.intent == "navigate"
    assert r.navigation == {"action": "start", "destination": "the pharmacy"}


def test_parse_navigation_stop_and_rejects_junk():
    r = companion.parse('{"intent":"stop_navigation","spoken":"Stopped.","navigation":{"action":"stop"}}')
    assert r.navigation == {"action": "stop"}
    # A malformed navigation object is dropped, not trusted.
    bad = companion.parse('{"intent":"describe","spoken":"hi","navigation":{"action":"teleport"}}')
    assert bad.navigation is None


def test_navstate_progression_and_arrival():
    # A straight-line route: three maneuver points ~30 m apart heading north.
    steps = [
        RouteStep("Head north.", 30, 53.3400, -6.2600),
        RouteStep("Turn left onto Nassau Street.", 30, 53.3403, -6.2600),
        RouteStep("Arrive at the pharmacy.", 0, 53.3406, -6.2600),
    ]
    nav = NavState()
    nav.start(Route("the pharmacy", steps, 60))
    assert "Starting navigation" in nav.first_instruction()

    # Far from everything -> nothing to say.
    assert nav.update(53.3390, -6.2600) is None
    # Approaching maneuver 2 -> announce it.
    assert nav.update(53.34028, -6.2600) == "Turn left onto Nassau Street."
    # Approaching the final maneuver -> announce it.
    assert nav.update(53.34058, -6.2600) == "Arrive at the pharmacy."
    # At the destination with nothing left -> arrival, and the route clears.
    msg = nav.update(53.3406, -6.2600)
    assert msg == "You've arrived at the pharmacy."
    assert not nav.active()


def _fresh_orchestrator():
    import app.config as cfg

    cfg.settings.demo_mode = "off"
    cfg.settings.stt_provider = "mock"
    cfg.settings.vision_provider = "mock"
    cfg.settings.tts_provider = "mock"
    cfg.settings.nav_provider = "mock"

    import app.orchestrator as orch_mod

    importlib.reload(orch_mod)
    return orch_mod.Orchestrator()


def test_navigate_turn_starts_route_and_ticks():
    async def scenario():
        o = _fresh_orchestrator()
        # No location yet -> it should ask for it, not crash.
        t0 = await o.run("", b"", "take me to the pharmacy")
        assert t0.intent == "navigate" and "location" in t0.answer.lower()
        assert not o.nav.active()

        # With a location, the routing engine (mock) produces the real first step.
        loc = {"lat": 53.3403, "lng": -6.2601}
        t1 = await o.run("", b"", "take me to the pharmacy", loc)
        assert t1.intent == "navigate"
        assert "Starting navigation" in t1.answer
        assert o.nav.active()

        # Simulate walking the route: the device streams positions past each
        # maneuver point in turn. Announce each maneuver, then arrival.
        pts = [(s.lat, s.lng) for s in o.nav.route.steps]
        announcements = []
        for lat, lng in pts[1:] + [pts[-1]]:
            step = await o.on_location(lat, lng)
            if step:
                announcements.append(step.text)
        assert any("nassau" in a.lower() for a in announcements), announcements
        assert any("arrived" in a.lower() for a in announcements), announcements
        assert not o.nav.active()
        return t1, announcements

    t1, announcements = asyncio.run(scenario())
    print("\nnavigate ->", t1.answer)
    print("ticks    ->", announcements)


def test_where_am_i_prepends_place():
    async def scenario():
        o = _fresh_orchestrator()
        t = await o.run("", b"", "where am i", {"lat": 53.3403, "lng": -6.2601})
        assert t.intent == "where_am_i"
        assert "Dawson Street" in t.answer  # from MockNavigation.reverse_geocode
        return t

    t = asyncio.run(scenario())
    print("where_am_i ->", t.answer)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("\nALL NAVIGATION TESTS PASS")
