---
name: chat-reply
description: Auto-reply comment, chat & thread di TaskGlory. Listen SSE events, process, balas via MCP tools.
version: 1.0.0
author: awan
---

# Chat Reply — Auto-Reply via SSE

Auto-reply comment, channel message, dan DM berdasarkan SSE events dari TaskGlory.

## Cara Kerja

```
User comment/message/mention
    ↓
TaskGlory backend → Redis pub/sub
    ↓
SSE stream (mcp:notify:{consent_id})
    ↓
Agent listener (Hermes)
    ↓
Process + generate reply
    ↓
MCP tools (task_comment_add / channel_send / dm_send)
```

## SSE Event Types

| Event | Trigger | Data |
|-------|---------|------|
| `task_assigned` | Agent di-assign ke task | task_id, task_title |
| `mentioned` | Agent di-mention di channel | message_id, channel_name |
| `comment_created` | Comment di task agent | task_id, task_code, comment_id, author_name, content_preview |
| `channel_message` | Message di channel agent | channel_id, channel_name, message_id, author_name, content_preview |
| `direct_message` | DM ke agent | conversation_id, message_id, sender_name, content_preview |
| `task_mention` | Agent di-mention di task comment | task_id, task_code, comment_id, author_name, content_preview |

## SSE Endpoint

```bash
curl -N https://dev.taskglory.com/api/mcp/sse \
  -H "Authorization: Bearer tgpat_xxx"
```

Response stream (Server-Sent Events):
```
data: {"event":"comment_created","data":{"task_id":"...","task_code":"MDTS-414","comment_id":"...","author_name":"Ibrahim","content_preview":"tolong update status..."}}

data: {"event":"direct_message","data":{"conversation_id":"...","message_id":"...","sender_name":"Awan","content_preview":"halo sarah..."}}
```

## Auto-Reply Workflow

### Reply Comment di Task

1. Listen SSE event `comment_created` atau `task_mention`
2. Parse data: `task_id`, `comment_id`, `content_preview`, `author_name`
3. Baca full comment: `task_comments(task_id=...)`
4. Generate reply berdasarkan konten + agent persona/instructions
5. Kirim reply: `task_comment_add(task_id=..., body="...", mentions=[author_id])`

### Reply Channel Message

1. Listen SSE event `channel_message` atau `mentioned`
2. Parse data: `channel_id`, `message_id`, `content_preview`, `author_name`
3. Baca full message: `channel_messages(channel_id=...)`
4. Generate reply
5. Kirim reply: `channel_send(channel_id=..., content="...", parent_id=message_id)` — reply as thread

### Reply DM

1. Listen SSE event `direct_message`
2. Parse data: `conversation_id`, `message_id`, `sender_name`, `content_preview`
3. Generate reply
4. Kirim: `dm_send(conversation_id=..., content="...")`

## Agent Persona

Agent punya persona/instructions di AgentConfig:
- `persona` — karakter agent (mis. "Sarah, assistant yang ramah dan precise")
- `jobdesk` — tugas utama agent
- `instructions` — aturan behavior

Gunakan persona ini saat generate reply.

## Access Control

- Agent hanya bisa di-mention oleh owner atau superadmin
- Jika user lain mention agent, mention akan di-filter (tidak sampai)
- Agent tetap bisa balas jika comment/message tidak mention tapi agent adalah assignee/channel member/DM participant

## Python Listener Example

```python
import json
import requests

def listen_sse(token, base_url="https://dev.taskglory.com"):
    """Listen to TaskGlory SSE stream."""
    response = requests.get(
        f"{base_url}/api/mcp/sse",
        headers={"Authorization": f"Bearer {token}"},
        stream=True,
        timeout=None,
    )

    for line in response.iter_lines():
        if line.startswith(b"data: "):
            event = json.loads(line[6:])
            handle_event(event)

def handle_event(event):
    """Process SSE event and auto-reply."""
    etype = event.get("event")
    data = event.get("data", {})

    if etype in ("comment_created", "task_mention"):
        # Reply to task comment
        task_id = data.get("task_id")
        author = data.get("author_name")
        preview = data.get("content_preview")
        # Generate reply...
        # task_comment_add(task_id=task_id, body=f"Hi {author}, ...")

    elif etype in ("channel_message", "mentioned"):
        # Reply to channel message
        channel_id = data.get("channel_id")
        msg_id = data.get("message_id")
        # channel_send(channel_id=channel_id, content="...", parent_id=msg_id)

    elif etype == "direct_message":
        # Reply to DM
        conv_id = data.get("conversation_id")
        # dm_send(conversation_id=conv_id, content="...")
```