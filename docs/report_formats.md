# ActionsGuard Report Formats

ActionsGuard generates comprehensive security reports in multiple formats to suit different use cases.

## Overview

All report formats include:
- **Executive Summary**: High-level metrics and risk distribution
- **Workflow-Level Findings**: Security issues identified in specific workflow files
- **Actionable Recommendations**: Step-by-step remediation guidance
- **Risk Categorization**: Repositories grouped by risk level (Critical/High/Medium/Low)

## Available Formats

### 1. HTML Report

**Format:** `html`

**Best for:**
- Presenting to stakeholders and management
- Sharing with non-technical teams
- Visual analysis and exploration
- Print-friendly documentation

**Features:**
- Enterprise-grade visual design with purple gradient header
- Interactive layout with color-coded severity badges
- Metrics dashboard with executive summary
- Risk distribution visualization
- Per-repository sections with workflow breakdowns
- Highlighted remediation recommendations
- Responsive design (mobile-friendly)
- Professional styling suitable for formal reports

**Usage:**
```bash
actionsguard scan --user USERNAME --format html
```

**Output:** `reports/report.html`

**Example Structure:**
```
📊 Executive Summary
├── Metrics Grid (Total Repos, Avg Score, Issues, Duration)
├── Risk Distribution (Critical/High/Medium/Low counts)
└── Top 5 Issues (Most common security problems)

📁 Repository Details
├── owner/repo-name (Risk Badge: CRITICAL)
│   ├── Score: 3.5/10
│   ├── .github/workflows/ci.yml (3 issues)
│   │   ├── 🔴 Dangerous-Workflow (CRITICAL)
│   │   │   ├── Message: pull_request_target detected
│   │   │   ├── Line: 12
│   │   │   └── 💡 How to Fix: Replace 'pull_request_target'...
│   │   └── 🟠 Token-Permissions (HIGH)
│   └── .github/workflows/release.yml (1 issue)
└── ...
```

---

### 2. Markdown Report

**Format:** `markdown`

**Best for:**
- GitHub/GitLab documentation
- README files and wikis
- Version-controlled reports
- Developer-friendly format

**Features:**
- GitHub Flavored Markdown
- Emoji indicators for severity and status
- Tables for metrics and top issues
- Collapsible sections for low-priority items
- Linked repository names
- Code-formatted workflow paths
- Blockquotes for recommendations

**Usage:**
```bash
actionsguard scan --user USERNAME --format markdown
```

**Output:** `reports/report.md`

**Example Structure:**
```markdown
# 🛡️ ActionsGuard Security Report

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| Total Repositories | 5 (5 scanned successfully) |
| Average Score | 7.2/10 |
| Total Issues | 28 |

### Risk Distribution

- 🔴 **Critical:** 1 repositories
- 🟠 **High:** 2 repositories
- 🟡 **Medium:** 1 repositories
- 🟢 **Low:** 1 repositories

### 🔍 Top Security Issues

| Issue | Instances | Repos Affected |
|-------|-----------|----------------|
| Dangerous-Workflow | 8 | 3 |
| Token-Permissions | 5 | 4 |

## 📁 Repository Details

### 🔴 [owner/repo](https://github.com/owner/repo)

**Score:** 3.5/10.0 | **Risk:** CRITICAL

#### 📁 Workflow Security Analysis

##### `.github/workflows/ci.yml` (3 issues)

**🔴 Dangerous-Workflow** (CRITICAL)

pull_request_target workflow with code checkout detected

📍 **Line:** 12

> 💡 **How to Fix:** Replace 'pull_request_target' with 'pull_request' trigger...
```

---

### 3. JSON Report

**Format:** `json`

**Best for:**
- Automated processing and integration
- Security dashboards and SIEM tools
- Custom analysis scripts
- Data warehousing
- API integrations

**Features:**
- Structured machine-readable format
- Schema versioning for compatibility
- Complete data including all findings
- Metadata and timestamps
- Nested hierarchy preserving relationships
- UTF-8 encoding with proper escaping

**Usage:**
```bash
actionsguard scan --user USERNAME --format json
```

**Output:** `reports/report.json`

**Schema Documentation:** See [json_schema.md](./json_schema.md)

**Example Structure:**
```json
{
  "schema_version": "1.0.0",
  "tool": "ActionsGuard",
  "report_type": "security_scan",
  "generated_at": "2025-10-25T14:30:00.123456",
  "summary": {
    "total_repos": 5,
    "successful_scans": 5,
    "failed_scans": 0,
    "average_score": 7.2,
    "executive_summary": {
      "risk_distribution": {
        "CRITICAL": 1,
        "HIGH": 2,
        "MEDIUM": 1,
        "LOW": 1
      },
      "top_issues": [...]
    },
    "results": [
      {
        "repo_name": "owner/repo",
        "score": 6.5,
        "risk_level": "MEDIUM",
        "workflows": [
          {
            "path": ".github/workflows/ci.yml",
            "findings": [
              {
                "check_name": "Dangerous-Workflow",
                "severity": "CRITICAL",
                "message": "...",
                "line_number": 12,
                "recommendation": "..."
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**Python Integration Example:**
```python
import json

