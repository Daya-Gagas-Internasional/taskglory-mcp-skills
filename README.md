# TaskGlory Skills

Hermes Agent skills for TaskGlory — install via `hermes skills tap add`.

## Skills

| Skill | Description |
|-------|-------------|
| `taskglory-ops` | Operasikan TaskGlory via MCP — 24 tools reference, workflows, agent identity |
| `chat-reply` | Auto-reply comment/chat/thread via SSE events |
| `taskglory-skill-manager` | Install/manage skills di TaskGlory agents |

## Install

```bash
# Add sebagai tap source
hermes skills tap add Daya-Gagas-Internasional/taskglory-mcp-skills

# Install semua skill
hermes skills install Daya-Gagas-Internasional/taskglory-mcp-skills/taskglory-ops --yes
hermes skills install Daya-Gagas-Internasional/taskglory-mcp-skills/chat-reply --yes
hermes skills install Daya-Gagas-Internasional/taskglory-mcp-skills/taskglory-skill-manager --yes

# Atau install individual
hermes skills install Daya-Gagas-Internasional/taskglory-mcp-skills/taskglory-ops
```

Restart Hermes setelah install.

## Requirements

- Hermes Agent with MCP support
- TaskGlory PAT token (`tgpat_xxx`)
- TaskGlory MCP server configured in `~/.hermes/config.yaml`