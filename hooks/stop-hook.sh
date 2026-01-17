#!/usr/bin/env bash
# Delta SkillPack Stop Hook
# Implements Ralph Wiggum-style automatic iteration
#
# This hook intercepts Claude session exit and checks:
# 1. If Ralph loop is active
# 2. If PRD is not yet complete
# 3. If completion signal not detected
#
# If all conditions met, blocks exit and continues iteration.

set -euo pipefail

# Get paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${PWD}"

# Ralph state files
PRD_FILE="${REPO_ROOT}/.skillpack/ralph/prd.json"
SESSION_FILE="${REPO_ROOT}/.skillpack/ralph/session.json"
RALPH_ACTIVE_FILE="${REPO_ROOT}/.skillpack/ralph/.ralph_active"
COMPLETE_MARKER_FILE="${REPO_ROOT}/.skillpack/ralph/.complete"
TRANSCRIPT_FILE="${HOME}/.claude/transcript.json"

check_completion_signals() {
    COMPLETION_COUNT=0
    COMPLETION_SIGNAL_LIST=()

    # Signal 1: <promise>COMPLETE</promise> in transcript
    if [[ -f "$TRANSCRIPT_FILE" ]] && command -v jq &> /dev/null; then
        LAST_OUTPUT=$(jq -r '.messages[-1].content // ""' "$TRANSCRIPT_FILE" 2>/dev/null || true)
        if [[ "$LAST_OUTPUT" == *"<promise>COMPLETE</promise>"* ]]; then
            COMPLETION_COUNT=$((COMPLETION_COUNT + 1))
            COMPLETION_SIGNAL_LIST+=("promise")
        fi
    fi

    # Signal 2: PRD all stories completed
    if [[ -f "$PRD_FILE" ]] && command -v jq &> /dev/null; then
        IS_COMPLETE=$(jq 'all(.stories[]; .passes == true)' "$PRD_FILE" 2>/dev/null || echo "false")
        if [[ "$IS_COMPLETE" == "true" ]]; then
            COMPLETION_COUNT=$((COMPLETION_COUNT + 1))
            COMPLETION_SIGNAL_LIST+=("prd")
        fi
    fi

    # Signal 3: Completion marker file
    if [[ -f "$COMPLETE_MARKER_FILE" ]]; then
        COMPLETION_COUNT=$((COMPLETION_COUNT + 1))
        COMPLETION_SIGNAL_LIST+=("marker")
    fi
}

# Check if Ralph loop is active
if [[ ! -f "$RALPH_ACTIVE_FILE" ]]; then
    # Ralph not active, allow normal exit
    exit 0
fi

# Check completion signals (require at least 2)
check_completion_signals
if [[ "$COMPLETION_COUNT" -ge 2 ]]; then
    SIGNAL_SUMMARY=$(IFS=,; echo "${COMPLETION_SIGNAL_LIST[*]}")
    rm -f "$RALPH_ACTIVE_FILE"
    echo "✅ Ralph loop completed successfully! Signals: ${SIGNAL_SUMMARY}" >&2
    exit 0
fi

# Read iteration count
ITERATION=1
if [[ -f "$SESSION_FILE" ]] && command -v jq &> /dev/null; then
    ITERATION=$(jq -r '.current_iteration // 1' "$SESSION_FILE" 2>/dev/null || echo "1")
fi

# Check max iterations (default 100)
MAX_ITERATIONS=100
if [[ -f "$PRD_FILE" ]] && command -v jq &> /dev/null; then
    MAX_ITERATIONS=$(jq -r '.max_iterations // 100' "$PRD_FILE" 2>/dev/null || echo "100")
fi

if [[ "$ITERATION" -ge "$MAX_ITERATIONS" ]]; then
    # Max iterations reached, clean up and allow exit
    rm -f "$RALPH_ACTIVE_FILE"
    echo "⚠️ Ralph loop reached max iterations ($MAX_ITERATIONS)" >&2
    exit 0
fi

# Increment iteration
NEXT_ITERATION=$((ITERATION + 1))

# Update session file
if [[ -f "$SESSION_FILE" ]] && command -v jq &> /dev/null; then
    jq --argjson iter "$NEXT_ITERATION" '.current_iteration = $iter' "$SESSION_FILE" > "${SESSION_FILE}.tmp"
    mv "${SESSION_FILE}.tmp" "$SESSION_FILE"
fi

# Get PRD info for context
PRD_TITLE="Unknown"
PASSED_STORIES=0
TOTAL_STORIES=0
if [[ -f "$PRD_FILE" ]] && command -v jq &> /dev/null; then
    PRD_TITLE=$(jq -r '.title // "Unknown"' "$PRD_FILE" 2>/dev/null || echo "Unknown")
    TOTAL_STORIES=$(jq '.stories | length' "$PRD_FILE" 2>/dev/null || echo "0")
    PASSED_STORIES=$(jq '[.stories[] | select(.passes == true)] | length' "$PRD_FILE" 2>/dev/null || echo "0")
fi

# Block exit and continue iteration
SYSTEM_MSG="Ralph iteration $NEXT_ITERATION/$MAX_ITERATIONS. Progress: $PASSED_STORIES/$TOTAL_STORIES stories. Continue executing the next story."

PROMPT="Continue Ralph loop for: $PRD_TITLE

Current progress: $PASSED_STORIES/$TOTAL_STORIES stories completed.

Execute the next pending story using:
1. \`skill ralph next-story\` to get the next story
2. \`skill ralph execute-pipeline --story-id <id>\` to run it
3. Check results and commit if successful

When all stories pass, output: <promise>COMPLETE</promise>"

# Output JSON to block exit and inject prompt
cat << EOF
{
  "decision": "block",
  "reason": "$PROMPT",
  "systemMessage": "$SYSTEM_MSG"
}
EOF