# Load report
with open('reports/report.json') as f:
    report = json.load(f)

# Extract critical findings
for repo in report['summary']['results']:
    for workflow in repo['workflows']:
        critical = [f for f in workflow['findings']
                   if f['severity'] == 'CRITICAL']
        if critical:
            print(f"{repo['repo_name']}: {len(critical)} critical issues")
```

---

### 4. CSV Report

**Format:** `csv`

**Best for:**
- Excel/Google Sheets analysis
- Bulk data processing
- Simple filtering and sorting
- Non-technical users
- Quick overview of all repositories

**Features:**
- Flat table structure
- Repository-level summary
- Score and risk level per repo
- Issue counts by severity
- Compatible with spreadsheet software

**Usage:**
```bash
actionsguard scan --user USERNAME --format csv
```

**Output:** `reports/report.csv`

**Columns:**
- Repository Name
- Repository URL
- Score
- Risk Level
- Critical Issues
- High Issues
- Medium Issues
- Low Issues
- Scan Date
- Error (if any)

---

## Multi-Format Generation

Generate multiple formats simultaneously:

```bash
# All formats
actionsguard scan --user USERNAME --format html,markdown,json,csv

# Selected formats
actionsguard scan --user USERNAME --format html,json
```

## Report Contents Comparison

| Feature | HTML | Markdown | JSON | CSV |
|---------|------|----------|------|-----|
| Executive Summary | ✅ | ✅ | ✅ | ❌ |
| Workflow-Level Findings | ✅ | ✅ | ✅ | ❌ |
| Remediation Recommendations | ✅ | ✅ | ✅ | ❌ |
| Visual Styling | ✅ | ⚠️ | ❌ | ❌ |
| Machine Readable | ❌ | ⚠️ | ✅ | ✅ |
| GitHub Compatible | ⚠️ | ✅ | ❌ | ❌ |
| Print Friendly | ✅ | ❌ | ❌ | ❌ |
| Spreadsheet Import | ❌ | ❌ | ⚠️ | ✅ |
| API Integration | ❌ | ❌ | ✅ | ⚠️ |
| Risk Distribution | ✅ | ✅ | ✅ | ❌ |
| Top Issues | ✅ | ✅ | ✅ | ❌ |

✅ Full support | ⚠️ Partial support | ❌ Not supported

## Output Directory

By default, reports are saved to the `reports/` directory:
```
reports/
├── report.html
├── report.md
├── report.json
└── report.csv
```

Customize the output directory:
```bash
actionsguard scan --user USERNAME --output ./custom-reports
```

## Example Workflows

### Security Team Report
Generate comprehensive HTML report for stakeholder presentation:
```bash
actionsguard scan --org my-company --format html
open reports/report.html
```

### Developer Documentation
Add Markdown report to repository wiki:
```bash
actionsguard scan --org my-company --format markdown
cp reports/report.md wiki/Security-Audit.md
git add wiki/Security-Audit.md
git commit -m "Add security scan results"
```

### Automated Monitoring
Integrate JSON output with security dashboard:
```bash
actionsguard scan --org my-company --format json
python scripts/upload_to_dashboard.py reports/report.json
```

### Bulk Analysis
Export to CSV for spreadsheet analysis:
```bash
actionsguard scan --org my-company --format csv
# Open reports/report.csv in Excel/Google Sheets
```

## Report Data Structure

All reports contain the same underlying data:

1. **Executive Summary**
   - Total repositories scanned
   - Average security score
   - Risk distribution (Critical/High/Medium/Low)
   - Top security issues across organization
   - Scan duration

2. **Per-Repository Results**
   - Repository name and URL
   - Overall security score (0-10)
   - Risk level classification
   - Scan timestamp
   - Error details (if scan failed)

3. **Per-Workflow Analysis** (HTML, Markdown, JSON only)
   - Workflow file path
   - Security findings for each workflow
   - Severity levels for each finding
   - Line numbers (when available)
   - Detailed remediation recommendations

4. **Check Results**
   - Check name (e.g., "Dangerous-Workflow")
   - Score (0-10)
   - Status (PASS/WARN/FAIL)
   - Reason for failure
   - Documentation links

## Further Reading

- [JSON Schema Documentation](./json_schema.md) - Complete JSON format specification
- [Scorecard Checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md) - Understanding security checks
- [ActionsGuard CLI Reference](../README.md) - Complete CLI documentation
