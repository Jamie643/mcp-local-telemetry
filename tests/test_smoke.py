import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "mcp_server.py"


def _run(messages: list[dict]) -> list[dict]:
    proc = subprocess.run(
        [sys.executable, str(SERVER)],
        input="\n".join(json.dumps(m) for m in messages) + "\n",
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def test_initialize_handshake():
    (resp,) = _run([{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}])
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"]
    assert resp["result"]["serverInfo"]["name"] == "mcp-local-telemetry"


def test_tools_list():
    (resp,) = _run([{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}])
    names = {t["name"] for t in resp["result"]["tools"]}
    assert "get_system_metrics" in names
    assert "get_top_processes" in names


def test_tools_call_metrics():
    (resp,) = _run([
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_system_metrics", "arguments": {}},
        }
    ])
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert 0 <= payload["cpu_percent"] <= 100 * 4  # multi-core sanity
    assert 0 <= payload["memory_percent"] <= 100
    assert 0 <= payload["disk_percent"] <= 100


def test_notifications_are_silent():
    out = _run([
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 4, "method": "ping"},
    ])
    assert len(out) == 1
    assert out[0]["id"] == 4


def test_unknown_method():
    (resp,) = _run([{"jsonrpc": "2.0", "id": 5, "method": "does/not/exist"}])
    assert resp["error"]["code"] == -32601


def test_parse_error():
    proc = subprocess.run(
        [sys.executable, str(SERVER)],
        input="not json\n",
        capture_output=True,
        text=True,
        timeout=15,
    )
    (resp,) = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
    assert resp["error"]["code"] == -32700
