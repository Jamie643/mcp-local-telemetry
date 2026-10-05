"""Smoke tests for mcp_server.py.

These spawn the server as a subprocess and speak JSON-RPC to it over
stdio, exactly the way a real MCP client (Claude Code, Cursor, etc.) would.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "mcp_server.py"


def _run(messages: list[dict], *, expect_returncode: int = 0) -> list[dict]:
    """Feed JSON-RPC messages to the server, return parsed JSON responses.

    On failure, prints the server's stderr so the CI log actually shows
    what went wrong instead of an opaque unpacking error.
    """
    stdin_payload = "\n".join(json.dumps(m) for m in messages) + "\n"
    proc = subprocess.run(
        [sys.executable, str(SERVER)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        timeout=20,
    )

    if proc.returncode != expect_returncode:
        # Surface the real failure — this is the whole point of the test.
        raise AssertionError(
            f"server exited with code {proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n"
            f"--- stderr ---\n{proc.stderr}\n"
            f"--- sent ---\n{stdin_payload}"
        )

    out: list[dict] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise AssertionError(
                f"non-JSON line on stdout: {line!r}\n"
                f"--- full stdout ---\n{proc.stdout}\n"
                f"--- stderr ---\n{proc.stderr}"
            ) from e
    return out


# --- tests ---------------------------------------------------------------


def test_initialize_handshake():
    out = _run(
        [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}]
    )
    assert len(out) == 1, out
    resp = out[0]
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"]
    assert resp["result"]["serverInfo"]["name"] == "mcp-local-telemetry"


def test_tools_list():
    out = _run([{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    assert len(out) == 1, out
    names = {t["name"] for t in out[0]["result"]["tools"]}
    assert "get_system_metrics" in names
    assert "get_top_processes" in names


def test_tools_call_metrics():
    out = _run(
        [
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "get_system_metrics", "arguments": {}},
            }
        ]
    )
    assert len(out) == 1, out
    result = out[0]["result"]
    assert result["isError"] is False, result
    payload = json.loads(result["content"][0]["text"])
    assert isinstance(payload["cpu_percent"], (int, float))
    assert 0 <= payload["memory_percent"] <= 100
    assert 0 <= payload["disk_percent"] <= 100


def test_notifications_are_silent():
    out = _run(
        [
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 4, "method": "ping"},
        ]
    )
    # Server must NOT reply to the notification — only to the ping.
    assert len(out) == 1, out
    assert out[0]["id"] == 4


def test_unknown_method():
    out = _run(
        [{"jsonrpc": "2.0", "id": 5, "method": "does/not/exist"}]
    )
    assert len(out) == 1, out
    assert out[0]["error"]["code"] == -32601


def test_parse_error():
    # Deliberately send garbage; server should return -32700 and keep going.
    proc = subprocess.run(
        [sys.executable, str(SERVER)],
        input="not json\n",
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1, proc.stdout
    resp = json.loads(lines[0])
    assert resp["error"]["code"] == -32700
