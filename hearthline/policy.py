"""Turn a household plus an air reading into a spoken plan and a card."""

from __future__ import annotations

from hearthline.store import now_iso


def _sensitive(member: dict) -> bool:
    if member.get("role") == "child":
        return True
    if isinstance(member.get("age"), int) and member["age"] < 18:
        return True
    notes = " ".join(member.get("notes") or []).casefold()
    return any(word in notes for word in ("asthma", "copd", "heart", "pregnan"))


def _people(members: list[dict]) -> list[dict]:
    people = []
    for member in members:
        notes = member.get("notes") or []
        people.append(
            {
                "name": member.get("name") or "Someone",
                "role": member.get("role") or "adult",
                "note": ", ".join(notes),
            }
        )
    return people


def _names(members: list[dict]) -> str:
    names = [member["name"] for member in members if member.get("name")]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def build_plan(household: dict, air: dict, focus: str) -> dict:
    aqi = int(air["us_aqi"])
    band = air["band"]
    place = air.get("place_label") or household.get("place_label") or household.get("city") or air.get("city")
    members = household.get("members") or []
    sensitive = [member for member in members if _sensitive(member)]
    focus = focus if focus in {"school", "evening", "outdoor", "now"} else "now"
    actions = _actions(aqi, focus, sensitive)
    headline = actions[0]["label"] if actions else "Check the air before you head out"
    speech = _speech(place, aqi, band, focus, sensitive, bool(members))
    card = {
        "title": _title(focus),
        "city": household.get("city") or air.get("city") or "",
        "place_label": place,
        "aqi": aqi,
        "band": band,
        "pm2_5": air.get("pm2_5"),
        "headline": headline,
        "actions": actions,
        "people": _people(members),
        "cached": bool(air.get("cached")),
        "source": air.get("source") or "open-meteo",
        "saved_at": now_iso(),
    }
    return {"ok": True, "speech": speech, "card": card}


def _title(focus: str) -> str:
    return {
        "school": "School morning",
        "evening": "Tonight at home",
        "outdoor": "Heading outside",
        "now": "Right now",
    }[focus]


def _actions(aqi: int, focus: str, sensitive: list[dict]) -> list[dict]:
    who = _names(sensitive)
    if aqi <= 50:
        if focus == "evening":
            return [
                {"label": "Open the windows", "detail": "An hour of outside air will freshen the rooms."},
                {"label": "Balcony is fine", "detail": "Good air. No mask, no early night indoors."},
            ]
        if focus == "school":
            return [
                {"label": "Outdoor PE is on", "detail": "The class can use the grounds today."},
                {"label": "Air out the classroom", "detail": "Open the windows for the first period."},
            ]
        return [
            {"label": "Go out", "detail": "Air is good. Parks, walks, and errands are all fine."},
            {"label": "Open the windows", "detail": "Let the house breathe while you're out."},
        ]
    if aqi <= 100:
        if focus == "school":
            return [
                {"label": "Short outdoor PE", "detail": f"The class can go out. Keep it short{(' for ' + who) if who else ''}."},
                {"label": "Stop if breathing tightens", "detail": "Come inside at the first cough or tight chest. Moderate air is where that shows up."},
                {"label": "Windows for one period", "detail": "Air the classroom, then close it. Don't leave them open all day."},
            ]
        if focus == "evening":
            return [
                {"label": "Air the house for an hour", "detail": "Open the windows, then close them before bed."},
                {"label": "Balcony if breathing is easy", "detail": f"{(who + ' can step out') if who else 'Stepping out is fine'} as long as nobody feels tight."},
                {"label": "Close up after", "detail": "Moderate air is fine in a dose. It is not an all-night draft."},
            ]
        if sensitive:
            return [
                {"label": f"Keep an eye on {who}", "detail": "Moderate air. Cut it short if anyone starts to cough or feel tight."},
                {"label": "Windows for a bit", "detail": "A short airing is fine. Don't leave them open all day."},
            ]
        return [
            {"label": "Outside is fine", "detail": "Moderate air. Most people can keep their normal plans."},
            {"label": "Skip extra exertion", "detail": "A walk is fine. A long run can wait for a cleaner hour."},
        ]
    if aqi <= 150:
        if focus == "evening":
            return [
                {"label": "Windows stay shut", "detail": "Don't air the house out tonight."},
                {"label": "Skip the balcony", "detail": f"{who or 'Sensitive people'} should stay inside."},
                {"label": "Recirculate while cooking", "detail": "Use the fan on recirculate instead of pulling outdoor air in."},
            ]
        if focus == "school":
            return [
                {"label": "Indoor PE", "detail": f"Move the class inside. {who or 'Children'} are in the sensitive group at this level."},
                {"label": "Classroom windows shut", "detail": "Keep outdoor air out until the next check."},
                {"label": "Mask for pickup", "detail": "A well-fitted mask for the walk between the gate and home."},
            ]
        return [
            {"label": "Short trips only", "detail": f"{who or 'Sensitive people'} should skip prolonged time outside."},
            {"label": "Windows shut", "detail": "Keep the house closed while the band stays here."},
        ]
    if focus == "evening":
        return [
            {"label": "Seal the evening", "detail": "Windows closed. No balcony."},
            {"label": "Everyone stays in", "detail": f"This band is {('hard on ' + who) if who else 'unhealthy for the whole home'}."},
            {"label": "Mask if you must step out", "detail": "Only for something that cannot wait."},
        ]
    if focus == "school":
        return [
            {"label": "No outdoor PE", "detail": f"Keep {who or 'the class'} inside for games and lineup."},
            {"label": "Windows shut", "detail": "Classroom and home both stay closed."},
            {"label": "Mask the school run", "detail": "Wear one from the door to the classroom and back."},
        ]
    return [
        {"label": "Stay inside", "detail": "Cancel the park, the run, and any long errand."},
        {"label": "Windows shut", "detail": "Outdoor air is the thing you're keeping out."},
        {"label": "Mask for essentials", "detail": "Pharmacy or pickup only, then straight back."},
    ]


