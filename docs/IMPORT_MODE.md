# ActionsGuard Import Mode - User Guide

Use ActionsGuard to generate beautiful reports from existing Scorecard scans!

## Why Use Import Mode?

- **Skip installation issues**: Don't worry about Scorecard binary compatibility
- **Use official Scorecard**: Run Scorecard yourself with any version
- **Batch processing**: Scan multiple repos with Scorecard, then batch convert to reports
- **CI/CD friendly**: Separate scanning from reporting in your pipelines

## Quick Start

### Step 1: Run Scorecard Yourself

```bash
# Install Scorecard - choose your preferred method:

# Option 1: Homebrew (easiest)
brew install scorecard

# Option 2: Docker
# docker pull gcr.io/openssf/scorecard:stable

# Option 3: Go
# go install github.com/ossf/scorecard/v5/cmd/scorecard@latest

# Scan a repository and save JSON
scorecard --repo=github.com/kubernetes/kubernetes --format=json > kubernetes.json

# Or scan multiple repos
scorecard --repo=github.com/your-org/repo1 --format=json > repo1.json
scorecard --repo=github.com/your-org/repo2 --format=json > repo2.json
```

### Step 2: Generate Beautiful Reports

```bash
# Install ActionsGuard
pip install -e .

# Import and generate reports
actionsguard import-scorecard kubernetes.json

# That's it! Check ./reports/ for HTML, Markdown, and CSV reports
```

## Usage Examples

### Basic Import

```bash
# Generate all default formats (HTML, Markdown, CSV)
actionsguard import-scorecard scorecard.json
```

### Custom Output Directory

```bash
# Save reports to a custom directory
actionsguard import-scorecard scorecard.json --output ./my-reports
```

### Specific Formats Only

```bash
# Generate only HTML
actionsguard import-scorecard scorecard.json --format html

# Generate HTML and Markdown
actionsguard import-scorecard scorecard.json --format html,markdown

# Generate all formats including JSON
actionsguard import-scorecard scorecard.json --format html,markdown,csv,json
```

### Override Repository Name

```bash
# Manually specify repo name if auto-detection fails
actionsguard import-scorecard scorecard.json --repo-name kubernetes/kubernetes
```

## Batch Processing Multiple Repos

```bash
#!/bin/bash
# scan-all.sh - Scan multiple repos

# List of repos to scan
REPOS=(
    "kubernetes/kubernetes"
    "prometheus/prometheus"
    "grafana/grafana"
)

# Scan each repo
for repo in "${REPOS[@]}"; do
    echo "Scanning $repo..."
    scorecard --repo=github.com/$repo --format=json > "${repo//\//-}.json"
done

# Generate reports for all
for json_file in *.json; do
    echo "Generating reports for $json_file..."
    actionsguard import-scorecard "$json_file" --output "./reports/$(basename $json_file .json)"
done

echo "All reports generated!"
```

## What You Get

After running `actionsguard import-scorecard`, you'll get:

### HTML Report (`report.html`)
- Beautiful, interactive visualization
- Color-coded risk levels
- Sortable tables
- Mobile-responsive
- Shareable with stakeholders

### Markdown Report (`report.md`)
- GitHub-friendly format
- Emojis for visual indicators
- Collapsible sections
- Perfect for issues/PRs

### CSV Report (`report.csv`)
- Excel/Google Sheets compatible
- Easy filtering and sorting
- Great for data analysis
- Comparison tracking

### JSON Report (`report.json`) - Optional
- Machine-readable
- Complete scan data
- API integration ready

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Security Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Install Scorecard
        run: |
          # Using Homebrew (if available on runner)
          brew install scorecard
          # Or use Go:
          # go install github.com/ossf/scorecard/v5/cmd/scorecard@latest
          # echo "$(go env GOPATH)/bin" >> $GITHUB_PATH

      - name: Scan Repository
        run: |
          scorecard --repo=github.com/${{ github.repository }} \
            --format=json > scorecard.json
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Generate Reports
        run: |
          pip install actionsguard
          actionsguard import-scorecard scorecard.json

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: reports/

      - name: Comment on PR (if available)
        if: github.event_name == 'pull_request'
        run: |
          gh pr comment ${{ github.event.pull_request.number }} \
            --body-file reports/report.md
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### GitLab CI Example

```yaml
security_scan:
  stage: test
  script:
    # Install scorecard via Go (most reliable in CI)
    - go install github.com/ossf/scorecard/v5/cmd/scorecard@latest
    - export PATH=$PATH:$(go env GOPATH)/bin
    - scorecard --repo=github.com/your-org/your-repo --format=json > scorecard.json
    - pip install actionsguard
    - actionsguard import-scorecard scorecard.json
  artifacts:
    paths:
      - reports/
    reports:
      junit: reports/report.xml
```

## Comparison: Import vs Scan Mode

| Feature | `import-scorecard` | `scan` |
|---------|-------------------|--------|
| **Scorecard required?** | Yes (run separately) | Yes (called by ActionsGuard) |
| **Installation issues?** | None | Possible binary mismatch |
| **Token needed?** | No (for import) | Yes |
| **Best for** | Existing scans, CI/CD | Quick all-in-one scanning |
| **Flexibility** | High | Medium |
| **Speed** | Fast (just reporting) | Slower (scanning + reporting) |

## Troubleshooting

### "Invalid JSON file"

```bash
# Verify JSON is valid
jq . scorecard.json

# If invalid, check Scorecard ran successfully
scorecard --repo=github.com/owner/repo --format=json > scorecard.json
echo $?  # Should be 0
```

### "Repository name not detected"

```bash
# Manually specify the repo name
actionsguard import-scorecard scorecard.json --repo-name owner/repo
```

### "No such file"

```bash
# Check the file exists
ls -lh scorecard.json

# Use absolute path
actionsguard import-scorecard /full/path/to/scorecard.json
```

## Tips and Tricks

### 1. Scan Organization Repos

```bash
# Get all org repos
gh repo list your-org --limit 1000 --json nameWithOwner -q '.[].nameWithOwner' > repos.txt

# Scan each
while read repo; do
    echo "Scanning $repo..."
    scorecard --repo=github.com/$repo --format=json > "${repo//\//-}.json"
    actionsguard import-scorecard "${repo//\//-}.json" --output "./reports/$repo"
done < repos.txt
```

### 2. Compare Over Time

```bash
# Scan today
scorecard --repo=github.com/owner/repo --format=json > scan-$(date +%Y-%m-%d).json

# Generate report
actionsguard import-scorecard scan-$(date +%Y-%m-%d).json --output ./reports/$(date +%Y-%m-%d)

# Keep history for comparison
```

### 3. Combine Multiple Scans

```bash
# Scan multiple repos
for repo in repo1 repo2 repo3; do
    scorecard --repo=github.com/org/$repo --format=json > $repo.json
done

# Generate combined report
actionsguard import-scorecard repo1.json repo2.json repo3.json --output ./combined-report
# Note: Multi-file import coming in future version!
```

## Next Steps

1. **Run your first scan**: `scorecard --repo=github.com/owner/repo --format=json > report.json`
2. **Generate reports**: `actionsguard import-scorecard report.json`
3. **View HTML report**: `open reports/report.html`
4. **Share with team**: Send the HTML or add Markdown to GitHub issues

## Getting Help

- **Issues**: https://github.com/cybrking/actions-guard/issues
- **Examples**: See `examples/` directory
- **Documentation**: [README.md](../README.md)

---

**Pro Tip**: You can use `import-scorecard` even if Scorecard isn't installed on your machine - just get the JSON from someone who ran it!
