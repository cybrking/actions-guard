# Inventory Tracking - Keep Track of All Your Repos

The inventory system keeps a running database of all your repositories, their scores, and tracks changes over time.

## Quick Start

### 1. First Scan - Build Your Inventory

```bash
export GITHUB_TOKEN="your_token_here"

# Option A: Scan your entire organization
actionsguard inventory update --org your-org-name

# Option B: Scan your personal account
actionsguard inventory update --user cybrking

# Option C: Scan any user's public repos
actionsguard inventory update --user username
```

This scans all repos and saves to `.actionsguard/inventory.json`

### 2. View Your Inventory

```bash
# List all repos with scores
actionsguard inventory list

# Show only critical repos
actionsguard inventory list --filter-risk CRITICAL

# Sort by score (worst first)
actionsguard inventory list --sort score
```

### 3. Export Reports

```bash
# Export to HTML dashboard, CSV, and JSON
actionsguard inventory export

# Open the dashboard
open inventory-export/inventory.html
```

### 4. Track Changes Over Time

```bash
# Run updates weekly (or however often you want)
actionsguard inventory update --org your-org-name
# or
actionsguard inventory update --user cybrking

# See what changed
actionsguard inventory diff
```

## What You Get

### Inventory Database (`.actionsguard/inventory.json`)

Stores for each repository:
- **Current score and risk level**
- **Score history** - every scan is saved
- **Latest check results** - detailed findings
- **Metadata** - first seen, scan count, etc.

### Beautiful CLI Output

```
📊 Updating Repository Inventory

Scanning organization: my-org

✅ Inventory updated!

  🆕 New repositories:     3
  📝 Updated repositories: 12
  ✓  Unchanged:            5

Recent Score Changes:

  📈 critical-app: 6.5 → 7.2 (+0.7)
  📉 legacy-api: 7.8 → 7.1 (-0.7)

Inventory stored in: .actionsguard/inventory.json
```

### Inventory List View

```
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━┓
┃ Repository       ┃ Score ┃ Risk    ┃ Scans┃ Last Updated ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━┩
│ org/critical-app │ 3.2/10│CRITICAL │    5 │ 2024-10-24   │
│ org/old-service  │ 5.1/10│  HIGH   │    3 │ 2024-10-23   │
│ org/main-app     │ 7.5/10│ MEDIUM  │    8 │ 2024-10-24   │
│ org/new-project  │ 9.1/10│   LOW   │    2 │ 2024-10-24   │
└──────────────────┴───────┴─────────┴──────┴──────────────┘

Summary:
  Total: 4 repos
  Average Score: 6.2/10
  🔴 Critical: 1
  🟠 High: 1
  🟡 Medium: 1
  🟢 Low: 1
```

### HTML Dashboard

```html
Repository Inventory Dashboard
Generated: 2024-10-24 14:30:00

┌──────────────┬────────────┬──────────┬──────────┐
│ Total Repos  │ Avg Score  │ Critical │ High Risk│
│     50       │    7.2     │    3     │    8     │
└──────────────┴────────────┴──────────┴──────────┘

[Sortable table with all repos, scores, risk levels...]
```

### CSV Export

Perfect for Excel or Google Sheets:
```csv
Repository,URL,Current Score,Risk Level,First Seen,Last Updated,Scan Count
org/app1,https://github.com/org/app1,7.5,MEDIUM,2024-10-01,2024-10-24,8
org/app2,https://github.com/org/app2,4.2,HIGH,2024-10-05,2024-10-24,5
...
```

## Common Use Cases

### Weekly Security Audit

```bash
#!/bin/bash
# weekly-audit.sh

export GITHUB_TOKEN="your_token"

# Update inventory
actionsguard inventory update --org my-org

# Export reports
actionsguard inventory export --output ./weekly-reports/$(date +%Y-%m-%d)

# Show changes
actionsguard inventory diff

# Email CSV to team
mail -s "Weekly Security Report" team@company.com < inventory-export/inventory.csv
```

### Monitor Critical Repos

```bash
# Show only critical and high risk repos
actionsguard inventory list --filter-risk CRITICAL
actionsguard inventory list --filter-risk HIGH

# Export just the critical ones
actionsguard inventory list --filter-risk CRITICAL --sort score
```

### Track Improvements

```bash
# Update after making security fixes
actionsguard inventory update --org my-org

# See improvements
actionsguard inventory diff

# Expected output:
# 📈 Improved:
#   app1: 5.2 → 7.8 (+2.6)
#   app2: 6.1 → 7.2 (+1.1)
```

### Audit Specific Repos

```bash
# Only track your critical applications
actionsguard inventory update --org my-org --only critical-app1,critical-app2,critical-app3
```

## Automation

### GitHub Actions (Weekly Updates)

