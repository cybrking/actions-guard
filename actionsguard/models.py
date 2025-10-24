"""Data models for ActionsGuard scan results."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class Severity(str, Enum):
    """Security severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Status(str, Enum):
    """Check status."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIP = "SKIP"


class RiskLevel(str, Enum):
    """Overall risk level."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class WorkflowFinding:
    """A specific security finding in a workflow file."""

    workflow_path: str  # e.g., ".github/workflows/ci.yml"
    check_name: str  # e.g., "Dangerous-Workflow"
    severity: Severity
    message: str  # Description of the issue
    line_number: Optional[int] = None
    snippet: Optional[str] = None  # Code snippet showing the issue
    recommendation: Optional[str] = None  # How to fix it

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_path": self.workflow_path,
            "check_name": self.check_name,
            "severity": self.severity.value,
            "message": self.message,
            "line_number": self.line_number,
            "snippet": self.snippet,
            "recommendation": self.recommendation,
        }


@dataclass
class WorkflowAnalysis:
    """Security analysis for a single workflow file."""

    path: str  # e.g., ".github/workflows/ci.yml"
    findings: List[WorkflowFinding] = field(default_factory=list)
    score: Optional[float] = None  # Individual workflow score if calculable

    def get_critical_count(self) -> int:
        """Count critical severity findings."""
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    def get_high_count(self) -> int:
        """Count high severity findings."""
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    def get_medium_count(self) -> int:
        """Count medium severity findings."""
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)

    def get_low_count(self) -> int:
        """Count low severity findings."""
        return sum(1 for f in self.findings if f.severity == Severity.LOW)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": self.path,
            "findings": [f.to_dict() for f in self.findings],
            "score": self.score,
            "critical_count": self.get_critical_count(),
            "high_count": self.get_high_count(),
            "medium_count": self.get_medium_count(),
            "low_count": self.get_low_count(),
        }


@dataclass
class CheckResult:
    """Result for a single security check."""

    name: str
    score: int  # 0-10
    status: Status
    reason: str
    documentation_url: str
    severity: Severity
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["status"] = self.status.value
        result["severity"] = self.severity.value
        return result

    @staticmethod
    def calculate_severity(score: int) -> Severity:
        """
        Calculate severity based on score.

        Args:
            score: Score from 0-10

        Returns:
            Severity level
        """
        if score >= 8:
            return Severity.INFO
        elif score >= 6:
            return Severity.LOW
        elif score >= 4:
            return Severity.MEDIUM
        elif score >= 2:
            return Severity.HIGH
        else:
            return Severity.CRITICAL


@dataclass
class ScanResult:
    """Result for a single repository scan."""

    repo_name: str
    repo_url: str
    score: float
    risk_level: RiskLevel
    scan_date: datetime
    checks: List[CheckResult] = field(default_factory=list)
    workflows: List[WorkflowAnalysis] = field(default_factory=list)  # NEW: Per-workflow findings
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "repo_name": self.repo_name,
            "repo_url": self.repo_url,
            "score": self.score,
            "risk_level": self.risk_level.value,
            "scan_date": self.scan_date.isoformat(),
            "checks": [check.to_dict() for check in self.checks],
            "workflows": [workflow.to_dict() for workflow in self.workflows],
            "metadata": self.metadata,
            "error": self.error,
        }

    @staticmethod
    def calculate_risk_level(score: float) -> RiskLevel:
        """
        Calculate risk level based on overall score.

        Args:
            score: Overall score from 0.0-10.0

        Returns:
            Risk level
        """
        if score >= 8.0:
            return RiskLevel.LOW
        elif score >= 6.0:
            return RiskLevel.MEDIUM
        elif score >= 4.0:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    def get_severity_counts(self) -> Dict[str, int]:
        """Get count of checks by severity."""
        counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFO": 0,
        }
        for check in self.checks:
            counts[check.severity.value] += 1
        return counts

    def has_critical_issues(self) -> bool:
        """Check if scan has critical issues."""
        return any(
            check.severity == Severity.CRITICAL and check.status == Status.FAIL
            for check in self.checks
        )


