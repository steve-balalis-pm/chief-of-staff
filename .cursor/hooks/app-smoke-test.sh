#!/bin/bash
# Chief of Staff Hub — post-edit smoke test hook
#
# Fires after the agent edits a file. If the edited file is inside the app/
# directory AND the dev server is already running on port 8001, runs the smoke
# test and returns the results as additional_context for the agent.
#
# Skips silently when:
#   - the edited file is not an app source file (.py / .html / .css)
#   - the dev server is not running (we never auto-start it here)

set -euo pipefail

# ---------- read hook input ----------
input=$(cat)

# Extract the file path from the Write tool input
file_path=$(echo "$input" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    # afterFileEdit wraps the tool call; path lives in tool_input.path
    path = (d.get('tool_input') or d).get('path', '')
    print(path)
except Exception:
    print('')
" 2>/dev/null || true)

# ---------- filter: only care about app source files ----------
if [[ "$file_path" != *"/chief_of_staff/app/"* ]]; then
    exit 0
fi

# Only .py, .html, .css files are worth testing
if [[ "$file_path" != *.py && "$file_path" != *.html && "$file_path" != *.css ]]; then
    exit 0
fi

# ---------- filter: only run if server is already up ----------
if ! lsof -ti :8001 > /dev/null 2>&1; then
    # Server not running — skip silently
    exit 0
fi

# ---------- run the smoke test ----------
SMOKE_SCRIPT="$HOME/.cursor/skills/app-dev-check/scripts/smoke_test.py"

if [[ ! -f "$SMOKE_SCRIPT" ]]; then
    exit 0
fi

# Find a python3 — prefer the venv if the project root is resolvable
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python3"

if [[ -x "$VENV_PYTHON" ]]; then
    PYTHON="$VENV_PYTHON"
else
    PYTHON="python3"
fi

result=$("$PYTHON" "$SMOKE_SCRIPT" 2>&1 || true)

# ---------- return additional_context to the agent ----------
python3 -c "
import json, sys
result = sys.argv[1]
file  = sys.argv[2]
import os
short = os.path.basename(file)
output = {
    'additional_context': (
        f'[Auto smoke test after editing {short}]\n'
        + result
        + '\nIf any routes failed, investigate before marking the task complete.'
    )
}
print(json.dumps(output))
" "$result" "$file_path"
