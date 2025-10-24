# ActionsGuard 🛡️

**GitHub Actions Security Scanner** - Scan your GitHub Actions workflows for security vulnerabilities using OpenSSF Scorecard.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/actionsguard.svg)](https://badge.fury.io/py/actionsguard)

## Features

- **🔍 Comprehensive Scanning**: Scan single repositories or entire organizations
- **📊 Multiple Report Formats**: JSON, HTML, CSV, and Markdown reports
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

### Via pip (Recommended)

```bash
pip install actionsguard
```

### From source

```bash
git clone https://github.com/your-username/actionsguard.git
cd actionsguard
pip install -e .
```

### Prerequisites

ActionsGuard requires [OpenSSF Scorecard](https://github.com/ossf/scorecard) to be installed:

```bash
# Using Go
go install github.com/ossf/scorecard/v5/cmd/scorecard@latest

# Or download from releases
# https://github.com/ossf/scorecard/releases
```

## Quick Start

### 1. Set up GitHub Token

```bash
export GITHUB_TOKEN="your_github_personal_access_token"
```

The token needs the following scopes:
- `repo` (for private repos) or `public_repo` (for public repos only)
- `read:org` (for organization scanning)

### 2. Scan a Repository

```bash
actionsguard scan --repo owner/repository
```

### 3. Scan an Organization

```bash
actionsguard scan --org your-organization
```

## Usage

### CLI Examples

#### Basic Scanning

```bash
# Scan a single repository
actionsguard scan --repo kubernetes/kubernetes

# Scan entire organization
actionsguard scan --org my-org

# Scan with custom token
actionsguard scan --repo owner/repo --token ghp_xxxxxxxxxxxx
```

#### Advanced Filtering

```bash
# Exclude specific repositories
actionsguard scan --org my-org --exclude repo1,repo2

# Only scan specific repositories
actionsguard scan --org my-org --only important-repo,critical-repo

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
git clone https://github.com/your-username/actionsguard.git
cd actionsguard

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

### Common Issues

**Scorecard not found**
```bash
Error: OpenSSF Scorecard not found
```
Solution: Install Scorecard as described in [Prerequisites](#prerequisites)

**Rate limit exceeded**
```bash
Error: GitHub API rate limit exceeded
```
Solution: Wait for rate limit reset or use a different token

**No permissions**
```bash
Error: No permission to access organization
```
Solution: Ensure token has `read:org` scope

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

## Support

- **Documentation**: [GitHub Wiki](https://github.com/your-username/actionsguard/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-username/actionsguard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/actionsguard/discussions)

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