def _speech(place: str, aqi: int, band: str, focus: str, sensitive: list[dict], known_people: bool) -> str:
    who = _names(sensitive)
    level = f"{place} is at {aqi}, {band.lower()}."
    if aqi <= 50:
        if focus == "school":
            plan = "Outdoor PE is on, and the classroom can open its windows for the first period."
        elif focus == "evening":
            plan = "Open the windows for an hour tonight. The balcony is fine."
        else:
            plan = "Go out as you planned, and open the windows while you're at it."
    elif aqi <= 100:
        if focus == "school" and who:
            plan = f"Outdoor PE can go ahead, but keep it short for {who} and stop if breathing feels tight. Open the classroom windows only for the first period."
        elif focus == "evening" and who:
            plan = f"Open the windows for an hour tonight, then close them. {who} can use the balcony if breathing stays easy."
        elif focus == "school":
            plan = "School can stay outside. Open the classroom windows for the first period, and skip a long run."
        elif focus == "evening":
            plan = "Open the windows for an hour, then close them. The balcony is fine."
        elif who:
            plan = f"Most plans can stay, but keep {who} on a shorter outing and come in if breathing feels tight."
        else:
            plan = "You can keep a normal day. Save a long run for a cleaner hour."
    elif aqi <= 150:
        if focus == "school":
            plan = (
                f"Move PE indoors and keep the classroom windows shut. "
                f"{who + ' should wear a mask for pickup.' if who else 'A mask is worth it for pickup.'}"
            )
        elif focus == "evening":
            plan = "Leave the windows closed tonight, skip the balcony, and recirculate the fan while you cook."
        elif who:
            plan = f"Keep {who} inside for anything longer than a quick errand, and shut the windows."
        else:
            plan = "Treat this as a sensitive-group day: short trips, windows shut."
    else:
        if focus == "school":
            plan = f"No outdoor PE. Windows stay shut, and the school run gets a mask. {who + ' is who this is for.' if who else ''}".strip()
        elif focus == "evening":
            plan = "Stay in, windows closed, balcony off. A mask only if you absolutely have to step out."
        else:
            plan = "Stay inside. Cancel outdoor plans and keep the windows shut."
    if not known_people and aqi > 50:
        plan += " Tell me who lives here, especially any child or anyone with asthma, and I'll tighten this."
    closing = {
        "school": "I saved this as today's school plan.",
        "evening": "I saved this as tonight's plan.",
        "outdoor": "I saved this as the outdoor plan.",
        "now": "I saved this plan.",
    }[focus]
    return " ".join(part for part in (level, plan, closing) if part)
