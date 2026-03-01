# WorldMonitor MCP Server

An [MCP server](https://modelcontextprotocol.io) that gives Claude access to [WorldMonitor's](https://worldmonitor.app) real-time global intelligence data — 100+ sources covering geopolitics, military, markets, infrastructure, and more.

Use it with Claude Code's `/memo` skill to generate intelligence briefings on demand.

## What it does

33 tools that let Claude pull live data:

| Category | Tools |
|----------|-------|
| **Intelligence** | CII risk scores, country intel briefs, GDELT tensions, PIZZINT, GDELT article search |
| **News** | Global news digest (100+ feeds), Financial Times (8 sections) |
| **Military** | Theater posture, military flights, USNI fleet report |
| **Conflict & Unrest** | ACLED events, social unrest, humanitarian summaries |
| **Markets & Economy** | Market quotes, commodities, crypto, macro signals, energy prices, FRED data, central bank rates |
| **Supply Chain** | Shipping rates, chokepoint status, trade restrictions |
| **Infrastructure** | Internet outages, cyber threats, submarine cable health |
| **Maritime** | Vessel tracking, navigational warnings |
| **Other** | Prediction markets, earthquakes, climate anomalies, wildfires, displacement data, ETF flows |

## Quick start

### 1. Install

```bash
pip install worldmonitor-mcp
```

Or from source:

```bash
git clone https://github.com/YOUR_USERNAME/worldmonitor-mcp
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

Or just talk to Claude naturally — it has access to all 33 tools:

> "What's the current military posture in the Indo-Pacific theater?"
> "Show me countries with rising instability scores"
> "What are the FT's top stories today?"

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

## License

MIT