```yaml
name: Update Security Inventory

on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday
  workflow_dispatch:

jobs:
  update-inventory:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Install ActionsGuard
        run: pip install actionsguard

      - name: Update Inventory
        run: actionsguard inventory update --org ${{ github.repository_owner }}
        env:
          GITHUB_TOKEN: ${{ secrets.ORG_SCAN_TOKEN }}

      - name: Export Reports
        run: actionsguard inventory export

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: inventory-reports
          path: inventory-export/

      - name: Commit Inventory
        run: |
          git config user.name "Security Bot"
          git config user.email "security@company.com"
          git add .actionsguard/inventory.json
          git commit -m "chore: Update security inventory"
          git push
```

### Cron Job (Self-Hosted)

```bash
# Add to crontab: crontab -e
0 0 * * 0 /path/to/update-inventory.sh

# update-inventory.sh
#!/bin/bash
export GITHUB_TOKEN="your_token"
cd /path/to/security-tracking
actionsguard inventory update --org my-org
actionsguard inventory export --output ./reports/$(date +%Y-%m-%d)
```

## Commands Reference

### Update Inventory

```bash
actionsguard inventory update --org ORG_NAME [OPTIONS]

Options:
  --org, -o           Organization name (required)
  --exclude TEXT      Comma-separated repos to exclude
  --only TEXT         Only scan these repos
  --token, -t TEXT    GitHub token (or GITHUB_TOKEN env var)
```

### List Inventory

```bash
actionsguard inventory list [OPTIONS]

Options:
  --sort [score|risk|name|updated]  Sort by field (default: risk)
  --filter-risk [CRITICAL|HIGH|MEDIUM|LOW]  Show only specific risk level
```

### Export Inventory

```bash
actionsguard inventory export [OPTIONS]

Options:
  --output, -o TEXT   Output directory (default: ./inventory-export)
  --format, -f TEXT   Formats: json,html,csv (default: all)
```

### Show Changes

```bash
actionsguard inventory diff

# No options - shows all changes since last scan
```

## How It Works

1. **First Scan**: Creates `.actionsguard/inventory.json`
2. **Each Update**:
   - Scans repos again
   - Compares to previous scores
   - Updates current state
   - Appends to history
3. **Historical Data**: Never deleted, keeps growing
4. **Diff Detection**: Compares last 2 scans

## Inventory File Structure

```json
{
  "org/repo1": {
    "repo_name": "org/repo1",
    "repo_url": "https://github.com/org/repo1",
    "current_score": 7.5,
    "current_risk": "MEDIUM",
    "first_seen": "2024-10-01T10:00:00",
    "last_updated": "2024-10-24T14:00:00",
    "scan_count": 8,
    "score_history": [
      {"date": "2024-10-01T10:00:00", "score": 6.8, "risk": "MEDIUM"},
      {"date": "2024-10-08T10:00:00", "score": 7.1, "risk": "MEDIUM"},
      {"date": "2024-10-15T10:00:00", "score": 7.3, "risk": "MEDIUM"},
      {"date": "2024-10-24T14:00:00", "score": 7.5, "risk": "MEDIUM"}
    ],
    "latest_checks": {
      "Dangerous-Workflow": {"score": 8, "status": "PASS", "severity": "LOW"},
      "Token-Permissions": {"score": 7, "status": "WARN", "severity": "MEDIUM"}
    },
    "metadata": {...}
  }
}
```

## Best Practices

1. **Update Regularly**: Weekly or bi-weekly scans
2. **Version Control**: Commit `.actionsguard/inventory.json` to git
3. **Export Reports**: Keep historical exports for comparison
4. **Monitor Changes**: Set up alerts for regressions
5. **Exclude Archived**: Use `--exclude` for inactive repos

## Troubleshooting

**Inventory not found**:
```bash
# Create initial inventory
actionsguard inventory update --org your-org
```

**Old scores showing**:
```bash
# Force refresh
rm -rf .actionsguard/inventory.json
actionsguard inventory update --org your-org
```

**Export fails**:
```bash
# Check inventory exists
cat .actionsguard/inventory.json

# If empty, run update first
actionsguard inventory update --org your-org
```

## Example Workflow

```bash
# Day 1: Initial scan
actionsguard inventory update --org my-company
actionsguard inventory list

# Day 7: Weekly update
actionsguard inventory update --org my-company
actionsguard inventory diff  # See what changed
actionsguard inventory export  # Generate reports

# Day 14: Another update
actionsguard inventory update --org my-company
actionsguard inventory diff
actionsguard inventory export

# Now you have 3 weeks of history!
```

## What's Next?

After building your inventory, you can:
- Set up automated weekly scans
- Create alerts for score drops
- Track compliance over time
- Generate executive dashboards
- Compare teams/orgs

---

**Simple. Powerful. Automatic.**

Just run `actionsguard inventory update --org your-org` and you're tracking!
