"""Hearthline MCP server. Streamable HTTP, spec 2025-11-25 or later."""

from __future__ import annotations

import json
import os

from mcp.server import MCPServer

from hearthline import store
from hearthline.aqi import read_air
from hearthline.policy import build_plan

mcp = MCPServer(
    "hearthline",
    title="Hearthline",
    version="1.0.0",
    instructions=(
        "Hearthline is an Alexa+ coach for the air around one household. "
        "Remember the city and who lives there, especially children and anyone with asthma. "
        "Check live air quality, then plan the school morning or the evening. "
        "Keep that profile and the last plan for the next session. "
        "Speak the plan in a short voice reply and return the card that goes with it."
    ),
)


def _dump(payload: dict) -> str:
    return json.dumps(payload)


@mcp.tool(description="Remember the household city, a home name, or one person. Call once per person. Empty fields are left unchanged.")
async def remember_household(
    city: str = "",
    home_name: str = "",
    member_name: str = "",
    member_role: str = "",
    member_note: str = "",
    member_age: int = 0,
) -> str:
    household = store.load_household()
    saved: list[str] = []
    if city.strip():
        household["city"] = " ".join(part.capitalize() for part in city.split())
        saved.append("city")
    if home_name.strip():
        household["home_name"] = home_name.strip()
        saved.append("home name")
    if member_name.strip():
        role = member_role.strip().lower() or "adult"
        if role not in {"child", "adult"}:
            role = "adult"
        if member_age and 0 < member_age < 18:
            role = "child"
        store.upsert_member(
            household,
            {
                "name": " ".join(part.capitalize() for part in member_name.split()),
                "role": role,
                "note": member_note.strip().lower(),
                "age": member_age or None,
            },
        )
        saved.append(member_name.strip())
    store.save_household(household)
    return _dump({"ok": True, "saved": saved, "household": household})


@mcp.tool(description="Read the household this server already remembers, including the last plan.")
async def get_household() -> str:
    return _dump({"ok": True, "household": store.load_household()})


@mcp.tool(description="Forget the household, saved plans, and cached air reading.")
async def clear_household() -> str:
    store.clear_all()
    return _dump({"ok": True, "household": store.empty_household()})


@mcp.tool(description="Check live air quality for a city. Uses the saved home city when city is empty.")
async def check_air(city: str = "") -> str:
    chosen = city.strip() or (store.load_household().get("city") or "")
    reading = await read_air(chosen)
    return _dump(reading)


@mcp.tool(description="Build a school, evening, outdoor, or right-now plan from the household and live air. Saves the plan for the next session.")
async def plan_day(focus: str = "now", city: str = "") -> str:
    household = store.load_household()
    chosen = city.strip() or household.get("city") or ""
    if not chosen:
        return _dump(
            {
                "ok": False,
                "speech": "Tell me the city first. For example: we live in Ajmer.",
                "card": None,
            }
        )
    air = await read_air(chosen)
    if not air.get("ok"):
        return _dump({"ok": False, "speech": air.get("speech") or "I couldn't check the air.", "card": None})
    same_home = not city.strip() or city.strip().casefold() == (household.get("city") or "").casefold()
    if same_home or not household.get("city"):
        if not household.get("city"):
            household["city"] = air.get("city") or chosen
        household["place_label"] = air.get("place_label") or household.get("place_label") or ""
    plan = build_plan(household, air, (focus or "now").strip().lower())
    brief = {"speech": plan["speech"], "headline": plan["card"]["headline"], "card": plan["card"]}
    if same_home or not household.get("last_brief"):
        household["last_brief"] = brief
    store.save_household(household)
    store.append_history(brief)
    return _dump(plan)


@mcp.tool(description="Save a named routine the household wants to repeat, such as the school run.")
async def save_routine(name: str, note: str = "") -> str:
    household = store.load_household()
    routine = {"name": name.strip() or "Routine", "note": note.strip(), "saved_at": store.now_iso()}
    household.setdefault("routines", []).append(routine)
    household["routines"] = household["routines"][-10:]
    store.save_household(household)
    return _dump({"ok": True, "routine": routine, "household": household})


@mcp.tool(description="Recall the most recent plans this server saved.")
async def recall_history(limit: int = 5) -> str:
    bounded = max(1, min(int(limit or 5), 20))
    briefs = store.load_history()[-bounded:]
    return _dump({"ok": True, "briefs": briefs})


@mcp.resource(
    "household://profile",
    mime_type="application/json",
    description="The household Hearthline currently remembers.",
)
def household_profile() -> str:
    return json.dumps(store.load_household(), indent=2)


def main() -> None:
    port = int(os.environ.get("HEARTHLINE_MCP_PORT", "8765"))
    # JSON responses over Streamable HTTP. Stateless so a judge's client can
    # call tools without holding a long-lived SSE socket.
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=port,
        json_response=True,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()
