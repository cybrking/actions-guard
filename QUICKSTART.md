# ActionsGuard - Quick Start Guide

This guide will help you install and run ActionsGuard in under 5 minutes.

## Step 1: Install OpenSSF Scorecard

### For macOS Users

**Option A: Using curl (Recommended)**

```bash
# For Apple Silicon (M1/M2/M3)
curl -Lo scorecard https://github.com/ossf/scorecard/releases/latest/download/scorecard_darwin_arm64
chmod +x scorecard
sudo mv scorecard /usr/local/bin/

# For Intel Macs
curl -Lo scorecard https://github.com/ossf/scorecard/releases/latest/download/scorecard_darwin_amd64
chmod +x scorecard
sudo mv scorecard /usr/local/bin/
```

**Option B: Using Go**

```bash
# IMPORTANT: Use v4, not v5!
go install github.com/ossf/scorecard/v4/cmd/scorecard@latest

# Add to PATH (add this to your ~/.zshrc or ~/.bash_profile)
export PATH=$PATH:$(go env GOPATH)/bin

# Reload your shell
source ~/.zshrc  # or source ~/.bash_profile
```

**Verify Installation:**

```bash
scorecard version
# Should output something like: scorecard version: v4.x.x
```

### For Linux Users

```bash
# Download binary
curl -Lo scorecard https://github.com/ossf/scorecard/releases/latest/download/scorecard_linux_amd64
chmod +x scorecard
sudo mv scorecard /usr/local/bin/

# Verify
scorecard version
```

### For Windows Users

Download the binary from: https://github.com/ossf/scorecard/releases/latest

Extract and add to PATH, then verify:
```cmd
scorecard version
```

---

## Step 2: Install ActionsGuard

### Clone the Repository

```bash
# Clone from GitHub
git clone https://github.com/cybrking/actions-guard.git
cd actions-guard
```

### Set Up Python Environment

```bash
# Create virtual environment (recommended)
python3 -m venv venv

# Activate it
# For macOS/Linux:
source venv/bin/activate

# For Windows:
# venv\Scripts\activate
```

### Install Dependencies

```bash
# Install ActionsGuard and dependencies
pip install -e .

# Verify installation
actionsguard --version
# Should output: actionsguard, version 1.0.0
```

---

## Step 3: Set Up GitHub Token

### Create a GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens/new
2. Name it: "ActionsGuard Scanner"
3. Select scopes:
   - ✅ `repo` (for private repos) or `public_repo` (for public only)
   - ✅ `read:org` (for organization scanning)
4. Click "Generate token"
5. **Copy the token** (you won't see it again!)

### Set the Token

```bash
# Export as environment variable
export GITHUB_TOKEN="ghp_YourTokenHere"

# Or add to your shell config for persistence
echo 'export GITHUB_TOKEN="ghp_YourTokenHere"' >> ~/.zshrc
source ~/.zshrc
```

---

## Step 4: Run Your First Scan

### Test with a Single Repository

```bash
# Scan the Kubernetes repository (public example)
actionsguard scan --repo kubernetes/kubernetes
```

### Scan Your Own Repository

```bash
# Replace with your repo
actionsguard scan --repo your-username/your-repo
```

### Scan an Organization

```bash
# Scan all repos in an organization
actionsguard scan --org your-org-name
```

### View the Reports

After scanning, reports will be in the `./reports` directory:

```bash
# List generated reports
ls -lh reports/

# Open HTML report in browser
# macOS:
open reports/report.html

# Linux:
xdg-open reports/report.html

# Windows:
start reports/report.html
```

---

## Common Use Cases

### 1. Weekly Security Audit

```bash
# Scan your organization, excluding archived repos
actionsguard scan --org my-company \
  --exclude old-repo1,archived-repo2 \
  --output ./weekly-audit
```

### 2. CI/CD Integration

```bash
# Fail if critical issues found
actionsguard scan --repo my-org/my-app \
  --fail-on-critical \
  --format json,markdown
```

### 3. Focus on Specific Checks

```bash
# Only check for dangerous workflows and token permissions
actionsguard scan --org my-org \
  --checks Dangerous-Workflow,Token-Permissions
```

### 4. Run All Scorecard Checks

```bash
# Get comprehensive security analysis
actionsguard scan --repo my-org/critical-app \
  --all-checks
```

---

## What to Look For in Reports

### Risk Levels

- 🔴 **CRITICAL** (Score 0-3.9): Immediate action required
- 🟠 **HIGH** (Score 4.0-5.9): Address soon
- 🟡 **MEDIUM** (Score 6.0-7.9): Moderate risk
- 🟢 **LOW** (Score 8.0-10.0): Good security posture

### Key Security Checks

1. **Dangerous-Workflow**: Looks for untrusted input in dangerous contexts
2. **Token-Permissions**: Ensures minimal token permissions
3. **Pinned-Dependencies**: Verifies dependencies are pinned to specific versions

---

## Troubleshooting

### Issue: "Scorecard not found"

```bash
# Check if scorecard is in PATH
which scorecard

# If not found, reinstall and verify
scorecard version
```

### Issue: "GitHub token not found"

```bash
# Verify token is set
echo $GITHUB_TOKEN

# If empty, export it again
export GITHUB_TOKEN="your-token-here"
```

### Issue: "Rate limit exceeded"

```bash
# Check your rate limit status
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/rate_limit | jq .

# Wait for reset time or use a different token
```

### Issue: "No permission to access organization"

Make sure your token has the `read:org` scope. You may need to create a new token with the correct scopes.

---

## Next Steps

1. **Schedule Regular Scans**: Set up a cron job or GitHub Action
2. **Review Critical Issues**: Start with 🔴 CRITICAL findings
3. **Track Progress**: Keep reports for comparison over time
4. **Share Results**: Use HTML reports for stakeholder presentations

---

## Getting Help

- **Documentation**: [Full README](README.md)
- **Issues**: [GitHub Issues](https://github.com/cybrking/actions-guard/issues)
- **Examples**: See the `examples/` directory

---

**Happy Scanning! 🛡️**
