#!/usr/bin/env bash
# Delta SkillPack SessionStart Hook
# Checks for active PRD and injects context

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"

# Find the repo root (where .skillpack would be)
REPO_ROOT="${PWD}"

# Check for active PRD
PRD_FILE="${REPO_ROOT}/.skillpack/ralph/prd.json"

if [[ -f "$PRD_FILE" ]]; then
    # Read PRD status
    if command -v jq &> /dev/null; then
        PRD_ID=$(jq -r '.id // "unknown"' "$PRD_FILE" 2>/dev/null || echo "unknown")
        PRD_TITLE=$(jq -r '.title // "Unknown"' "$PRD_FILE" 2>/dev/null || echo "Unknown")
        TOTAL_STORIES=$(jq '.stories | length' "$PRD_FILE" 2>/dev/null || echo "0")
        PASSED_STORIES=$(jq '[.stories[] | select(.passes == true)] | length' "$PRD_FILE" 2>/dev/null || echo "0")
        IS_COMPLETE=$(jq 'all(.stories[]; .passes == true)' "$PRD_FILE" 2>/dev/null || echo "false")

        if [[ "$IS_COMPLETE" == "true" ]]; then
            STATUS="✅ Complete"
        else
            STATUS="🔄 In Progress ($PASSED_STORIES/$TOTAL_STORIES stories)"
        fi

        # Output context for Claude
        CONTEXT="## Active Ralph PRD

| Field | Value |
|-------|-------|
| PRD ID | $PRD_ID |
| Title | $PRD_TITLE |
| Status | $STATUS |
| Stories | $PASSED_STORIES/$TOTAL_STORIES passed |

Use \`skill ralph status\` for details, or \`/ralph-loop\` to continue."

        # Output as JSON for Claude Code hooks system
        cat << EOF
{
  "assistant": "$CONTEXT"
}
EOF
    else
        # jq not available, simple message
        cat << EOF
{
  "assistant": "Active PRD found at $PRD_FILE. Use \`skill ralph status\` to check progress."
}
EOF
    fi
else
    # No active PRD
    exit 0
fi
