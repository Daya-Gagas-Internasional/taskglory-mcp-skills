---
name: taskglory-ops
description: Operasikan TaskGlory via MCP — query task, space, list, member, comment, channel, file. Auto-reply comment & chat.
version: 1.0.0
author: awan
---

# TaskGlory Operations

Query dan manage TaskGlory workspace via MCP tools. Semua 24 MCP tools available.

## MCP Tools Reference

### Read Tools (10)

| Tool | Params | Fungsi |
|------|--------|--------|
| `workspace_overview` | — | Workspace info + agent identity + task counts by status |
| `space_list` | limit, offset | List spaces di workspace |
| `space_get` | space_id | Detail space + lists di dalamnya |
| `list_list` | space_id, limit, offset | List lists di dalam space |
| `task_list` | space_id?, list_id?, status?, assignee_id?, search?, due_before?, due_after?, limit, offset | List tasks dengan filter |
| `task_get` | task_id | Detail task: description, checklist, assignees, tags, status history, attachments, time logs |
| `task_comments` | task_id, limit, offset | Comments di task (oldest first) |
| `member_list` | role?, limit, offset | Workspace members |
| `file_list` | task_id?, space_id?, limit, offset | Files di workspace/task/space |
| `file_get` | file_id | File metadata + presigned download URL (15 min) |

### Write Tools (14)

| Tool | Params | Fungsi |
|------|--------|--------|
| `task_create` | title, list_id, space_id?, description?, status?, priority?, category?, due_date?, start_date?, assignee_ids?, time_estimate?, tags?, is_meeting? | Buat task baru, auto-generate task_code |
| `task_update` | task_id, title?, description?, status?, priority?, category?, due_date?, start_date?, assignee_ids?, checklist?, tags?, time_estimate? | Update task, hanya field yang dikirim |
| `task_comment_add` | task_id, body, mentions? | Tambah comment ke task |
| `task_comment_edit` | comment_id, body | Edit comment milik agent sendiri |
| `channel_list` | limit, offset | List channels di workspace |
| `channel_get` | channel_id | Detail channel |
| `channel_messages` | channel_id, limit, before? | Messages di channel (newest first) |
| `channel_send` | channel_id, content, parent_id?, mentions? | Kirim message ke channel / reply thread |
| `dm_list` | limit, offset | List DM conversations agent |
| `dm_send` | conversation_id, content, mentions? | Kirim DM |
| `notification_list` | limit, offset, unread_only? | Notifications agent |
| `file_upload` | filename, content_base64, content_type?, task_id?, space_id? | Upload file dari base64 |
| `file_upload_url` | filename, url, content_type?, task_id?, space_id? | Upload file dari URL |
| `timelog_add` | task_id, duration, log_type?, description?, is_billable?, logged_date? | Add time log (duration in minutes) |

## Agent Identity

`workspace_overview` return `agent_identity`:

```json
{
  "agent_identity": {
    "id": "uuid",
    "name": "Sarah",
    "email": "agent-sarah@agents.taskglory.com",
    "display_name": "Sarah (Ibrahim Aghythara's Agent)",
    "owner_name": "Ibrahim Aghythara",
    "owner_email": "ibrahim@example.com"
  }
}
```

Gunakan ini untuk:
- Tahu siapa diri agent
- Tahu siapa owner/tuan agent
- Tahu siapa yang ngajak bicara (dari comment/message author)

## Common Workflows

### Cari & Ambil Task User

1. `member_list` → cari user by email → dapat `id`
2. `task_list(assignee_id=<id>, status="To Do")` — filter by status bila perlu
3. `task_get(task_id=...)` untuk detail

### Buat Task Baru

1. `space_list` → cari space yang sesuai
2. `space_get(space_id=...)` → dapat `list_id`
3. `task_create(title=..., list_id=..., space_id=..., description=...)` → auto-generate task_code
4. `task_update(task_id=..., assignee_ids=[...])` → assign ke member
5. `task_comment_add(task_id=..., body=..., mentions=[member_id])` → notify via @mention

### Balas Comment di Task

1. `task_comments(task_id=...)` → baca comment terbaru
2. `task_comment_add(task_id=..., body="balasan...", mentions=[user_id])` → balas

### Kirim Chat ke Channel

1. `channel_list()` → cari channel
2. `channel_messages(channel_id=...)` → baca pesan terbaru
3. `channel_send(channel_id=..., content="pesan...", parent_id=msg_id)` → reply thread

### Kirim DM

1. `dm_list()` → cek conversation yang ada
2. `dm_send(conversation_id=..., content="pesan...")` → kirim

## Status Values

`"To Do"`, `"In Progress"`, `"Review"`, `"Done"`, `"Deploy To Dev"`, `"Deploy in Dev"`, `"Deploy To Prod"`, `"Completed"`, `"Done In Local"`

## Priority Values

`"none"`, `"urgent"`, `"high"`, `"medium"`, `"low"`

## Audit Log

Setiap write action (create/update/comment/send) otomatis tercatat di Audit Logs:
- `user_name` = agent display name
- `action` = create/update
- `entity_type` = task/comment/channel_message/direct_message/file/timelog
- `changes` = field changes dengan old/new values

## Access Control

- Agent hanya bisa di-mention/assign oleh **owner** atau **superadmin**
- Agent hanya bisa edit comment miliknya sendiri
- Agent harus punya MCP consent active di workspace