#!/bin/bash
# ralph-loop.sh - Industrial Automation Development Loop
# Each iteration starts a new AI process for complete context refresh

set -e

REPO_DIR="${1:-.}"
MAX_ITERATIONS="${2:-100}"
SKILLPACK_DIR="$REPO_DIR/.skillpack/ralph"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo -e "  ${BLUE}Ralph Industrial Automation Development Loop${NC}"
echo "════════════════════════════════════════════════════════════════════"
echo "  Repository:      $REPO_DIR"
echo "  Max Iterations:  $MAX_ITERATIONS"
echo "  Data Directory:  $SKILLPACK_DIR"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Ensure skillpack ralph directory exists
mkdir -p "$SKILLPACK_DIR"

# Check if PRD exists
if [ ! -f "$SKILLPACK_DIR/prd.json" ]; then
    echo -e "${RED}Error: No PRD found at $SKILLPACK_DIR/prd.json${NC}"
    echo "Run 'skill ralph init \"your task\"' first to generate a PRD."
    exit 1
fi

iteration=0
while [ $iteration -lt $MAX_ITERATIONS ]; do
    iteration=$((iteration + 1))
    echo ""
    echo -e "${BLUE}═══ Iteration $iteration ═══${NC}"
    echo ""

    # 1. Get next story from PRD
    next_story=$(skill ralph next-story --json 2>/dev/null || echo "null")

    if [ "$next_story" = "null" ] || [ -z "$next_story" ]; then
        # Check if all stories are complete
        completion=$(skill ralph status --json 2>/dev/null | jq -r '.completion_rate // 0')
        if [ "$completion" = "1" ]; then
            echo ""
            echo "════════════════════════════════════════════════════════════════════"
            echo -e "  ${GREEN}All Stories Complete!${NC}"
            echo "════════════════════════════════════════════════════════════════════"
            echo ""
            echo "<promise>COMPLETE</promise>"
            exit 0
        else
            echo -e "${YELLOW}No eligible stories to execute. Waiting...${NC}"
            sleep 5
            continue
        fi
    fi

    story_id=$(echo "$next_story" | jq -r '.id')
    story_title=$(echo "$next_story" | jq -r '.title')
    story_type=$(echo "$next_story" | jq -r '.type')

    echo -e "Story:  ${GREEN}$story_id${NC} - $story_title"
    echo -e "Type:   ${YELLOW}$story_type${NC}"
    echo ""

    # 2. Execute story pipeline based on type (new process = clean context)
    case $story_type in
        "feature"|"refactor")
            # plan → implement → review → verify
            echo "Pipeline: plan → implement → review → verify"
            skill ralph execute-pipeline \
                --story-id "$story_id" \
                --steps "plan,implement,review,verify"
            ;;
        "ui")
            # ui → implement → review → browser
            echo "Pipeline: ui → implement → review → browser"
            skill ralph execute-pipeline \
                --story-id "$story_id" \
                --steps "ui,implement,review,browser"
            ;;
        "test")
            # implement → review → verify
            echo "Pipeline: implement → review → verify"
            skill ralph execute-pipeline \
                --story-id "$story_id" \
                --steps "implement,review,verify"
            ;;
        "docs")
            # plan → implement → review
            echo "Pipeline: plan → implement → review"
            skill ralph execute-pipeline \
                --story-id "$story_id" \
                --steps "plan,implement,review"
            ;;
        *)
            echo -e "${RED}Unknown story type: $story_type${NC}"
            skill ralph mark-failed --story-id "$story_id" --error "Unknown story type"
            continue
            ;;
    esac

    # 3. Check execution result
    status=$(skill ralph story-status --story-id "$story_id" --json 2>/dev/null | jq -r '.passes // false')

    if [ "$status" = "true" ]; then
        echo ""
        echo -e "${GREEN}✅ Story $story_id completed successfully${NC}"

        # Commit changes
        if git diff --quiet && git diff --staged --quiet; then
            echo "No changes to commit."
        else
            git add -A
            git commit -m "feat($story_id): $story_title" --no-verify 2>/dev/null || true
            echo "Changes committed."
        fi
    else
        echo ""
        echo -e "${RED}❌ Story $story_id failed, will retry in next iteration${NC}"
    fi

    # 4. Brief pause to avoid API rate limiting
    echo ""
    echo "Waiting 2 seconds before next iteration..."
    sleep 2
done

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo -e "  ${YELLOW}Max iterations ($MAX_ITERATIONS) reached${NC}"
echo "  PRD not fully complete"
echo "════════════════════════════════════════════════════════════════════"
exit 1
