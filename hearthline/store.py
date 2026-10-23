"""JSON files for the household profile and the brief history."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_LOCK = threading.Lock()


def data_dir() -> Path:
    override = os.environ.get("HEARTHLINE_DATA")
    if override:
        path = Path(override)
    else:
        path = Path(__file__).resolve().parents[1] / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def empty_household() -> dict:
    return {
        "home_name": "",
        "city": "",
        "place_label": "",
        "members": [],
        "routines": [],
        "last_brief": None,
        "updated_at": None,
    }


def _read(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp.replace(path)


def load_household() -> dict:
    with _LOCK:
        stored = _read(data_dir() / "household.json", None)
    if not isinstance(stored, dict):
        return empty_household()
    household = empty_household()
    household.update({key: stored.get(key, household[key]) for key in household})
    if not isinstance(household["members"], list):
        household["members"] = []
    if not isinstance(household["routines"], list):
        household["routines"] = []
    return household


def save_household(household: dict) -> dict:
    household["updated_at"] = now_iso()
    with _LOCK:
        _write(data_dir() / "household.json", household)
    return household


def upsert_member(household: dict, member: dict) -> dict:
    name = (member.get("name") or "").strip()
    if not name:
        return household
    key = name.casefold()
    members = household.setdefault("members", [])
    for existing in members:
        if str(existing.get("name", "")).casefold() == key:
            if member.get("role"):
                existing["role"] = member["role"]
            if member.get("age"):
                existing["age"] = member["age"]
            note = (member.get("note") or "").strip()
            if note and note not in existing.get("notes", []):
                existing.setdefault("notes", []).append(note)
            return household
    notes = []
    note = (member.get("note") or "").strip()
    if note:
        notes.append(note)
    members.append(
        {
            "name": name,
            "role": member.get("role") or "adult",
            "age": member.get("age") or None,
            "notes": notes,
        }
    )
    return household


def load_history() -> list[dict]:
    with _LOCK:
        stored = _read(data_dir() / "history.json", [])
    if not isinstance(stored, list):
        return []
    return [item for item in stored if isinstance(item, dict)]


def append_history(brief: dict) -> list[dict]:
    with _LOCK:
        history = _read(data_dir() / "history.json", [])
        if not isinstance(history, list):
            history = []
        history.append(brief)
        history = history[-20:]
        _write(data_dir() / "history.json", history)
    return history


def clear_all() -> None:
    with _LOCK:
        folder = data_dir()
        for name in ("household.json", "history.json", "air-cache.json"):
            path = folder / name
            if path.exists():
                path.unlink()


def load_air_cache() -> dict | None:
    with _LOCK:
        stored = _read(data_dir() / "air-cache.json", None)
    return stored if isinstance(stored, dict) else None


def save_air_cache(reading: dict) -> None:
    with _LOCK:
        _write(data_dir() / "air-cache.json", reading)
