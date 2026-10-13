---
name: chat-reply
description: Auto-reply comment, chat & thread di TaskGlory. SSE listener → Hermes CLI → MCP tools. Real-time, tanpa queue/cron.
version: 2.1.0
author: awan
---

# Chat Reply — Real-time Auto-Reply via SSE + Hermes CLI

Auto-reply comment, channel message, dan DM berdasarkan SSE events dari TaskGlory. Real-time: saat event masuk, listener langsung spawn Hermes → MCP tools → reply terkirim.

## Arsitektur (v2.1)

```
User comment/message/mention
    ↓
TaskGlory backend → Redis pub/sub
    ↓
SSE stream (/api/mcp/sse)
    ↓
Python listener (taskglory_sse_listener.py) — bg process / launchd
    ↓
Jalankan `hermes chat -Q --oneshot --query-file <tmp>` (MCP tools loaded)
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

### Quick setup (recommended)

Jalankan setup script — otomatis cek prerequisites, copy listener, get token dari config, generate + load launchd/systemd service:

```bash
bash scripts/setup.sh
```

Script akan:
1. Cek python3, hermes binary, MCP taskglory connection
2. Copy `taskglory_sse_listener.py` ke `~/.hermes/scripts/`
3. Ambil token dari `~/.hermes/config.yaml` (auto-detect)
4. Resolve hermes path (auto-detect, atau set `HERMES_BIN` env var)
5. Generate launchd plist (macOS) atau systemd service (Linux) dengan token + path benar
6. Load service + verify SSE connected

### Manual setup

Jika prefer manual, ikut step-by-step:

Copy `taskglory_sse_listener.py` (dari `scripts/` folder skill ini) ke `~/.hermes/scripts/`:

```bash
mkdir -p ~/.hermes/scripts
cp scripts/taskglory_sse_listener.py ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/taskglory_sse_listener.py
```

### 2. Hermes path (biasanya otomatis)

Listener auto-resolve urutan: `HERMES_BIN` env var → `shutil.which("hermes")` → `~/.local/bin/hermes`.
Override hanya jika hermes ada di lokasi non-standar:

```bash
export HERMES_BIN=/path/to/hermes
```

Untuk launchd/systemd, set lewat service file (setup.sh sudah handle).

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
3. Listener tulis prompt ke temp file, jalankan `hermes chat -Q --oneshot --query-file <tmp>`
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
| `scripts/taskglory_sse_listener.py` | Main listener script (generic, auto-detect hermes path) |
| `scripts/setup.sh` | Setup script — auto-detect token, copy listener, generate + load service |
| `~/.hermes/scripts/taskglory_sse_listener.py` | Installed listener (copy dari scripts/) |
| `~/.hermes/scripts/sse_listener.log` | Log output (auto-created) |
| `~/.hermes/scripts/sse_processed_ids.txt` | Dedupe: processed comment/message IDs (auto-created) |
| `~/Library/LaunchAgents/com.hermes.taskglory-sse.plist` | launchd plist (macOS, auto-generated by setup.sh) |
| `~/.config/systemd/user/taskglory-sse.service` | systemd service (Linux, auto-generated by setup.sh) |

## Pitfalls

1. **JANGAN pakai PTY + paste prompt ke TUI** — mengirim prompt multi-line ke PTY `hermes chat --cli` membuat TUI mendeteksinya sebagai PASTE (log: `Collapsed paste #N: 16 lines`); newline masuk ke buffer dan prompt TIDAK pernah ter-submit. Agent idle sampai SIGKILL (`exit=-9`), `Output tail` cuma echo prompt, dan `agent.log` tidak punya satu pun `API call #1`/`turn_context` untuk sesi itu. Menaikkan timeout tidak menolong. Pakai `-Q --oneshot --query-file <tmpfile>` (non-interaktif) — MCP tools tetap load penuh. Ini BEDA dari `hermes -z` yang memang hanya built-in tools.
2. **Hermes path di launchd** — launchd tidak load shell profile (`.zshrc`/`.bashrc`), jadi `hermes` tidak ada di PATH. WAJIB pakai full path (mis. `/Users/awan/.local/bin/hermes`). Listener cek `HERMES_BIN` env var, fallback ke hardcoded path — edit sesuai mesin kamu.
3. **`--query-file` untuk teks arbitrer** — jangan interpolasi konten komentar ke argv/shell: quote, backtick, dan `$(...)` bisa ter-interpret. Temp file menghindari semua itu sekaligus batas panjang argumen.
4. **Token 401** — pastikan pakai token dari `~/.hermes/config.yaml`. Token lama mungkin expired. Regenerate dari TaskGlory web jika perlu.
5. **Agent self-comment tidak trigger SSE** — backend filter event dari agent sendiri. Test harus pakai comment dari user lain.
6. **Dedupe** — `comment_created` + `task_mention` bisa punya `comment_id` sama. Listener skip duplicate via `sse_processed_ids.txt`.
7. **Jangan percaya log listener sebagai bukti reply terkirim** — baris `[SSE] Auto-reply completed` hanya menandai handler selesai. Ground truth cuma `task_comments(task_id=...)` → harus ada komentar `is_agent: true`. Indikasi benar di log: `exit=0` + output tail berisi comment id.
8. **Python path di launchd** — homebrew python path berbeda dari system python. Cek: `which python3` di terminal, pakai path itu di plist.
9. **Event timeout** — listener max 480s per event (override: `TG_REPLY_TIMEOUT` env var). Jika Hermes lambat, event berikutnya menunggu. Untuk concurrency, bisa modifikasi listener untuk spawn thread per event (tapi hati-hati dengan resource).

