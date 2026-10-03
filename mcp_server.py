#!/usr/bin/env python3
"""
mcp-local-telemetry — a minimal Model Context Protocol (MCP) server that
exposes local system telemetry (CPU, RAM, Disk) to MCP-aware AI agents
such as Claude Code, Cursor, and ChatGPT Desktop.

Transport: JSON-RPC 2.0 over stdio.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover - handled at tool-call time
    psutil = None

__version__ = "0.1.0"

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "mcp-local-telemetry", "version": __version__}

# JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Logs MUST go to stderr — stdout is reserved for JSON-RPC frames.
logging.basicConfig(
    level=os.environ.get("MCP_LOG_LEVEL", "WARNING"),
    stream=sys.stderr,
    format="[mcp-local-telemetry] %(levelname)s %(message)s",
)
log = logging.getLogger("mcp-local-telemetry")

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_system_metrics",
        "title": "Get System Metrics",
        "description": (
            "Returns current CPU, RAM, and Disk utilisation for the local "
            "machine. Useful for pre-flight checks before launching heavy "
            "builds, containers, or model inference."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_top_processes",
        "title": "Get Top Processes",
        "description": "Returns the N processes with the highest CPU usage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 5,
                    "description": "How many processes to return.",
                }
            },
            "additionalProperties": False,
        },
    },
]


def _ok(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _require_psutil() -> None:
    if psutil is None:
        raise RuntimeError(
            "psutil is not installed. Install with: pip install psutil"
        )


def _disk_root() -> str:
    return os.path.abspath(os.sep)


def tool_get_system_metrics() -> dict[str, Any]:
    _require_psutil()
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage(_disk_root()).percent,
        "load_avg": getattr(psutil, "getloadavg", lambda: (None,) * 3)(),
        "boot_time": psutil.boot_time(),
    }


def tool_get_top_processes(limit: int = 5) -> list[dict[str, Any]]:
    _require_psutil()
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            procs.append(
                {
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"],
                    "memory_percent": round(info["memory_percent"] or 0.0, 2),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda x: x["cpu_percent"] or 0.0, reverse=True)
    return procs[:limit]


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "get_system_metrics":
        payload = tool_get_system_metrics()
    elif name == "get_top_processes":
        limit = int(arguments.get("limit", 5))
        payload = tool_get_top_processes(limit)
    else:
        raise ValueError(f"Unknown tool: {name}")

    return {
        "content": [{"type": "text", "text": json.dumps(payload, default=str)}],
        "isError": False,
    }


def handle(req: dict[str, Any]) -> dict[str, Any] | None:
    method = req.get("method")
    req_id = req.get("id")

    # Notifications carry no id and MUST NOT receive a response.
    if req_id is None and isinstance(method, str) and method.startswith("notifications/"):
        log.debug("notification: %s", method)
        return None

    if method == "initialize":
        return _ok(
            req_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            },
        )

    if method == "ping":
        return _ok(req_id, {})

    if method == "tools/list":
        return _ok(req_id, {"tools": TOOLS})

    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not isinstance(name, str):
            return _err(req_id, INVALID_PARAMS, "params.name is required")
        try:
            return _ok(req_id, _call_tool(name, arguments))
        except ValueError as e:
            return _err(req_id, INVALID_PARAMS, str(e))
        except Exception as e:  # noqa: BLE001 - report as tool error, not crash
            log.exception("tool call failed")
            return _ok(
                req_id,
                {
                    "content": [{"type": "text", "text": f"error: {e}"}],
                    "isError": True,
                },
            )

    if method in {"resources/list", "prompts/list"}:
        # Advertise empty sets so clients that probe don't error out.
        key = method.split("/")[0]
        return _ok(req_id, {key: []})

    return _err(req_id, METHOD_NOT_FOUND, f"Method not found: {method}")


def _read_message() -> dict[str, Any] | None:
    """Read one JSON-RPC message. MCP stdio uses newline-delimited JSON."""
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return {}
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        log.warning("parse error: %s", e)
        return {"__parse_error__": str(e)}


def main() -> int:
    log.info("starting %s v%s", SERVER_INFO["name"], __version__)
    while True:
        req = _read_message()
        if req is None:
            break
        if not req:
            continue

        if "__parse_error__" in req:
            resp: dict[str, Any] | None = _err(None, PARSE_ERROR, req["__parse_error__"])
        else:
            try:
                resp = handle(req)
            except Exception as e:  # noqa: BLE001 - never die on one bad frame
                log.exception("handler crashed")
                resp = _err(req.get("id"), INTERNAL_ERROR, str(e))

        if resp is None:
            continue
        sys.stdout.write(json.dumps(resp, default=str) + "\n")
        sys.stdout.flush()

    log.info("stdin closed, exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
