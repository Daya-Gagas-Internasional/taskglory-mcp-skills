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

### Quick setup (recommended)

Jalankan setup script — otomatis cek prerequisites, copy listener, get token dari config, generate + load service:

```bash
# Setelah install skill, run setup script
bash ~/.hermes/skills/productivity/chat-reply/scripts/setup.sh
```

Atau dari repo:

```bash
cd taskglory-skill/skills/chat-reply
bash scripts/setup.sh
```

Script auto-detect token dari `~/.hermes/config.yaml`, resolve hermes path, generate launchd/systemd service, load + verify.

### Manual setup

Kalau tidak bisa run `setup.sh`, ikut langkah berikut:

#### Langkah 1 — Dapatkan TaskGlory PAT token

PAT token di-generate oleh admin TaskGlory. Minta ke admin workspace kamu:

1. Hubungi admin TaskGlory workspace kamu
2. Minta dibuatkan PAT token untuk agent Hermes kamu
3. Admin akan memberikan token dengan format: `tgpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
4. Simpan token ini aman. Token bersifat rahasia — jangan share atau commit ke git.

#### Langkah 2 — Konfigurasi MCP taskglory di Hermes

Pastikan `~/.hermes/config.yaml` punya section `mcp_servers.taskglory` dengan token kamu:

```yaml
mcp_servers:
  taskglory:
    url: https://dev.taskglory.com/api/mcp
    headers:
      Authorization: Bearer tgpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Test koneksi:

```bash
hermes mcp test taskglory
```

Harus muncul: `✓ Connected` dan `✓ Tools discovered: 24`.

#### Langkah 3 — Copy listener script

```bash
mkdir -p ~/.hermes/scripts
cp ~/.hermes/skills/productivity/chat-reply/scripts/taskglory_sse_listener.py ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/taskglory_sse_listener.py
```

#### Langkah 4 — Cek path Hermes binary

```bash
which hermes
```

Catat full path-nya (mis. `/Users/kamu/.local/bin/hermes` atau `/home/kamu/.local/bin/hermes`).

#### Langkah 5 — Test listener

Jalankan listener dengan token kamu:

```bash
python3 ~/.hermes/scripts/taskglory_sse_listener.py "tgpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" &
```

Cek log:

```bash
tail -f ~/.hermes/scripts/sse_listener.log
```

Harus muncul:

```
[SSE] Connected. Status=200. Listening for events...
```

Kalau muncul `401 Unauthorized` — token salah atau expired. Ulangi Langkah 1.
Kalau muncul `No such file or directory: 'hermes'` — set env var:

```bash
export HERMES_BIN="/path/ke/hermes"
python3 ~/.hermes/scripts/taskglory_sse_listener.py "tgpat_xxx" &
```

Stop listener: `kill %1` atau `pkill -f taskglory_sse_listener`.

#### Langkah 6 — Setup persistent (opsional)

Agar listener auto-start saat boot + auto-restart kalau crash:

**macOS (launchd):**

Buat file `~/Library/LaunchAgents/com.hermes.taskglory-sse.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hermes.taskglory-sse</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/ke/python3</string>
        <string>/Users/KAMU/.hermes/scripts/taskglory_sse_listener.py</string>
        <string>tgpat_TOKEN_KAMU</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HERMES_BIN</key>
        <string>/Users/KAMU/.local/bin/hermes</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/KAMU/.hermes/scripts/sse_listener_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/KAMU/.hermes/scripts/sse_listener_stderr.log</string>
    <key>WorkingDirectory</key>
    <string>/Users/KAMU/.hermes/scripts</string>
</dict>
</plist>
```

Ganti:
- `/path/ke/python3` → output `which python3`
- `/Users/KAMU` → home directory kamu
- `tgpat_TOKEN_KAMU` → token dari Langkah 1
- `/Users/KAMU/.local/bin/hermes` → output `which hermes`

Load:

```bash
launchctl load ~/Library/LaunchAgents/com.hermes.taskglory-sse.plist
```

Cek:

```bash
launchctl list | grep taskglory-sse
```

Stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.hermes.taskglory-sse.plist
```

**Linux (systemd):**

Buat file `~/.config/systemd/user/taskglory-sse.service`:

```ini
[Unit]
Description=TaskGlory SSE Auto-Reply Listener
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 %h/.hermes/scripts/taskglory_sse_listener.py tgpat_TOKEN_KAMU
Restart=always
RestartSec=3
Environment=HERMES_BIN=%h/.local/bin/hermes

[Install]
WantedBy=default.target
```

Ganti `tgpat_TOKEN_KAMU` dan `HERMES_BIN` path.

Enable:

```bash
systemctl --user daemon-reload
systemctl --user enable --now taskglory-sse
```

Cek:

```bash
systemctl --user status taskglory-sse
```

Stop:

```bash
systemctl --user stop taskglory-sse
```

#### Langkah 7 — Test auto-reply

1. Buka TaskGlory web
2. Minta user lain (bukan agent sendiri) comment atau mention agent di sebuah task
3. Cek log: `tail ~/.hermes/scripts/sse_listener.log`
4. Harus muncul: `Event received` → `Auto-reply completed`
5. Cek task di web — agent harus ada reply comment

Catatan: comment dari agent sendiri tidak trigger SSE event (backend filter). Test wajib pakai user lain.

### Penting

- `hermes -z` (one-shot) TIDAK load MCP tools. Listener pakai `hermes chat --cli` via PTY.
- launchd tidak load shell PATH — set `HERMES_BIN` full path di listener atau plist.
- Agent self-comment tidak trigger SSE (backend filter). Test pakai user lain.