@dataclass
class ScanSummary:
    """Summary across multiple repositories."""

    total_repos: int
    successful_scans: int
    failed_scans: int
    average_score: float
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    results: List[ScanResult] = field(default_factory=list)
    scan_duration: Optional[float] = None

    def get_executive_summary(self) -> Dict[str, Any]:
        """
        Generate executive summary statistics.

        Returns:
            Dict with executive-level metrics
        """
        # Risk distribution
        risk_distribution = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }
        for result in self.results:
            if result.error is None:
                risk_distribution[result.risk_level.value] += 1

        # Issue frequency analysis
        issue_types = {}
        repos_affected_by_issue = {}

        for result in self.results:
            if result.error:
                continue
            for check in result.checks:
                check_name = check.name
                if check_name not in issue_types:
                    issue_types[check_name] = {
                        "count": 0,
                        "repos_affected": set(),
                        "max_severity": check.severity,
                    }

                if check.status == Status.FAIL or check.score < 7:
                    issue_types[check_name]["count"] += 1
                    issue_types[check_name]["repos_affected"].add(result.repo_name)

                    # Track highest severity
                    current_sev = issue_types[check_name]["max_severity"]
                    if self._severity_rank(check.severity) > self._severity_rank(current_sev):
                        issue_types[check_name]["max_severity"] = check.severity

        # Convert sets to counts and sort by frequency
        top_issues = []
        for issue_name, data in issue_types.items():
            if data["count"] > 0:
                top_issues.append({
                    "name": issue_name,
                    "instances": data["count"],
                    "repos_affected": len(data["repos_affected"]),
                    "severity": data["max_severity"].value,
                })

        top_issues.sort(key=lambda x: (x["instances"], x["repos_affected"]), reverse=True)

        return {
            "total_repositories": self.total_repos,
            "successful_scans": self.successful_scans,
            "failed_scans": self.failed_scans,
            "average_score": self.average_score,
            "scan_duration": self.scan_duration,
            "risk_distribution": risk_distribution,
            "issue_counts": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "total": self.critical_count + self.high_count + self.medium_count + self.low_count,
            },
            "top_issues": top_issues[:10],  # Top 10 most common issues
        }

    @staticmethod
    def _severity_rank(severity: Severity) -> int:
        """Rank severity for comparison."""
        ranks = {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MEDIUM: 2,
            Severity.LOW: 1,
            Severity.INFO: 0,
        }
        return ranks.get(severity, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_repos": self.total_repos,
            "successful_scans": self.successful_scans,
            "failed_scans": self.failed_scans,
            "average_score": self.average_score,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "scan_duration": self.scan_duration,
            "executive_summary": self.get_executive_summary(),
            "results": [result.to_dict() for result in self.results],
        }

    @staticmethod
    def from_results(results: List[ScanResult], scan_duration: Optional[float] = None) -> "ScanSummary":
        """
        Create summary from list of scan results.

        Args:
            results: List of scan results
            scan_duration: Total scan duration in seconds

        Returns:
            ScanSummary instance
        """
        successful = [r for r in results if r.error is None]
        failed = [r for r in results if r.error is not None]

        avg_score = (
            sum(r.score for r in successful) / len(successful)
            if successful
            else 0.0
        )

        # Count severity across all checks
        critical = 0
        high = 0
        medium = 0
        low = 0

        for result in successful:
            counts = result.get_severity_counts()
            critical += counts["CRITICAL"]
            high += counts["HIGH"]
            medium += counts["MEDIUM"]
            low += counts["LOW"]

        return ScanSummary(
            total_repos=len(results),
            successful_scans=len(successful),
            failed_scans=len(failed),
            average_score=round(avg_score, 2),
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            results=results,
            scan_duration=scan_duration,
        )
