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
