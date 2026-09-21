---
name: chat-reply
description: Auto-reply comment, chat & thread di TaskGlory. SSE listener → Hermes CLI (PTY) → MCP tools. Real-time, tanpa queue/cron.
version: 2.0.0
author: awan
---

# Chat Reply — Real-time Auto-Reply via SSE + Hermes CLI

Auto-reply comment, channel message, dan DM berdasarkan SSE events dari TaskGlory. Real-time: saat event masuk, listener langsung spawn Hermes → MCP tools → reply terkirim.

## Arsitektur (v2.0)

```
User comment/message/mention
    ↓
TaskGlory backend → Redis pub/sub
    ↓
SSE stream (/api/mcp/sse)
    ↓
Python listener (taskglory_sse_listener.py) — bg process / launchd
    ↓
Spawn `hermes chat --cli` via PTY (MCP tools loaded)
    ↓
Hermes baca task/comments + generate reply via MCP tools
    ↓
task_comment_add / channel_send / dm_send → reply terkirim
```

TANPA queue file. TANPA cron. Real-time.

## Prerequisites

1. **Hermes Agent** installed (`hermes` binary di PATH atau full path)
2. **MCP taskglory** configured & tested: `hermes mcp test taskglory` ✓
3. **TaskGlory PAT token** (`tgpat_xxx`) — ada di `~/.hermes/config.yaml` section `mcp_servers.taskglory.headers.Authorization`

Cek token:
```bash
grep -o 'tgpat_[a-f0-9]*' ~/.hermes/config.yaml
```

Cek hermes path:
```bash
which hermes
```

## Setup

### 1. Copy listener script

Copy `taskglory_sse_listener.py` (dari `scripts/` folder skill ini) ke `~/.hermes/scripts/`:

```bash
mkdir -p ~/.hermes/scripts
cp scripts/taskglory_sse_listener.py ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/taskglory_sse_listener.py
```

### 2. Update hermes path di listener

Edit `~/.hermes/scripts/taskglory_sse_listener.py`, cari baris:

```python
HERMES_BIN = os.environ.get("HERMES_BIN", "/Users/awan/.local/bin/hermes")
```

Ganti path sesuai output `which hermes` di mesin kamu.

### 3. Start listener

Manual (untuk test):
```bash
python3 ~/.hermes/scripts/taskglory_sse_listener.py "tgpat_xxx" &
```

Cek log:
```bash
tail -f ~/.hermes/scripts/sse_listener.log
```

Harus muncul:
```
[SSE] Connected. Status=200. Listening for events...
```

### 4. Setup persistent (launchd macOS)

Buat plist `~/Library/LaunchAgents/com.hermes.taskglory-sse.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hermes.taskglory-sse</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USERNAME/.hermes/scripts/taskglory_sse_listener.py</string>
        <string>tgpat_YOUR_TOKEN</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/.hermes/scripts/sse_listener_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/.hermes/scripts/sse_listener_stderr.log</string>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/.hermes/scripts</string>
</dict>
</plist>
```

Ganti `YOUR_USERNAME`, `YOUR_TOKEN`, dan python path (`/usr/bin/python3` atau path homebrew python).

Load:
```bash
launchctl load ~/Library/LaunchAgents/com.hermes.taskglory-sse.plist
```

Cek status:
```bash
launchctl list | grep taskglory-sse
```

Unload:
```bash
launchctl unload ~/Library/LaunchAgents/com.hermes.taskglory-sse.plist
```

### 5. Setup persistent (Linux systemd)

Buat `~/.config/systemd/user/taskglory-sse.service`:

```ini
[Unit]
Description=TaskGlory SSE Auto-Reply Listener
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 %h/.hermes/scripts/taskglory_sse_listener.py tgpat_YOUR_TOKEN
Restart=always
RestartSec=3
Environment=HERMES_BIN=%h/.local/bin/hermes

[Install]
WantedBy=default.target
```

Enable:
```bash
systemctl --user enable --now taskglory-sse
```

## SSE Event Types

| Event | Trigger | Data Fields |
|-------|---------|-------------|
| `comment_created` | Comment di task agent | task_id, task_code, comment_id, author_name, content_preview |
| `task_mention` | Agent di-mention di task comment | task_id, task_code, comment_id, author_name, content_preview |
| `channel_message` | Message di channel agent | channel_id, channel_name, message_id, author_name, content_preview |
| `mentioned` | Agent di-mention di channel | message_id, channel_name |
| `direct_message` | DM ke agent | conversation_id, message_id, sender_name, content_preview |
| `task_assigned` | Agent di-assign ke task | task_id, task_title |

## Auto-Reply Workflow

### Reply Comment di Task

