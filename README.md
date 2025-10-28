# ActionsGuard 🛡️

**GitHub Actions Security Scanner** - Scan your GitHub Actions workflows for security vulnerabilities using OpenSSF Scorecard.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/actionsguard.svg)](https://badge.fury.io/py/actionsguard)

## Features

- **🔍 Comprehensive Scanning**: Scan single repositories, entire organizations, or user accounts
- **📊 Multiple Report Formats**: JSON, HTML, CSV, and Markdown reports
- **📦 Inventory Tracking**: Keep track of all your repos and their security scores over time
- **🚀 Easy Integration**: Use as CLI tool or GitHub Action
- **⚡ Parallel Execution**: Fast scanning with concurrent repository processing
- **🎯 Focused Checks**: Run specific security checks or all OpenSSF Scorecard checks
- **📈 Beautiful Reports**: Visual HTML reports with risk scoring and detailed findings

## What It Checks

ActionsGuard leverages [OpenSSF Scorecard](https://github.com/ossf/scorecard) to check for:

- **Dangerous Workflows**: Detects potentially dangerous patterns in GitHub Actions
- **Token Permissions**: Ensures proper token permission configuration
- **Pinned Dependencies**: Verifies dependencies are pinned to specific versions
- And 15+ additional security checks

## Installation

### Prerequisites

**Important**: ActionsGuard requires [OpenSSF Scorecard](https://github.com/ossf/scorecard) to be installed first.

#### Option 1: Homebrew (Recommended)

```bash
# macOS or Linux (with Homebrew installed)
brew install scorecard
```

#### Option 2: Docker

```bash
# Use the official Docker image
docker pull gcr.io/openssf/scorecard:stable

# Run scorecard via Docker
docker run -e GITHUB_AUTH_TOKEN=token gcr.io/openssf/scorecard:stable \
  --show-details --repo=https://github.com/owner/repo
```

#### Option 3: Go Install

```bash
# If you have Go 1.21+ installed
go install github.com/ossf/scorecard/v5/cmd/scorecard@latest

# Make sure $GOPATH/bin is in your PATH
export PATH=$PATH:$(go env GOPATH)/bin
```

#### Option 4: Download Binary (Manual)

```bash
# Download from releases page
# Visit: https://github.com/ossf/scorecard/releases/latest
# Download the appropriate tar.gz for your platform
# Example for Linux:
curl -LO https://github.com/ossf/scorecard/releases/download/v5.3.0/scorecard_5.3.0_linux_amd64.tar.gz
tar -xzf scorecard_5.3.0_linux_amd64.tar.gz
sudo mv scorecard /usr/local/bin/
```

Verify installation:
```bash
scorecard version
```

### Install ActionsGuard

#### Development Installation (Current Method)

Since ActionsGuard is not yet published to PyPI, install from source:

```bash
# Clone the repository
git clone https://github.com/cybrking/actions-guard.git
cd actions-guard

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install ActionsGuard in development mode
pip install -e .

# Verify installation
actionsguard --version
```

#### Future: Via pip (After PyPI Publication)

```bash
pip install actionsguard
```

## Quick Start

### 1. Set up GitHub Token

**Option A: Fine-grained Token (Recommended)**

Create at: https://github.com/settings/personal-access-tokens/new

**Permissions needed:**
- Repository permissions:
  - Actions: Read
  - Contents: Read
  - Metadata: Read
- Organization permissions (for org scanning):
  - Members: Read

```bash
export GITHUB_TOKEN="github_pat_your_token_here"
```

**Option B: Classic Token**

Create at: https://github.com/settings/tokens/new

**Scopes needed:**
- `repo` (for private repos) or `public_repo` (for public repos only)
- `read:org` (for organization scanning)

```bash
export GITHUB_TOKEN="ghp_your_token_here"
```

**⚠️ Important for Private Repositories:**

If you're scanning your own private repos, you MUST use `repo` scope (not just `public_repo`). If you see "0 repositories found", your token likely doesn't have the right permissions.

**Quick test:**
```bash
# Check if your token can see your repos
actionsguard debug --user your-username
```

The debug command will:
- Show which user you're authenticated as
- Display your token scopes
- List all repositories your token can see
- Explain why repos might be filtered out

### 2. Scan a Repository

```bash
actionsguard scan --repo owner/repository
```

### 3. Scan an Organization or User Account

```bash
# Scan an entire organization
actionsguard scan --org your-organization

# Scan a user account (e.g., your personal repos)
actionsguard scan --user cybrking
```

## Usage

### CLI Examples

#### Basic Scanning

```bash
# Scan a single repository
actionsguard scan --repo kubernetes/kubernetes

# Scan entire organization
actionsguard scan --org my-org

# Scan a user account (personal repos)
actionsguard scan --user cybrking

# Scan with custom token
actionsguard scan --repo owner/repo --token ghp_xxxxxxxxxxxx
```

#### Advanced Filtering

```bash
# Exclude specific repositories
actionsguard scan --org my-org --exclude repo1,repo2
actionsguard scan --user cybrking --exclude forked-repo

# Only scan specific repositories
actionsguard scan --org my-org --only important-repo,critical-repo
actionsguard scan --user cybrking --only my-critical-project

# Run specific security checks
actionsguard scan --org my-org --checks Dangerous-Workflow,Token-Permissions

# Run all Scorecard checks
actionsguard scan --org my-org --all-checks
```

#### Custom Output

```bash
# Change output directory
actionsguard scan --org my-org --output ./security-reports

# Generate specific report formats
actionsguard scan --org my-org --format json,html

# Fail on critical issues (useful for CI/CD)
actionsguard scan --org my-org --fail-on-critical
```

#### Parallel Scanning

```bash
# Adjust parallel scan workers (default: 5)
actionsguard scan --org my-org --parallel 10
```

### GitHub Action Usage

Add ActionsGuard to your workflow:

```yaml
name: Security Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Run ActionsGuard
        uses: your-username/actionsguard@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          org-name: my-organization
          fail-on-critical: true

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        with:
          name: security-reports
          path: reports/
```

#### Action Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `github-token` | GitHub token for API access | Yes | - |
| `org-name` | Organization to scan | No | Current repo org |
| `repo-name` | Single repository to scan | No | - |
| `exclude-repos` | Comma-separated repos to exclude | No | - |
| `only-repos` | Only scan these repos | No | - |
| `checks` | Specific checks to run | No | `Dangerous-Workflow,Token-Permissions,Pinned-Dependencies` |
| `all-checks` | Run all checks | No | `false` |
| `output-format` | Report formats | No | `html,json,csv,markdown` |
| `fail-on-critical` | Fail if critical issues found | No | `false` |

#### Action Outputs

| Output | Description |
|--------|-------------|
| `reports-path` | Path to generated reports |
| `critical-count` | Number of critical issues |
| `overall-score` | Average security score |
| `summary` | JSON scan summary |

## Report Formats

### HTML Report

Beautiful, interactive HTML report with:
- Executive summary with metrics
- Color-coded risk levels
- Collapsible sections for easy navigation
- Direct links to documentation
- Mobile-responsive design

### JSON Report

Machine-readable JSON with complete scan data:

```json
{
  "total_repos": 50,
  "successful_scans": 48,
  "failed_scans": 2,
  "average_score": 7.2,
  "critical_count": 3,
  "results": [...]
}
```

### CSV Report

Spreadsheet-compatible format for analysis in Excel or Google Sheets:

```csv
Repository,URL,Score,Risk Level,Critical Issues,High Issues,...
owner/repo1,https://...,6.5,MEDIUM,0,2,...
```

### Markdown Report

GitHub-flavored markdown with emojis and collapsible sections, perfect for:
- GitHub Issues
- Pull Request comments
- Documentation

## Configuration

### Environment Variables

- `GITHUB_TOKEN`: GitHub personal access token
- `ACTIONSGUARD_OUTPUT_DIR`: Default output directory
- `ACTIONSGUARD_CHECKS`: Default checks to run

### Exit Codes

- `0`: Success, no critical issues
- `1`: Critical issues found (with `--fail-on-critical`)
- `2`: Error during execution

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/cybrking/actions-guard.git
cd actions-guard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/ -v --cov=actionsguard
```

### Code Quality

```bash
# Format code
black actionsguard/ tests/

# Lint
flake8 actionsguard/ tests/

# Type checking
mypy actionsguard/
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Security Scan
  run: |
    pip install actionsguard
    actionsguard scan --org ${{ github.repository_owner }} --fail-on-critical
```

### GitLab CI

```yaml
security_scan:
  script:
    - pip install actionsguard
    - actionsguard scan --org my-org --fail-on-critical
  artifacts:
    paths:
      - reports/
```

### Jenkins

```groovy
stage('Security Scan') {
    steps {
        sh 'pip install actionsguard'
        sh 'actionsguard scan --org my-org --fail-on-critical'
        publishHTML([
            reportDir: 'reports',
            reportFiles: 'report.html',
            reportName: 'Security Report'
        ])
    }
}
```

## Troubleshooting

For detailed troubleshooting guides, see:
- **Token Issues**: [docs/TROUBLESHOOTING_TOKEN.md](docs/TROUBLESHOOTING_TOKEN.md)
- **General Guide**: [docs/TOKEN_GUIDE.md](docs/TOKEN_GUIDE.md)

### Common Issues

**1. Scorecard Command Not Found**

```bash
Error: OpenSSF Scorecard not found
```

**Solution**: Install scorecard using one of the recommended methods:

```bash
# Easiest: Use Homebrew (macOS or Linux)
brew install scorecard

# Or use Docker
docker pull gcr.io/openssf/scorecard:stable

# Or use Go (if you have Go installed)
go install github.com/ossf/scorecard/v5/cmd/scorecard@latest
export PATH=$PATH:$(go env GOPATH)/bin
```

**2. ActionsGuard Not Found on PyPI**

```bash
ERROR: Could not find a version that satisfies the requirement actionsguard
```

**Solution**: ActionsGuard is not yet published to PyPI. Install from source:

```bash
git clone https://github.com/cybrking/actions-guard.git
cd actions-guard
pip install -e .
```

**3. GitHub API Rate Limit**

```bash
Error: GitHub API rate limit exceeded
```

**Solution**:
- Wait for rate limit reset (check: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit`)
- Use a different token
- Authenticated requests have higher limits (5000/hour vs 60/hour)

**4. Organization Access Denied**

```bash
Error: No permission to access organization
```

**Solution**:
- For Fine-grained tokens: Ensure "Members: Read" permission is granted under Organization permissions
- For Classic tokens: Ensure your token has the `read:org` scope
- Verify you're a member of the organization or have appropriate access

**5. Python Project Not Found**

```bash
ERROR: file:///path does not appear to be a Python project
```

**Solution**: Make sure you're in the correct directory (should contain `setup.py` and `pyproject.toml`):

```bash
cd actions-guard  # Navigate to the cloned repository
pip install -e .
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OpenSSF Scorecard](https://github.com/ossf/scorecard) - The security checks engine
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API wrapper
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://github.com/Textualize/rich) - Terminal formatting

## Roadmap

- [ ] SARIF output for GitHub Security tab
- [ ] Comparison mode for regression detection
- [ ] Auto-create GitHub Issues for critical findings
- [ ] Custom security check plugins
- [ ] Web UI for report visualization
- [ ] Integration with more CI/CD platforms

---

**Made with ❤️ by Travis Felder**

If you find ActionsGuard useful, please consider giving it a ⭐ on GitHub!
