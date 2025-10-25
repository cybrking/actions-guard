# ActionsGuard JSON Report Schema

Version: 1.0.0

## Overview

The JSON report format provides complete scan results in a machine-readable format suitable for:
- Integration with security dashboards
- Automated analysis and alerting
- Data warehousing and trend analysis
- Custom reporting tools

## Root Structure

```json
{
  "schema_version": "1.0.0",
  "tool": "ActionsGuard",
  "report_type": "security_scan",
  "generated_at": "2025-10-25T14:30:00.123456",
  "summary": {
    // ScanSummary object (see below)
  }
}
```

## ScanSummary Object

```json
{
  "total_repos": 5,
  "successful_scans": 5,
  "failed_scans": 0,
  "average_score": 7.2,
  "critical_count": 3,
  "high_count": 8,
  "medium_count": 12,
  "low_count": 5,
  "scan_duration": 45.3,
  "executive_summary": {
    // Executive summary (see below)
  },
  "results": [
    // Array of ScanResult objects (see below)
  ]
}
```

## Executive Summary

```json
{
  "total_repositories": 5,
  "successful_scans": 5,
  "failed_scans": 0,
  "average_score": 7.2,
  "scan_duration": 45.3,
  "risk_distribution": {
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 1,
    "LOW": 1
  },
  "issue_counts": {
    "critical": 3,
    "high": 8,
    "medium": 12,
    "low": 5,
    "total": 28
  },
  "top_issues": [
    {
      "name": "Dangerous-Workflow",
      "instances": 8,
      "repos_affected": 3,
      "severity": "HIGH"
    },
    {
      "name": "Token-Permissions",
      "instances": 5,
      "repos_affected": 4,
      "severity": "MEDIUM"
    }
  ]
}
```

## ScanResult Object (Per Repository)

```json
{
  "repo_name": "owner/repo",
  "repo_url": "https://github.com/owner/repo",
  "score": 6.5,
  "risk_level": "MEDIUM",
  "scan_date": "2025-10-25T14:30:00.123456",
  "checks": [
    // Array of CheckResult objects (see below)
  ],
  "workflows": [
    // Array of WorkflowAnalysis objects (see below)
  ],
  "metadata": {
    "has_workflows": true,
    "scorecard_version": "v4.13.1"
  },
  "error": null
}
```

## CheckResult Object

```json
{
  "name": "Dangerous-Workflow",
  "score": 5,
  "status": "WARN",
  "reason": "pull_request_target workflow detected",
  "documentation_url": "https://github.com/ossf/scorecard/blob/main/docs/checks.md#dangerous-workflow",
  "severity": "HIGH",
  "details": {
    // Optional check-specific details
  }
}
```

## WorkflowAnalysis Object

```json
{
  "path": ".github/workflows/ci.yml",
  "score": null,
  "critical_count": 1,
  "high_count": 2,
  "medium_count": 0,
  "low_count": 1,
  "findings": [
    // Array of WorkflowFinding objects (see below)
  ]
}
```

## WorkflowFinding Object

```json
{
  "workflow_path": ".github/workflows/ci.yml",
  "check_name": "Dangerous-Workflow",
  "severity": "CRITICAL",
  "message": "pull_request_target workflow with code checkout detected",
  "line_number": 12,
  "snippet": "on: pull_request_target",
  "recommendation": "Replace 'pull_request_target' with 'pull_request' trigger. If you must use pull_request_target, add explicit permission checks and avoid checking out PR code."
}
```

## Field Definitions

### Severity Levels
- `CRITICAL`: Immediate security risk requiring urgent remediation
- `HIGH`: Significant security risk
- `MEDIUM`: Moderate security concern
- `LOW`: Minor security improvement opportunity
- `INFO`: Informational finding

### Status Values
- `PASS`: Check passed successfully
- `WARN`: Check passed but with warnings
- `FAIL`: Check failed
- `ERROR`: Check could not be completed
- `SKIP`: Check was skipped

### Risk Levels (Repository-level)
- `CRITICAL`: Score < 4.0
- `HIGH`: Score 4.0-5.9
- `MEDIUM`: Score 6.0-7.9
- `LOW`: Score >= 8.0

## Example Use Cases

### 1. Extract All Critical Findings

```python
import json

with open('report.json') as f:
    report = json.load(f)

for repo in report['summary']['results']:
    for workflow in repo['workflows']:
        for finding in workflow['findings']:
            if finding['severity'] == 'CRITICAL':
                print(f"{repo['repo_name']} - {workflow['path']}: {finding['message']}")
```

### 2. Generate Risk Dashboard Data

```python
risk_dist = report['summary']['executive_summary']['risk_distribution']
print(f"Critical repos: {risk_dist['CRITICAL']}")
print(f"High risk repos: {risk_dist['HIGH']}")
```

### 3. Extract Top Issues for Reporting

```python
top_issues = report['summary']['executive_summary']['top_issues']
for issue in top_issues[:5]:
    print(f"{issue['name']}: {issue['instances']} instances across {issue['repos_affected']} repos")
```

## Schema Evolution

Future versions may add additional fields while maintaining backward compatibility. Consumers should:
- Check `schema_version` field to determine report format
- Ignore unknown fields for forward compatibility
- Use `executive_summary` for high-level metrics
- Use `results[].workflows` for detailed per-workflow findings
