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

## Install

```bash
pip install mcp-local-telemetry
