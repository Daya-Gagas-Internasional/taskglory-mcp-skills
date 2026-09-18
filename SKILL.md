---
name: taskglory-skill-manager
description: Install, manage, and configure skills on TaskGlory agents. Save PAT token, list agents, install skills via API.
version: 1.0.0
author: awan
---

# TaskGlory Skill Manager

Manage skills on TaskGlory agents — save token, list agents, install/uninstall skills.

## Prerequisites

- TaskGlory PAT token (format: `tgpat_xxx`) — get from TaskGlory settings page
- TaskGlory MCP server configured in `~/.hermes/config.yaml`

## Setup: Save Token

Token disimpan di Hermes config (`~/.hermes/config.yaml`) under `mcp_servers.taskglory`:

```yaml
mcp_servers:
  taskglory:
    url: https://dev.taskglory.com/api/mcp
    headers:
      Authorization: Bearer tgpat_xxxxxxxxxxxx
```

Kalau belum ada, edit config manual atau jalankan:

```bash
hermes config set mcp_servers.taskglory.url https://dev.taskglory.com/api/mcp
hermes config set mcp_servers.taskglory.headers.Authorization "Bearer tgpat_xxxxxxxxxxxx"
```

Restart Hermes setelah edit config.

## Step-by-step: Install Skill ke Agent

### Step 1: Dapatkan Workspace ID

Panggil MCP tool `workspace_overview`:

```
mcp__taskglory__workspace_overview
```

Atau via terminal:

```bash
curl -s -X POST https://dev.taskglory.com/api/mcp \
  -H "Authorization: Bearer tgpat_xxx" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"workspace_overview","arguments":{}},"id":1}' \
  | python3 -m json.tool
```

Response ada `workspace.id` — simpan UUID ini.

### Step 2: List Agents di Workspace

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

### Step 4: Verify Skills Terinstall

```bash
curl -s -X GET "https://dev.taskglory.com/api/superadmin/agents/<agent_id>" \
  -H "Authorization: Bearer tgpat_xxx" \
  | python3 -m json.tool
```

Cek field `skills_config` — array skill yang sudah terinstall.

## Default Skills (Auto-Install)

Saat agent dibuat via API, otomatis terinstall:
- `taskglory-ops` — query task/user/workspace via MCP
- `chat-reply` — balas comment/chat/thread otomatis

## Uninstall Skill

```bash
curl -s -X DELETE "https://dev.taskglory.com/api/superadmin/agents/<agent_id>/skills/<skill_id>" \
  -H "Authorization: Bearer tgpat_xxx"
```

## Permission Rules

- Hanya **owner agent** atau **superadmin** yang bisa install/uninstall skill
- Hanya **owner agent** atau **superadmin** yang bisa mention/assign agent ke task
- Agent user (`is_agent=True`) tidak bisa install skill ke dirinya sendiri

## Agent Identity

Cek siapa agent kamu lewat `workspace_overview` — response ada `agent_identity`:

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

## Quick Reference

| Action | Method | Endpoint |
|--------|--------|----------|
| List agents | GET | `/api/workspaces/{ws_id}/agents` |
| Install skill | POST | `/api/agents/skills/install` |
| Uninstall skill | DELETE | `/api/superadmin/agents/{agent_id}/skills/{skill_id}` |
| Agent detail | GET | `/api/superadmin/agents/{agent_id}` |
| Workspace overview | MCP | `workspace_overview` tool |