1. SSE event `comment_created` atau `task_mention` masuk
2. Listener parse: task_id, comment_id, author_name, content_preview
3. Listener spawn Hermes CLI via PTY dengan prompt berisi event detail
4. Hermes baca task detail: `task_get(task_id=...)`
5. Hermes baca comments: `task_comments(task_id=...)`
6. Hermes generate reply berdasarkan konten + agent persona
7. Hermes kirim: `task_comment_add(task_id=..., body="...", mentions=[author_id])`

### Reply Channel Message

1. SSE event `channel_message` atau `mentioned`
2. Listener parse: channel_id, message_id, author_name, content_preview
3. Hermes baca messages: `channel_messages(channel_id=...)`
4. Hermes kirim reply: `channel_send(channel_id=..., content="...", parent_id=message_id)`

### Reply DM

1. SSE event `direct_message`
2. Listener parse: conversation_id, message_id, sender_name, content_preview
3. Hermes kirim: `dm_send(conversation_id=..., content="...")`

## Agent Persona

Agent punya persona/instructions di AgentConfig TaskGlory (set via web/admin):
- `persona` — karakter agent (mis. "Sarah, assistant yang ramah dan precise")
- `jobdesk` — tugas utama agent
- `instructions` — aturan behavior

Hermes CLI akan baca persona ini dari system prompt + memory.

## Access Control

- Agent hanya bisa di-mention oleh owner atau superadmin
- Comment dari agent sendiri TIDAK trigger SSE event (backend filter)
- Agent tetap bisa balas jika comment/message tidak mention tapi agent adalah assignee/channel member/DM participant

## Files

| File | Fungsi |
|------|--------|
| `~/.hermes/scripts/taskglory_sse_listener.py` | Main listener script |
| `~/.hermes/scripts/sse_listener.log` | Log output (auto-created) |
| `~/.hermes/scripts/sse_processed_ids.txt` | Dedupe: processed comment/message IDs (auto-created) |
| `~/Library/LaunchAgents/com.hermes.taskglory-sse.plist` | launchd plist (macOS) |

## Pitfalls

1. **One-shot mode tidak load MCP** — `hermes -z` hanya load built-in tools. WAJIB pakai `hermes chat --cli` via PTY. Listener handle ini otomatis.
2. **Hermes path di launchd** — launchd tidak load shell profile (`.zshrc`/`.bashrc`), jadi `hermes` tidak ada di PATH. WAJIB pakai full path (mis. `/Users/awan/.local/bin/hermes`). Listener cek `HERMES_BIN` env var, fallback ke hardcoded path — edit sesuai mesin kamu.
3. **MCP connect time** — butuh ~9s (4s Hermes boot + 5s MCP register) sebelum prompt dikirim. Listener handle ini otomatis.
4. **Token 401** — pastikan pakai token dari `~/.hermes/config.yaml`. Token lama mungkin expired. Regenerate dari TaskGlory web jika perlu.
5. **Agent self-comment tidak trigger SSE** — backend filter event dari agent sendiri. Test harus pakai comment dari user lain.
6. **Dedupe** — `comment_created` + `task_mention` bisa punya `comment_id` sama. Listener skip duplicate via `sse_processed_ids.txt`.
7. **PTY required** — `hermes chat --cli` butuh TTY. Tanpa PTY, MCP tools tidak load. Listener pakai `pty.openpty()`.
8. **Python path di launchd** — homebrew python path berbeda dari system python. Cek: `which python3` di terminal, pakai path itu di plist.
9. **Event timeout** — listener max 180s per event. Jika Hermes lambat, event berikutnya menunggu. Untuk concurrency, bisa modifikasi listener untuk spawn thread per event (tapi hati-hati dengan resource).

## Verify

1. Listener running: `launchctl list | grep taskglory-sse` (macOS) atau `systemctl --user status taskglory-sse` (Linux)
2. SSE connected: `tail ~/.hermes/scripts/sse_listener.log` — harus ada "Connected. Status=200"
3. Test: minta user lain comment/mention agent di task → cek log muncul "Event received" → "Auto-reply completed"
4. Cek reply: buka task di web TaskGlory, agent harus ada reply comment

## Troubleshooting

| Masalah | Cek | Fix |
|---------|-----|-----|
| 401 Unauthorized | Token expired | Regenerate PAT, update listener + config.yaml |
| `No such file or directory: 'hermes'` | Hermes path salah | Update `HERMES_BIN` di listener atau plist |
| MCP tools not loaded | Hermes one-shot mode | Pastikan pakai `hermes chat --cli` via PTY, bukan `hermes -z` |
| No events received | SSE connection | Cek network, cek agent punya akses ke task/channel |
| Duplicate replies | Dedupe file | Cek `sse_processed_ids.txt`, hapus jika perlu re-process |
| Listener crash | launchd log | Cek `sse_listener_stderr.log`, `launchctl list` untuk exit code |