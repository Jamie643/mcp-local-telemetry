#!/usr/bin/env python3
"""mcp-local-telemetry — minimal MCP server exposing local system metrics."""
import json
import os
import sys

try:
    import psutil
except ImportError:
    psutil = None

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "mcp-local-telemetry", "version": "0.1.0"}

TOOLS = [
    {
        "name": "get_system_metrics",
        "title": "Get System Metrics",
        "description": "Returns current CPU, RAM, and Disk telemetry for local execution checks.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    }
]


def _ok(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _get_metrics():
    if psutil is None:
        raise RuntimeError("psutil is not installed; run `pip install psutil`")
    root = os.path.abspath(os.sep)
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage(root).percent,
    }


def handle(req):
    method = req.get("method")
    req_id = req.get("id")

    # Notifications (no id) must never receive a response.
    if req_id is None and method and method.startswith("notifications/"):
        return None

    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })

    if method == "ping":
        return _ok(req_id, {})

    if method == "tools/list":
        return _ok(req_id, {"tools": TOOLS})

    if method == "tools/call":
        params = req.get("params") or {}
        if params.get("name") != "get_system_metrics":
            return _err(req_id, -32602, f"Unknown tool: {params.get('name')}")
        try:
            metrics = _get_metrics()
            return _ok(req_id, {
                "content": [{"type": "text", "text": json.dumps(metrics)}],
                "isError": False,
            })
        except Exception as e:
            return _ok(req_id, {
                "content": [{"type": "text", "text": f"error: {e}"}],
                "isError": True,
            })

    return _err(req_id, -32601, f"Method not found: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            resp = _err(None, -32700, f"Parse error: {e}")
        else:
            resp = handle(req)
        if resp is None:
            continue
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
