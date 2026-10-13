# mcp-local-telemetry

[![CI](https://github.com/Jamie643/mcp-local-telemetry/actions/workflows/ci.yml/badge.svg)](https://github.com/Jamie643/mcp-local-telemetry/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-local-telemetry.svg)](https://pypi.org/project/mcp-local-telemetry/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-local-telemetry.svg)](https://pypi.org/project/mcp-local-telemetry/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/Jamie643/mcp-local-telemetry/blob/main/LICENSE)

A lightweight [Model Context Protocol](https://modelcontextprotocol.io) server that
exposes local system telemetry (CPU, RAM, Disk, top processes) to MCP-aware AI
agents — Claude Code, Cursor, ChatGPT Desktop, and any other MCP client.

Written as a single-file, dependency-light Python script. Ships in under 200
lines and speaks JSON-RPC 2.0 over stdio.

## Why

AI coding agents are increasingly asked to reason about the machine they are
running on — *"is it safe to run this build?", "what's eating CPU right now?"*.
This server gives them a structured, protocol-standard way to ask.

## Tools

| Tool | Description |
| --- | --- |
| `get_system_metrics` | CPU %, memory %, disk %, load average, boot time. |
| `get_top_processes` | Top-N processes by CPU usage. |

## Or install from source:

git clone https://github.com/Jamie643/mcp-local-telemetry.git
cd mcp-local-telemetry
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .

## Claude Code

claude mcp add local-telemetry -- mcp-local-telemetry

## Cursor / Claude Desktop (mcp.json)

{
  "mcpServers": {
    "local-telemetry": {
      "command": "mcp-local-telemetry"
    }
  }
}

## Manual smoke test

printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_system_metrics","arguments":{}}}' \
  | mcp-local-telemetry

## Development

  pip install -e ".[dev]"
ruff check .
mypy mcp_server.py
pytest

## Protocol notes

Transport: JSON-RPC 2.0 over stdio, newline-delimited.

Protocol version: 2024-11-05.

Capabilities: tools only.

All logs go to stderr; stdout carries only JSON-RPC frames.

## License
MIT — see LICENSE.


## Commit it

```bash
git add README.md
git commit -m "Rewrite README: add badges, remove unrelated stack section, use PyPI install"
git push

## Install

```bash
pip install mcp-local-telemetry
