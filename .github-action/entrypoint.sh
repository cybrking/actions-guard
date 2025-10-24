#!/bin/bash
set -e

# Parse inputs
GITHUB_TOKEN="${INPUT_GITHUB_TOKEN}"
ORG_NAME="${INPUT_ORG_NAME}"
REPO_NAME="${INPUT_REPO_NAME}"
EXCLUDE_REPOS="${INPUT_EXCLUDE_REPOS}"
ONLY_REPOS="${INPUT_ONLY_REPOS}"
CHECKS="${INPUT_CHECKS}"
ALL_CHECKS="${INPUT_ALL_CHECKS}"
OUTPUT_FORMAT="${INPUT_OUTPUT_FORMAT}"
FAIL_ON_CRITICAL="${INPUT_FAIL_ON_CRITICAL}"
OUTPUT_DIR="${INPUT_OUTPUT_DIR:-reports}"

# Export GitHub token
export GITHUB_TOKEN

# Build actionsguard command
CMD="actionsguard scan"

# Add repo or org
if [ -n "$REPO_NAME" ]; then
    CMD="$CMD --repo $REPO_NAME"
elif [ -n "$ORG_NAME" ]; then
    CMD="$CMD --org $ORG_NAME"
else
    # Default to current repository
    if [ -n "$GITHUB_REPOSITORY" ]; then
        CMD="$CMD --repo $GITHUB_REPOSITORY"
    else
        echo "Error: Must specify either repo-name, org-name, or run in GitHub Actions"
        exit 1
    fi
fi

# Add optional parameters
[ -n "$EXCLUDE_REPOS" ] && CMD="$CMD --exclude $EXCLUDE_REPOS"
[ -n "$ONLY_REPOS" ] && CMD="$CMD --only $ONLY_REPOS"
[ -n "$CHECKS" ] && [ "$ALL_CHECKS" != "true" ] && CMD="$CMD --checks $CHECKS"
[ "$ALL_CHECKS" = "true" ] && CMD="$CMD --all-checks"
[ -n "$OUTPUT_FORMAT" ] && CMD="$CMD --format $OUTPUT_FORMAT"
[ "$FAIL_ON_CRITICAL" = "true" ] && CMD="$CMD --fail-on-critical"
CMD="$CMD --output $OUTPUT_DIR"

# Run scan
echo "Running: $CMD"
eval $CMD

# Set outputs
REPORTS_PATH="$OUTPUT_DIR"
echo "reports-path=$REPORTS_PATH" >> "$GITHUB_OUTPUT"

# Parse results from JSON report
if [ -f "$OUTPUT_DIR/report.json" ]; then
    CRITICAL_COUNT=$(jq '.critical_count' "$OUTPUT_DIR/report.json")
    OVERALL_SCORE=$(jq '.average_score' "$OUTPUT_DIR/report.json")
    SUMMARY=$(jq -c '.' "$OUTPUT_DIR/report.json")

    echo "critical-count=$CRITICAL_COUNT" >> "$GITHUB_OUTPUT"
    echo "overall-score=$OVERALL_SCORE" >> "$GITHUB_OUTPUT"
    echo "summary=$SUMMARY" >> "$GITHUB_OUTPUT"

    # Write to job summary
    if [ -f "$OUTPUT_DIR/report.md" ]; then
        cat "$OUTPUT_DIR/report.md" >> "$GITHUB_STEP_SUMMARY"
    fi
fi

echo "ActionsGuard scan complete!"
