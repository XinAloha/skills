# Portable Loader Prompt

Use this prompt in agents that do not natively discover `SKILL.md` folders.

```text
You have access to a local skill named skill-northbound-margin-monitor at:
<NORTHBOUND_MARGIN_MONITOR_SKILL_ROOT>

When the user request matches this skill's SKILL.md description:
1. Read <NORTHBOUND_MARGIN_MONITOR_SKILL_ROOT>/SKILL.md.
2. Follow the workflow and guardrails in that file exactly.
3. Load referenced files under <NORTHBOUND_MARGIN_MONITOR_SKILL_ROOT>/references/ only when needed.
4. Run bundled scripts from the skill root only after reading the relevant instructions.
5. Preserve documented API names, parameters, file paths, formulas, validation limits, and freshness notes.
6. Do not invent data interfaces, credentials, factor definitions, or runtime behavior that is not supported by the skill files.
```

## MCP Server Integration

The skill can also be called by LLMs via its MCP server. Start the server with:

```bash
cd <SKILL_ROOT>
python mcp_server.py
```

### Claude Code (claude.ai/code)

Add to `.claude/mcp.json` or `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "northbound-margin-monitor": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "<SKILL_ROOT>",
      "env": {
        "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
        "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
        "ANTHROPIC_MODEL": "deepseek-v4-pro",
        "DEFAULT_USERNAME": "86xxxxxxxxxxx",
        "DEFAULT_PASSWORD": "xxx"
      }
    }
  }
}
```

### Available Tools

| Tool | Description |
|---|---|
| `run_panorama_monitor` | Run full panorama monitoring analysis for a given date |
| `get_latest_report` | Read the most recent panorama report |
| `check_trading_day` | Verify if a date is an A-share trading day |

### Direct CLI

```bash
python run.py                    # Default run, latest trading day
python run.py --date 20260630    # Specify date
python run.py --no-cache         # Force fresh data
python run.py --summary          # Summary mode (LLM 150-200 chars)
python run.py --top-n 30 --verbose  # Custom TOP-N + verbose
```

All data is from real sources (Pandadata + AKShare + LLM API). No mock/dry-run mode.
