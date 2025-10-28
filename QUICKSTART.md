# ActionsGuard - Quick Start Guide

This guide will help you install and run ActionsGuard in under 5 minutes.

## Step 1: Install OpenSSF Scorecard

### For macOS or Linux Users

**Option 1: Homebrew (Easiest)**

```bash
# Install scorecard via Homebrew
brew install scorecard

# Verify installation
scorecard version
# Should output something like: scorecard version: v5.x.x
```

**Option 2: Docker**

```bash
# Pull the official Docker image
docker pull gcr.io/openssf/scorecard:stable

# You can use Docker to run scorecard without local installation
# (See Docker usage examples later in this guide)
```

**Option 3: Go Install**

```bash
# If you have Go 1.21+ installed
go install github.com/ossf/scorecard/v5/cmd/scorecard@latest

# Add to PATH (add this to your ~/.zshrc or ~/.bash_profile)
export PATH=$PATH:$(go env GOPATH)/bin

# Reload your shell
source ~/.zshrc  # or source ~/.bash_profile

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

### Install ActionsGuard

```bash
# Install ActionsGuard
pip3 install .

# Verify installation
actionsguard --version
# Should output: actionsguard, version 1.0.0
```

---

## Step 3: Set Up GitHub Token

### Option 1: Fine-grained Token (Recommended) ⭐

Fine-grained tokens are more secure and provide granular access control.

**Create the token:**

1. Go to: https://github.com/settings/personal-access-tokens/new
2. Fill in the details:
   - **Token name**: "ActionsGuard Scanner"
   - **Expiration**: 90 days (or custom)
   - **Description**: "Security scanning for GitHub Actions workflows"

3. **Repository access**:
   - For single repo scanning: Select "Only select repositories" → Choose your repos
   - For organization scanning: Select "All repositories" (for your organizations)

4. **Permissions** - Set these Repository permissions:
   - ✅ **Actions**: Read (to access workflow files)
   - ✅ **Contents**: Read (to read repository contents)
   - ✅ **Metadata**: Read (automatically included)

5. **Organization permissions** (for org scanning):
   - ✅ **Members**: Read (to list organization repositories)

6. Click "Generate token"
7. **Copy the token** - it starts with `github_pat_`

**Set the token:**

```bash
# Export as environment variable
export GITHUB_TOKEN="github_pat_YourTokenHere"

# Or add to your shell config for persistence
echo 'export GITHUB_TOKEN="github_pat_YourTokenHere"' >> ~/.zshrc
source ~/.zshrc
```

### Option 2: Classic Token (Alternative)

Classic tokens have broader access but are simpler to set up.

1. Go to: https://github.com/settings/tokens/new
2. Name it: "ActionsGuard Scanner"
3. Select scopes:
   - ✅ `repo` (for private repos) or `public_repo` (for public only)
   - ✅ `read:org` (for organization scanning)
4. Click "Generate token"
5. **Copy the token** - it starts with `ghp_`

```bash
# Export as environment variable
export GITHUB_TOKEN="ghp_YourTokenHere"

# Or add to your shell config for persistence
echo 'export GITHUB_TOKEN="ghp_YourTokenHere"' >> ~/.zshrc
source ~/.zshrc
```

### Verify Token Setup

```bash
# Check if token is set
echo $GITHUB_TOKEN

# Test token (should show your username)
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | grep login
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

This is the most common issue!

**Quick fix:**
```bash
# Verify token is set
echo $GITHUB_TOKEN

# If empty, export it again
export GITHUB_TOKEN="your-token-here"

# If still not working, use the --token flag
actionsguard scan --repo owner/repo --token "your-token-here"
```

**Detailed troubleshooting:** See [TROUBLESHOOTING_TOKEN.md](docs/TROUBLESHOOTING_TOKEN.md) for comprehensive debugging steps.

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
