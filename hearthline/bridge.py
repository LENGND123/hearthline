"""One Alexa+ turn: open a Streamable HTTP session and call Hearthline's tools."""

from __future__ import annotations

import json
import os

from mcp import Client

from hearthline.agent import respond

DEFAULT_MCP_URL = "http://127.0.0.1:8765/mcp"


def mcp_url() -> str:
    return os.environ.get("HEARTHLINE_MCP_URL", DEFAULT_MCP_URL)


def _text(result) -> str:
    parts: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    if parts:
        return "\n".join(parts)
    structured = getattr(result, "structuredContent", None)
    if structured is None:
        structured = getattr(result, "structured_content", None)
    if structured is not None:
        return json.dumps(structured)
    return ""


def _payload(result) -> dict:
    if getattr(result, "isError", False) or getattr(result, "is_error", False):
        raise RuntimeError(_text(result) or "The MCP tool returned an error.")
    raw = _text(result).strip()
    if not raw:
        raise RuntimeError("The MCP tool returned an empty result.")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise RuntimeError("The MCP tool returned a result that was not an object.")
    return data


async def run_turn(text: str) -> dict:
    # mode="legacy" forces the 2025-11-25 initialize handshake the hackathon names.
    async with Client(mcp_url(), mode="legacy") as client:
        protocol = client.protocol_version
        trace: list[dict] = []

        async def call(name: str, arguments: dict) -> dict:
            result = await client.call_tool(name, arguments)
            payload = _payload(result)
            preview = payload.get("speech") or payload.get("error") or payload.get("place_label") or name
            trace.append(
                {
                    "tool": name,
                    "arguments": arguments,
                    "ok": bool(payload.get("ok", True)),
                    "preview": str(preview)[:180],
                }
            )
            return payload

        reply = await respond(text, call)
    reply["protocol"] = protocol
    reply["trace"] = trace
    return reply


async def list_tool_names() -> dict:
    async with Client(mcp_url(), mode="legacy") as client:
        listed = await client.list_tools()
        names = []
        tools = getattr(listed, "tools", listed)
        for tool in tools:
            names.append(getattr(tool, "name", str(tool)))
        return {"ok": True, "protocol": client.protocol_version, "tools": names}
