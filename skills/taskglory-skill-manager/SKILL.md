---
name: taskglory-skill-manager
description: Install, manage, dan configure skills di TaskGlory agents. Save PAT token, list agents, install/uninstall skills via API.
version: 1.0.0
author: awan
---

# TaskGlory Skill Manager

Manage skills pada TaskGlory agents — save token, list agents, install/uninstall skills.

## Prerequisites

- TaskGlory PAT token (format: `tgpat_xxx`) — dapat dari TaskGlory settings page
- TaskGlory MCP server ter-config di Hermes config (`config.yaml` di Hermes home dir, biasanya `~/.hermes/`)

## Setup: Save Token

Token disimpan di Hermes config (`config.yaml` di Hermes home dir):

```yaml
mcp_servers:
  taskglory:
    url: https://dev.taskglory.com/api/mcp
    headers:
      Authorization: Bearer tgpat_xxxxxxxxxxxx
```

Setelah edit config, restart Hermes.

## Install Skill ke Agent

### Step 1: Dapatkan Workspace ID

Panggil MCP tool `workspace_overview` (lewat Hermes atau curl):

```bash
curl -s -X POST https://dev.taskglory.com/api/mcp \
  -H "Authorization: Bearer tgpat_xxx" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"workspace_overview","arguments":{}},"id":1}' \
  | python3 -m json.tool
```

Simpan `workspace.id` dari response.

### Step 2: List Agents

```bash
curl -s -X GET "https://dev.taskglory.com/api/workspaces/<workspace_id>/agents" \
  -H "Authorization: Bearer tgpat_xxx" \
  | python3 -m json.tool
```

Response: array agent dengan `id`, `display_name`, `owner_name`, `skills_config`.

### Step 3: Install Skill

```bash
curl -s -X POST https://dev.taskglory.com/api/agents/skills/install \
  -H "Authorization: Bearer tgpat_xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "<agent_uuid>",
    "skill_id": "my-skill-name",
    "version": "1.0.0",
    "description": "What this skill does",
    "source_url": "https://github.com/owner/repo"
  }' \
  | python3 -m json.tool
```

Response sukses:
```json
{
  "message": "Skill my-skill-name installed successfully",
  "status": "installed",
  "skill": {
    "name": "my-skill-name",
    "version": "1.0.0",
    "description": "What this skill does",
    "source_url": "https://github.com/owner/repo",
    "installed_at": "2026-09-18T10:00:00",
    "installed_by": "email@user.com"
  },
  "agent_display_name": "Sarah (Ibrahim Aghythara's Agent)"
}
```

### Step 4: Verify

```bash
curl -s -X GET "https://dev.taskglory.com/api/superadmin/agents/<agent_id>" \
  -H "Authorization: Bearer tgpat_xxx" \
  | python3 -m json.tool
```

Cek field `skills_config`.

## Default Skills (Auto-Install saat Agent Dibuat)

| Skill | Fungsi |
|-------|--------|
| `taskglory-ops` | Query task/user/workspace via MCP |
| `chat-reply` | Balas comment/chat/thread otomatis |

## Uninstall Skill

```bash
curl -s -X DELETE "https://dev.taskglory.com/api/superadmin/agents/<agent_id>/skills/<skill_id>" \
  -H "Authorization: Bearer tgpat_xxx"
```

## Permission Rules

- Hanya **owner agent** atau **superadmin** yang bisa install/uninstall skill
- Hanya **owner agent** atau **superadmin** yang bisa mention/assign agent
- Agent user tidak bisa install skill ke dirinya sendiri

## Error Handling

| HTTP Status | Error | Penyebab |
|-------------|-------|----------|
| 403 | Only agent owner or superadmin can install skills | Bukan owner agent |
| 403 | Source URL not in allowed list | source_url tidak match tools_scope |
| 400 | Skill already installed | Skill sudah ada |
| 404 | Agent not found | agent_id salah |

## Agent Identity

Cek identitas agent via `workspace_overview` — ada field `agent_identity`:

```json
{
  "agent_identity": {
    "id": "uuid",
    "name": "Sarah",
    "display_name": "Sarah (Ibrahim Aghythara's Agent)",
    "owner_name": "Ibrahim Aghythara",
    "owner_email": "ibrahim@example.com"
  }
}
```

## API Quick Reference

| Action | Method | Endpoint |
|--------|--------|----------|
| List agents | GET | `/api/workspaces/{ws_id}/agents` |
| Agent detail | GET | `/api/superadmin/agents/{agent_id}` |
| Install skill | POST | `/api/agents/skills/install` |
| Uninstall skill | DELETE | `/api/superadmin/agents/{agent_id}/skills/{skill_id}` |
| Workspace overview | MCP | `workspace_overview` tool |