## Verify

1. Listener running: `launchctl list | grep taskglory-sse` (macOS) atau `systemctl --user status taskglory-sse` (Linux)
2. SSE connected: `tail ~/.hermes/scripts/sse_listener.log` — harus ada "Connected. Status=200"
3. Test: minta user lain comment/mention agent di task → cek log muncul "Event received" → `exit=0`
4. Cek reply (WAJIB, jangan skip): `task_comments(task_id=...)` via MCP, atau buka task di web TaskGlory — harus ada komentar dari agent

Test tanpa menunggu event baru — replay event lewat import langsung:
```bash
cd ~/.hermes/scripts && python3 -c "
import sys; sys.argv=['x','dummy']
import importlib.util
spec = importlib.util.spec_from_file_location('l','taskglory_sse_listener.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
p = m.build_prompt('comment_created', {'task_id':'...','task_code':'...','comment_id':'...','author_name':'...','content_preview':'...'})
m.trigger_hermes(p)"
```
Reply normal selesai ~25s dengan `exit=0`.

## Troubleshooting

| Masalah | Cek | Fix |
|---------|-----|-----|
| 401 Unauthorized | Token expired | Regenerate PAT, update listener + config.yaml |
| `No such file or directory: 'hermes'` | Hermes path salah | Update `HERMES_BIN` di listener atau plist |
| MCP tools not loaded | Mode `hermes -z` | Pakai `chat -Q --oneshot --query-file`, bukan `hermes -z` |
| `exit=-9`, output tail cuma echo prompt | Prompt ter-paste ke TUI, tidak ter-submit | Jangan pakai PTY `chat --cli`; pakai `--query-file` (Pitfall #1) |
| Log bilang "completed" tapi reply tidak ada | Salah baca log | Verifikasi via `task_comments`, cek `is_agent: true` |
| Token dev 401 di prod | PAT environment-specific | Generate PAT baru di host target; update config.yaml + plist/service |
| No events received | SSE connection | Cek network, cek agent punya akses ke task/channel |
| Duplicate replies | Dedupe file | Cek `sse_processed_ids.txt`, hapus jika perlu re-process |
| Listener crash | launchd log | Cek `sse_listener_stderr.log`, `launchctl list` untuk exit code |