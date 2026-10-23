"""Decide which MCP tools a turn needs, then speak from their results.

The simulator never calls the air service or the household file itself.
Every read and write goes through the MCP server.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_NAME_STOP = {
    "and",
    "the",
    "our",
    "home",
    "remember",
    "give",
    "should",
    "what",
    "please",
    "school",
    "morning",
    "tonight",
    "evening",
    "air",
    "windows",
    "window",
    "fine",
    "here",
    "going",
    "ready",
    "good",
    "back",
    "ok",
    "okay",
}
_CITY_STOP = {
    "the",
    "a",
    "an",
    "our",
    "my",
    "this",
    "that",
    "morning",
    "evening",
    "tonight",
    "today",
    "school",
    "class",
    "bed",
    "doors",
    "windows",
    "window",
    "home",
    "general",
    "india",
}


@dataclass
class Intent:
    city_to_save: str = ""
    city_for_query: str = ""
    members: list[dict] = field(default_factory=list)
    focus: str = "now"
    wants_plan: bool = False
    wants_air_only: bool = False
    wants_memory: bool = False
    wants_history: bool = False
    wants_reset: bool = False

    @property
    def is_help(self) -> bool:
        return not any(
            [
                self.city_to_save,
                self.city_for_query,
                self.members,
                self.wants_plan,
                self.wants_air_only,
                self.wants_memory,
                self.wants_history,
                self.wants_reset,
            ]
        )


def parse(text: str) -> Intent:
    raw = " ".join(text.strip().split())
    lower = raw.casefold()
    intent = Intent()
    if not lower or lower in {"help", "hello", "hi", "hey"} or "what can you do" in lower:
        return intent
    if any(phrase in lower for phrase in ("forget everything", "start over", "reset", "clear the home", "clear home")):
        intent.wants_reset = True
        return intent
    if any(phrase in lower for phrase in ("what do you remember", "who lives", "who is here", "who's here", "who do you know")):
        intent.wants_memory = True
        return intent
    if any(phrase in lower for phrase in ("last brief", "earlier brief", "what did you tell", "yesterday")):
        intent.wants_history = True
        return intent

    intent.city_to_save = _city_to_save(raw)
    intent.city_for_query = _city_for_query(raw) or intent.city_to_save
    intent.members = _members(raw)
    intent.focus = _focus(lower)
    intent.wants_plan = _wants_plan(lower)
    intent.wants_air_only = _wants_air_only(lower) and not intent.wants_plan
    if intent.city_to_save or intent.members or intent.wants_plan or intent.wants_air_only:
        return intent
    return Intent()


def _city_to_save(text: str) -> str:
    match = re.search(
        r"\b(?:live|living|lives|home|city|from)\s+in\s+([A-Za-z][A-Za-z .'-]{1,40})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        match = re.search(r"\bcity\s+is\s+([A-Za-z][A-Za-z .'-]{1,40})", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return _clean_city(match.group(1))


def _city_for_query(text: str) -> str:
    match = re.search(r"\b(?:in|for)\s+([A-Za-z][A-Za-z .'-]{1,40})", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return _clean_city(match.group(1))


def _clean_city(value: str) -> str:
    value = re.split(r"[.,!?]", value, maxsplit=1)[0]
    value = re.split(
        r"\b(?:and|with|where|for|tonight|today|please)\b",
        value,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    words = []
    for word in value.split():
        if word.casefold() in _CITY_STOP:
            break
        words.append(word)
    cleaned = " ".join(words).strip(" -'")
    if not cleaned or cleaned.casefold() in _CITY_STOP:
        return ""
    return " ".join(part.capitalize() for part in cleaned.split())


def _members(text: str) -> list[dict]:
    found: dict[str, dict] = {}

    def add(name: str, role: str = "", note: str = "", age: int = 0) -> None:
        clean = " ".join(part.capitalize() for part in name.split())
        if not clean or clean.casefold() in _NAME_STOP:
            return
        slot = found.setdefault(clean.casefold(), {"name": clean, "role": "", "note": "", "age": 0})
        if role and not slot["role"]:
            slot["role"] = role
        if note and not slot["note"]:
            slot["note"] = note
        if age and not slot["age"]:
            slot["age"] = age
        if slot["age"] and slot["age"] < 18:
            slot["role"] = "child"
        elif role == "child":
            slot["role"] = "child"

    for match in re.finditer(
        r"\b([A-Za-z]+)\s+is\s+(\d{1,2})\b(?:\s+and\s+has\s+([A-Za-z]+))?",
        text,
        flags=re.IGNORECASE,
    ):
        note = (match.group(3) or "").casefold()
        if note not in {"asthma", "allergies", "allergy", "copd"}:
            note = ""
        add(match.group(1), age=int(match.group(2)), note=note)

    for match in re.finditer(
        r"\b([A-Za-z]+)\s+has\s+(asthma|allergies|allergy|copd)\b",
        text,
        flags=re.IGNORECASE,
    ):
        add(match.group(1), note=match.group(2).casefold())

    for match in re.finditer(
        r"\bmy\s+(daughter|son|kid|child|wife|husband|partner)\s+([A-Za-z]+)",
        text,
        flags=re.IGNORECASE,
    ):
        kind = match.group(1).casefold()
        role = "child" if kind in {"daughter", "son", "kid", "child"} else "adult"
        add(match.group(2), role=role)

    for match in re.finditer(r"\bI\s+am\s+([A-Za-z]+)\b", text, flags=re.IGNORECASE):
        add(match.group(1), role="adult")

    return list(found.values())


def _focus(lower: str) -> str:
    if any(word in lower for word in ("tonight", "evening", "window", "balcony", "night")):
        return "evening"
    if any(word in lower for word in ("school", "pickup", "morning", "classroom", " pe")):
        return "school"
    if any(word in lower for word in ("outside", "outdoor", "park", "play")):
        return "outdoor"
    return "now"


def _wants_plan(lower: str) -> bool:
    markers = (
        "brief",
        "plan",
        "should",
        "school",
        "window",
        "outside",
        "outdoor",
        "tonight",
        "safe",
        "go out",
        "open the",
        " pe",
    )
    return any(marker in lower for marker in markers)


def _wants_air_only(lower: str) -> bool:
    return any(marker in lower for marker in ("aqi", "air quality", "how is the air", "what's the air", "whats the air", "the air in"))


async def respond(text: str, call) -> dict:
    intent = parse(text)
    if intent.wants_reset:
        await call("clear_household", {})
        return {
            "speech": "I cleared the home, the people, and the saved plans. Tell me the city and who lives there when you want to start again.",
            "card": None,
        }
    if intent.is_help:
        return {
            "speech": (
                "I remember who lives here, check the air, and plan the school run or the evening. "
                "Try: we live in Ajmer, and Riya has asthma."
            ),
            "card": None,
        }
    if intent.wants_memory:
        payload = await call("get_household", {})
        return {"speech": _memory_speech(payload.get("household") or {}), "card": _memory_card(payload.get("household") or {})}
    if intent.wants_history:
        payload = await call("recall_history", {"limit": 3})
        briefs = payload.get("briefs") or []
        if not briefs:
            return {"speech": "I haven't saved a plan yet. Ask me for a school brief after you tell me the city.", "card": None}
        last = briefs[-1]
        return {
            "speech": f"The last plan I saved was: {last.get('speech') or last.get('headline')}",
            "card": last.get("card"),
        }

    household = None
    if intent.city_to_save:
        household = await call(
            "remember_household",
            {"city": intent.city_to_save, "home_name": f"{intent.city_to_save} home"},
        )
    for member in intent.members:
        household = await call(
            "remember_household",
            {
                "member_name": member["name"],
                "member_role": member["role"] or "adult",
                "member_note": member["note"],
                "member_age": member["age"],
            },
        )

    if intent.wants_plan:
        plan = await call("plan_day", {"focus": intent.focus, "city": intent.city_for_query})
        speech = plan.get("speech") or "I couldn't make a plan."
        if household and household.get("ok"):
            speech = "Saved. " + speech
        return {"speech": speech, "card": plan.get("card")}

    if intent.wants_air_only:
        air = await call("check_air", {"city": intent.city_for_query})
        return {"speech": _air_speech(air), "card": _air_card(air)}

    if household and household.get("ok"):
        return {"speech": _saved_speech(household.get("household") or {}), "card": _memory_card(household.get("household") or {})}

    return {
        "speech": "Tell me the city, who has asthma, or ask for the school morning brief.",
        "card": None,
    }


def _saved_speech(household: dict) -> str:
    city = household.get("place_label") or household.get("city") or "your city"
    names = _member_phrase(household.get("members") or [])
    if names and household.get("city"):
        return f"I'll remember home as {city}. I have {names}. Ask me for the school morning brief when you're heading out."
    if household.get("city"):
        return f"I'll remember home as {city}. Tell me who lives there if a child or someone with asthma should change the plan."
    if names:
        return f"I'll remember {names}. I still need the city before I can check the air."
    return "I didn't catch a city or a person. Try: we live in Ajmer, and Riya has asthma."


def _memory_speech(household: dict) -> str:
    if not household.get("city") and not household.get("members"):
        return "I don't know this home yet. Tell me the city and who lives there."
    city = household.get("place_label") or household.get("city") or "an unnamed city"
    names = _member_phrase(household.get("members") or [])
    last = household.get("last_brief") or {}
    speech = f"Home is {city}."
    if names:
        speech += f" I know {names}."
    else:
        speech += " I don't know who lives there yet."
    headline = (last.get("card") or {}).get("headline")
    if headline:
        speech += f" The last plan was: {headline}."
    return speech


def _memory_card(household: dict) -> dict | None:
    if not household.get("city") and not household.get("members"):
        return None
    last = (household.get("last_brief") or {}).get("card") or {}
    return {
        "title": "This home",
        "city": household.get("city") or "",
        "place_label": household.get("place_label") or household.get("city") or "This home",
        "aqi": last.get("aqi"),
        "band": last.get("band") or "Not checked yet",
        "pm2_5": last.get("pm2_5"),
        "headline": last.get("headline") or "No plan saved yet",
        "actions": last.get("actions") or [],
        "people": [
            {
                "name": member.get("name"),
                "role": member.get("role") or "adult",
                "note": ", ".join(member.get("notes") or []),
            }
            for member in household.get("members") or []
        ],
        "cached": False,
        "source": "household",
        "saved_at": household.get("updated_at"),
    }


def _member_phrase(members: list[dict]) -> str:
    parts = []
    for member in members:
        name = member.get("name") or "someone"
        role = member.get("role") or "adult"
        notes = member.get("notes") or []
        age = member.get("age")
        bit = name
        if age:
            bit += f", {age}"
        bit += f", {role}"
        if notes:
            bit += " with " + " and ".join(notes)
        parts.append(bit)
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def _air_speech(air: dict) -> str:
    if not air.get("ok"):
        return air.get("speech") or "I couldn't check the air."
    cached = " This is a saved reading, not a live one." if air.get("cached") else ""
    pm = air.get("pm2_5")
    pm_bit = f" PM2.5 is {pm}." if pm is not None else ""
    return f"{air.get('place_label')} is at {air.get('us_aqi')}, {str(air.get('band', '')).lower()}.{pm_bit}{cached}"


def _air_card(air: dict) -> dict | None:
    if not air.get("ok"):
        return None
    return {
        "title": "Air right now",
        "city": air.get("city") or "",
        "place_label": air.get("place_label") or air.get("city"),
        "aqi": air.get("us_aqi"),
        "band": air.get("band"),
        "pm2_5": air.get("pm2_5"),
        "headline": air.get("band") or "Air",
        "actions": [],
        "people": [],
        "cached": bool(air.get("cached")),
        "source": air.get("source") or "open-meteo",
        "saved_at": air.get("observed_at"),
    }
