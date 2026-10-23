"""Start the MCP server, then the Alexa+ simulator."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import uvicorn

from hearthline.web import create_app

ROOT = Path(__file__).resolve().parents[1]
MCP_PORT = int(os.environ.get("HEARTHLINE_MCP_PORT", "8765"))
WEB_PORT = int(os.environ.get("HEARTHLINE_WEB_PORT", "8080"))


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _wait_for_port(port: int, proc: subprocess.Popen, timeout: float = 20) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"MCP server exited with code {proc.returncode}. See data/mcp.log.")
        if _port_open(port):
            return
        time.sleep(0.2)
    raise RuntimeError(f"MCP server did not open port {port}. See data/mcp.log.")


def main() -> None:
    log_path = ROOT / "data" / "mcp.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "w", encoding="utf-8")  # noqa: SIM115
    env = os.environ.copy()
    env["HEARTHLINE_MCP_PORT"] = str(MCP_PORT)
    env["HEARTHLINE_MCP_URL"] = f"http://127.0.0.1:{MCP_PORT}/mcp"
    proc = subprocess.Popen(
        [sys.executable, "-m", "hearthline.server"],
        cwd=ROOT,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env=env,
    )
    try:
        _wait_for_port(MCP_PORT, proc)
        print(f"Hearthline MCP  http://127.0.0.1:{MCP_PORT}/mcp")
        print(f"Alexa+ simulator  http://127.0.0.1:{WEB_PORT}")
        uvicorn.run(create_app(), host="127.0.0.1", port=WEB_PORT, log_level="info")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        log_file.close()


if __name__ == "__main__":
    main()
