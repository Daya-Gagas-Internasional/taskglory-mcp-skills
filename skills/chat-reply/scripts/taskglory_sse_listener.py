#!/usr/bin/env python3
"""TaskGlory SSE Listener — real-time auto-reply via Hermes CLI (PTY mode).

SSE event masuk → spawn `hermes chat --cli` via PTY → Hermes proses dengan MCP tools → auto-reply ke TaskGlory.
Tanpa queue file, tanpa cron. Real-time.

Usage:
    python3 taskglory_sse_listener.py <tgpat_token>

Environment variables:
    HERMES_BIN    — full path to hermes binary (default: tries `which hermes`, then ~/.local/bin/hermes)
    TG_BASE_URL   — TaskGlory base URL (default: https://dev.taskglory.com)

Requires:
    - Hermes Agent installed, MCP taskglory configured & enabled
    - Python 3.10+ (uses pty, select, fcntl — Unix only)

Setup:
    1. Get token: grep -o 'tgpat_[a-f0-9]*' ~/.hermes/config.yaml
    2. Get hermes path: which hermes
    3. Run: python3 taskglory_sse_listener.py "tgpat_xxx"
    4. For persistent: setup launchd (macOS) or systemd (Linux) — see SKILL.md
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import pty
import select
import fcntl
from datetime import datetime, timezone

BASE_URL = os.environ.get("TG_BASE_URL", "https://dev.taskglory.com")
SSE_URL = f"{BASE_URL}/api/mcp/sse"

TOKEN = sys.argv[1] if len(sys.argv) > 1 else None

if not TOKEN:
    print("ERROR: No token provided. Usage: python3 taskglory_sse_listener.py <token>", flush=True)
    sys.exit(1)

# Resolve hermes binary path
HERMES_BIN = os.environ.get("HERMES_BIN")
if not HERMES_BIN:
    HERMES_BIN = shutil.which("hermes") or os.path.expanduser("~/.local/bin/hermes")

if not os.path.isfile(HERMES_BIN):
    print(f"ERROR: hermes binary not found at {HERMES_BIN}. Set HERMES_BIN env var.", flush=True)
    sys.exit(1)

HERMES_BIN = str(HERMES_BIN)

LOG_FILE = os.path.expanduser("~/.hermes/scripts/sse_listener.log")
PROCESSED_FILE = os.path.expanduser("~/.hermes/scripts/sse_processed_ids.txt")

# Ensure scripts dir exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Load processed IDs to avoid duplicates
processed_ids = set()
if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE) as f:
        processed_ids = set(line.strip() for line in f if line.strip())


def log(msg):
    """Log to stdout + file."""
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def mark_processed(event_key):
    """Mark event as processed."""
    if event_key:
        processed_ids.add(event_key)
        with open(PROCESSED_FILE, "a") as f:
            f.write(event_key + "\n")


def build_prompt(event_type, data):
    """Build prompt for Hermes CLI based on SSE event."""
    if event_type in ("comment_created", "task_mention"):
        task_id = data.get("task_id", "")
        task_code = data.get("task_code", "")
        comment_id = data.get("comment_id", "")
        author = data.get("author_name", "Unknown")
        preview = data.get("content_preview", "")
        return (
            f"SSE event: {event_type}\n"
            f"Task: {task_code} (id: {task_id})\n"
            f"Author: {author}\n"
            f"Comment preview: {preview}\n"
            f"Comment ID: {comment_id}\n\n"
            f"Instruksi:\n"
            f"1. Baca task detail via mcp__taskglory__task_get(task_id=\"{task_id}\")\n"
            f"2. Baca comments via mcp__taskglory__task_comments(task_id=\"{task_id}\")\n"
            f"3. Pahami konteks task + comment author\n"
            f"4. Generate reply yang relevan dan helpful\n"
            f"5. Kirim reply via mcp__taskglory__task_comment_add(task_id=\"{task_id}\", body=\"...\", mentions=[])\n"
            f"6. Reply harus concise, professional, dalam Bahasa Indonesia\n"
            f"7. Setelah reply terkirim, selesai. Jangan lakukan hal lain.\n"
        )

    elif event_type in ("channel_message", "mentioned"):
        channel_id = data.get("channel_id", "")
        channel_name = data.get("channel_name", "")
        msg_id = data.get("message_id", "")
        author = data.get("author_name", "Unknown")
        preview = data.get("content_preview", "")
        return (
            f"SSE event: {event_type}\n"
            f"Channel: {channel_name} (id: {channel_id})\n"
            f"Author: {author}\n"
            f"Message preview: {preview}\n"
            f"Message ID: {msg_id}\n\n"
            f"Instruksi:\n"
            f"1. Baca channel messages via mcp__taskglory__channel_messages(channel_id=\"{channel_id}\")\n"
            f"2. Pahami konteks percakapan\n"
            f"3. Generate reply yang relevan\n"
            f"4. Kirim reply via mcp__taskglory__channel_send(channel_id=\"{channel_id}\", content=\"...\", parent_id=\"{msg_id}\")\n"
            f"5. Reply concise, professional, Bahasa Indonesia\n"
            f"6. Setelah reply terkirim, selesai.\n"
        )

    elif event_type == "direct_message":
        conv_id = data.get("conversation_id", "")
        msg_id = data.get("message_id", "")
        sender = data.get("sender_name", "Unknown")
        preview = data.get("content_preview", "")
        return (
            f"SSE event: direct_message\n"
            f"Conversation ID: {conv_id}\n"
            f"Sender: {sender}\n"
            f"Message preview: {preview}\n"
            f"Message ID: {msg_id}\n\n"
            f"Instruksi:\n"
            f"1. Baca DM history via mcp__taskglory__dm_list() untuk context\n"
            f"2. Pahami pesan sender\n"
            f"3. Generate reply yang relevan\n"
            f"4. Kirim reply via mcp__taskglory__dm_send(conversation_id=\"{conv_id}\", content=\"...\")\n"
            f"5. Reply concise, professional, Bahasa Indonesia\n"
            f"6. Setelah reply terkirim, selesai.\n"
        )

    elif event_type == "task_assigned":
        task_id = data.get("task_id", "")
        task_title = data.get("task_title", "")
        return (
            f"SSE event: task_assigned\n"
            f"Task: {task_title} (id: {task_id})\n\n"
            f"Instruksi:\n"
            f"1. Baca task detail via mcp__taskglory__task_get(task_id=\"{task_id}\")\n"
            f"2. Post comment acknowledging assignment via mcp__taskglory__task_comment_add\n"
            f"3. Comment: acknowledge + summary task + next steps\n"
            f"4. Bahasa Indonesia, concise\n"
            f"5. Selesai setelah comment terkirim.\n"
        )

    return None


def trigger_hermes(prompt):
    """Spawn hermes chat --cli via PTY, send prompt, wait for completion."""
    log(f"[HERMES] Spawning {HERMES_BIN} chat --cli for auto-reply...")

    try:
        # Create PTY
        master_fd, slave_fd = pty.openpty()

        # Set non-blocking on master
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        proc = subprocess.Popen(
            [HERMES_BIN, "chat", "--cli", "-Q", "--yolo", "--max-turns", "20"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )

        os.close(slave_fd)

        # Phase 1: Wait for Hermes ready signal (Welcome text or prompt box)
        start = time.time()
        ready = False
        boot_output = b""

        while time.time() - start < 30:
            try:
                r, _, _ = select.select([master_fd], [], [], 1.0)
                if r:
                    try:
                        chunk = os.read(master_fd, 4096)
                        if chunk:
                            boot_output += chunk
                            decoded = chunk.decode("utf-8", errors="replace")
                            if "Welcome" in decoded or "❯" in decoded:
                                ready = True
                                break
                        else:
                            break
                    except OSError:
                        break
            except (OSError, select.error):
                break

        if not ready:
            log(f"[HERMES] Ready signal not found after {time.time()-start:.1f}s, sending anyway...")
        else:
            log(f"[HERMES] Ready at {time.time()-start:.1f}s, waiting for MCP...")

        # Extra wait for MCP tools to fully register
        time.sleep(5)

        # Phase 2: Send prompt
        prompt_bytes = (prompt + "\n").encode("utf-8")
        os.write(master_fd, prompt_bytes)
        log(f"[HERMES] Prompt sent ({len(prompt)} chars) at {time.time()-start:.1f}s")

        # Phase 3: Wait for response
        output = boot_output
        TIMEOUT = 180  # 3 minutes max per event

        while time.time() - start < TIMEOUT:
            try:
                ready, _, _ = select.select([master_fd], [], [], 2.0)
                if ready:
                    try:
                        chunk = os.read(master_fd, 4096)
                        if chunk:
                            output += chunk
                        else:
                            break
                    except OSError:
                        break
            except (OSError, select.error):
                break

            # Check if process ended
            if proc.poll() is not None:
                try:
                    while True:
                        chunk = os.read(master_fd, 4096)
                        if not chunk:
                            break
                        output += chunk
                except OSError:
                    pass
                break

        # Send /exit
        try:
            os.write(master_fd, b"/exit\n")
        except OSError:
            pass

        # Wait for process to end
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        os.close(master_fd)

        elapsed = time.time() - start
        output_str = output.decode("utf-8", errors="replace")
        log(f"[HERMES] Done in {elapsed:.1f}s, exit={proc.returncode}")

        # Log last 500 chars for debugging
        if output_str:
            tail = output_str[-500:] if len(output_str) > 500 else output_str
            log(f"[HERMES] Output tail: {tail}")

        return True

    except Exception as e:
        log(f"[HERMES] Error: {e}")
        return False


def handle_event(event_type, data):
    """Process SSE event: dedupe → build prompt → trigger Hermes."""
    # Dedupe
    event_key = data.get("comment_id") or data.get("message_id") or ""
    if event_key and event_key in processed_ids:
        log(f"[SSE] Skipping duplicate: {event_type} (key={event_key})")
        return

    log(f"[SSE] Event received: {event_type} (key={event_key})")
    log(f"[SSE] Data: {json.dumps(data)[:300]}")

    # Build prompt
    prompt = build_prompt(event_type, data)
    if prompt is None:
        log(f"[SSE] No handler for event type: {event_type}")
        return

    # Mark as processed (before trigger to prevent race)
    mark_processed(event_key)

    # Trigger Hermes
    success = trigger_hermes(prompt)
    if success:
        log(f"[SSE] Auto-reply completed for {event_type} (key={event_key})")
    else:
        log(f"[SSE] Auto-reply FAILED for {event_type} (key={event_key})")


def listen():
    """Listen to SSE stream, dispatch events to handler."""
    while True:
        try:
            log(f"[SSE] Connecting to {SSE_URL} ...")
            headers = {
                "Authorization": f"Bearer {TOKEN}",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            }
            req = urllib.request.Request(SSE_URL, headers=headers)
            resp = urllib.request.urlopen(req, timeout=90)
            status = resp.status
            log(f"[SSE] Connected. Status={status}. Listening for events...")

            if status != 200:
                body = resp.read().decode("utf-8", errors="replace")
                log(f"[SSE] HTTP {status}: {body[:200]}. Reconnecting in 3s...")
                resp.close()
                time.sleep(3)
                continue

            buffer = b""
            while True:
                chunk = resp.read(1)
                if not chunk:
                    log("[SSE] Connection closed by server. Reconnecting in 3s...")
                    break

                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith(b"data: "):
                        payload = line[6:].decode("utf-8", errors="replace")
                        try:
                            event = json.loads(payload)
                            etype = event.get("event", "unknown")
                            data = event.get("data", {})
                            handle_event(etype, data)
                        except json.JSONDecodeError:
                            log(f"[SSE] Raw (non-JSON): {payload[:200]}")
                    elif line.startswith(b":"):
                        pass  # keep-alive comment

        except Exception as e:
            log(f"[SSE] Error: {e}. Reconnecting in 3s...")
            time.sleep(3)


if __name__ == "__main__":
    listen()