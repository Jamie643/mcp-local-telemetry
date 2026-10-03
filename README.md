# mcp-local-telemetry

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

## Install

```bash
git clone https://github.com/Jamie643/mcp-local-telemetry.git
cd mcp-local-telemetry
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
