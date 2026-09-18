#!/bin/bash
# TaskGlory MCP Skills — one-shot installer
# Usage: bash install-tg-skills.sh

set -e

REPO="Daya-Gagas-Internasional/taskglory-mcp-skills"
SKILLS=("taskglory-ops" "chat-reply" "taskglory-skill-manager")

echo "=== TaskGlory MCP Skills Installer ==="
echo ""

# Step 1: Add tap source
echo "[1/2] Adding tap source: $REPO"
hermes skills tap add "$REPO" 2>/dev/null || echo "  Tap already exists, skipping."
echo ""

# Step 2: Install all skills
echo "[2/2] Installing ${#SKILLS[@]} skills..."
for skill in "${SKILLS[@]}"; do
  echo "  - Installing $skill..."
  hermes skills install "$REPO/$skill" --yes 2>/dev/null && echo "    OK" || echo "    Already installed or failed, skipping."
done

echo ""
echo "=== Done! ==="
echo "Restart Hermes to load new skills."
echo "Verify: hermes skills list | grep taskglory"