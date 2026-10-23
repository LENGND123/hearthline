"""Alexa+ simulator: a living-room page that talks to the MCP server."""

from __future__ import annotations

from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from hearthline.bridge import list_tool_names, run_turn

WEB_ROOT = Path(__file__).resolve().parents[1] / "web"


async def index(_: Request) -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


async def health(_: Request) -> JSONResponse:
    try:
        status = await list_tool_names()
    except Exception as exc:  # The page needs a clear down state, not a stack trace.
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)
    return JSONResponse(status)


async def say(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Send a JSON body with a text field."}, status_code=400)
    text = str(body.get("text") or "").strip()
    if not text:
        return JSONResponse({"error": "Say something first."}, status_code=400)
    if len(text) > 500:
        return JSONResponse({"error": "Keep a turn under 500 characters."}, status_code=400)
    try:
        reply = await run_turn(text)
    except Exception as exc:
        return JSONResponse(
            {"error": f"The MCP server didn't answer. {exc}"},
            status_code=502,
        )
    return JSONResponse(reply)


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/", index),
            Route("/api/health", health),
            Route("/api/say", say, methods=["POST"]),
            Mount("/static", app=StaticFiles(directory=WEB_ROOT), name="static"),
        ]
    )


app = create_app()
