#!/bin/bash
# Chief of Staff Hub — session start context hook
#
# Fires at sessionStart. Injects the current Eastern date/time, checks whether
# the Chief of Staff Hub is live on port 8001, and instructs the agent to verify
# Atlassian MCP authentication before any Jira work begins.

set -euo pipefail

# Current date/time in Eastern time (handles EST/EDT automatically)
EASTERN_DT=$(TZ="America/New_York" date "+%A, %B %-d, %Y at %-I:%M %p %Z")

# Check if the app is responding on port 8001
if curl -sf --max-time 3 http://localhost:8001/ > /dev/null 2>&1; then
    APP_STATUS="running"
else
    APP_STATUS="not running"
fi

python3 - "$EASTERN_DT" "$APP_STATUS" <<'PYEOF'
import json, sys

eastern_dt = sys.argv[1]
app_status = sys.argv[2]

if app_status == "running":
    app_line = "**Chief of Staff Hub (port 8001):** Running\n"
else:
    app_line = (
        "**Chief of Staff Hub (port 8001):** NOT RUNNING — "
        "start it with `cd /Users/Steven.Balalis/Desktop/just_code\\(current\\)/chief_of_staff "
        "&& .venv/bin/uvicorn app.main:app --reload --port 8001` before using the hub.\n"
    )

output = {
    "additional_context": (
        "## Chief of Staff Hub — Session Context\n\n"
        f"**Current date/time (Eastern):** {eastern_dt}\n"
        + app_line + "\n"
        "**Required startup actions (run these now, before anything else):**\n"
        "1. Call the `atlassianUserInfo` Atlassian MCP tool to verify Jira/Confluence "
        "authentication is active. If it returns an auth error or prompts for login, "
        "complete the auth flow before proceeding with any Jira-related tasks.\n"
        "2. If the hub is not running (see above), offer to start it.\n"
        "3. Use the Eastern date/time above as today's date for any briefings, "
        "ticket hygiene checks, standup prep, or time-sensitive tasks in this session."
    )
}
print(json.dumps(output))
PYEOF
