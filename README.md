# TaskGlory Skills

Hermes Agent skills for TaskGlory — install via `hermes skills tap add`.

## Skills

| Skill | Description |
|-------|-------------|
| `taskglory-ops` | Operasikan TaskGlory via MCP — 24 tools reference, workflows, agent identity |
| `chat-reply` | Real-time auto-reply comment/chat/thread via SSE + Hermes CLI (PTY) |
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

## chat-reply Setup (v2.0)

Skill `chat-reply` v2.0 menggunakan SSE listener Python yang spawn Hermes CLI via PTY untuk auto-reply real-time. Tidak butuh cron atau queue file.

### Quick setup

1. Copy listener script:
   ```bash
   mkdir -p ~/.hermes/scripts
   cp scripts/taskglory_sse_listener.py ~/.hermes/scripts/   # dari skill folder
   ```

2. Get token + hermes path:
   ```bash
   grep -o 'tgpat_[a-f0-9]*' ~/.hermes/config.yaml
   which hermes
   ```

3. Test run:
   ```bash
   python3 ~/.hermes/scripts/taskglory_sse_listener.py "tgpat_xxx" &
   tail -f ~/.hermes/scripts/sse_listener.log
   ```

4. Setup persistent (launchd macOS / systemd Linux) — lihat SKILL.md untuk detail

5. Test: minta user lain comment/mention agent di task TaskGlory → agent auto-reply

### Penting

- `hermes -z` (one-shot) TIDAK load MCP tools. Listener pakai `hermes chat --cli` via PTY.
- launchd tidak load shell PATH — set `HERMES_BIN` full path di listener atau plist.
- Agent self-comment tidak trigger SSE (backend filter). Test pakai user lain.