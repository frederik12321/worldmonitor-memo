# WorldMonitor MCP Server

An [MCP server](https://modelcontextprotocol.io) that gives Claude access to [WorldMonitor's](https://worldmonitor.app) real-time global intelligence data — 100+ sources covering geopolitics, military, markets, infrastructure, and more.

Use it with Claude Code's `/memo` skill to generate intelligence briefings on demand.

## What it does

38 tools across 12 categories, with TTL caching, async I/O, composite aggregation, and delta detection:

| Category | Tools |
|----------|-------|
| **Intelligence** | CII risk scores, country intel briefs, GDELT tensions, PIZZINT, GDELT article search |
| **News** | Global news digest (100+ feeds), FT headlines (public RSS) |
| **Military** | Theater posture, military flights, USNI fleet report |
| **Conflict & Unrest** | ACLED events, social unrest, humanitarian summaries |
| **Markets & Economy** | Market quotes, commodities, crypto, macro signals, energy prices, FRED data, central bank rates, ETF flows |
| **Supply Chain** | Shipping rates, chokepoint status, trade restrictions |
| **Infrastructure** | Internet outages, cyber threats, submarine cable health |
| **Maritime** | Vessel tracking, navigational warnings |
| **Environment** | Earthquakes, climate anomalies, wildfires, displacement data |
| **Composites** | Global briefing (9 endpoints), country dashboard (5 endpoints), market pulse (7 endpoints) |
| **Monitoring** | What's-new delta detection, cache status, server health |
| **Other** | Prediction markets |

## Architecture

```
worldmonitor_mcp/
  server.py          # FastMCP init, lifespan, composite/monitoring tools
  client.py          # Async HTTP client, TTL cache integration, health tracking
  cache.py           # In-memory TTL cache (3-tier: 3min / 10min / 30min)
  validation.py      # Input validation (NIST CSF: PROTECT)
  trimmer.py         # Response size control (8KB default, 16KB composites)
  delta.py           # Change detection between successive API responses
  tools/             # Domain tool modules (async, cached)
    intelligence.py, news.py, military.py, conflict.py, markets.py,
    supply_chain.py, infrastructure.py, maritime.py, environment.py,
    other.py, composites.py
tests/               # 58 tests (cache, validation, trimmer, delta)
```

**Key engineering features:**
- **Async throughout** — all tools are `async def`, HTTP calls use `httpx.AsyncClient`, composite tools use `asyncio.gather()` for parallel fetching
- **3-tier TTL cache** — fast (3min: markets, flights), medium (10min: news, conflict), slow (30min: risk scores, posture). No external dependencies
- **Response trimming** — strips null fields, caps list sizes, binary-search truncation to stay within token budgets
- **Composite tools** — `get_global_briefing()` replaces 12 individual calls; `get_country_dashboard(cc)` replaces 5; `get_market_pulse()` replaces 7
- **Delta detection** — `get_whats_new()` tracks which data sources changed since last check
- **API health tracking** — per-endpoint success rates and latency via `get_server_status()`

## Quick start

### 1. Install

```bash
pip install worldmonitor-mcp
```

Or from source:

```bash
git clone https://github.com/frederik12321/worldmonitor-memo
cd worldmonitor-mcp
pip install -e .
```

### 2. Configure Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "worldmonitor": {
      "command": "worldmonitor-mcp",
      "env": {
        "WORLDMONITOR_BASE_URL": "https://worldmonitor.app"
      }
    }
  }
}
```

If running from source:

```json
{
  "mcpServers": {
    "worldmonitor": {
      "command": "python",
      "args": ["-m", "worldmonitor_mcp.server"],
      "env": {
        "WORLDMONITOR_BASE_URL": "https://worldmonitor.app"
      }
    }
  }
}
```

### 3. Install the /memo skill

Copy the skill file to your Claude Code commands directory:

```bash
cp skills/memo.md ~/.claude/commands/memo.md
```

### 4. Use it

```
/memo           # global daily briefing
/memo UA        # global + Ukraine deep-dive
/memo IR        # global + Iran focus
```

Or just talk to Claude naturally — it has access to all 38 tools:

> "What's the current military posture in the Indo-Pacific theater?"
> "Show me countries with rising instability scores"
> "What changed since my last briefing?"

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORLDMONITOR_BASE_URL` | No | `https://worldmonitor.app` | API base URL |
| `WORLDMONITOR_API_KEY` | No | — | API key if your deployment requires auth |

## Security

This server follows NIST Cybersecurity Framework (CSF) principles:

- **URL pinning** — `BASE_URL` is validated against an allow-list at startup (no SSRF)
- **Credential scoping** — API key is never sent on redirects (redirects disabled)
- **Input validation** — All user parameters (country codes, enums, ranges) are validated before use
- **Defused XML** — RSS parsing uses `defusedxml` to prevent XXE and entity expansion attacks
- **Sanitised errors** — Error responses never leak internal URLs, paths, or credentials
- **Credential isolation** — Secrets stay in environment variables, never in code

## Attribution

This MCP server is a **client** that consumes the public API of [WorldMonitor](https://github.com/koala73/worldmonitor), a real-time global intelligence dashboard created by **Elie Habib**. WorldMonitor is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](https://github.com/koala73/worldmonitor?tab=License-1-ov-file).

This project does **not** include, copy, or modify any WorldMonitor source code — it communicates with a running WorldMonitor instance over HTTP. As an independent API client, this MCP server is licensed separately under MIT.

## License

MIT — see [LICENSE](LICENSE).

The [WorldMonitor](https://github.com/koala73/worldmonitor) platform this server connects to is © 2024-2026 Elie Habib, licensed under [AGPL-3.0](https://github.com/koala73/worldmonitor/blob/main/LICENSE).
