"""Tests for data models."""

import pytest
from datetime import datetime

from actionsguard.models import (
    CheckResult,
    ScanResult,
    ScanSummary,
    Severity,
    Status,
    RiskLevel,
)


def test_check_result_creation():
    """Test CheckResult creation."""
    check = CheckResult(
        name="Dangerous-Workflow",
        score=5,
        status=Status.WARN,
        reason="Potential issues found",
        documentation_url="https://example.com",
        severity=Severity.MEDIUM,
    )

    assert check.name == "Dangerous-Workflow"
    assert check.score == 5
    assert check.status == Status.WARN
    assert check.severity == Severity.MEDIUM


def test_check_result_to_dict():
    """Test CheckResult serialization."""
    check = CheckResult(
        name="Test",
        score=8,
        status=Status.PASS,
        reason="All good",
        documentation_url="https://example.com",
        severity=Severity.LOW,
    )

    result = check.to_dict()
    assert result["name"] == "Test"
    assert result["score"] == 8
    assert result["status"] == "PASS"
    assert result["severity"] == "LOW"


def test_severity_calculation():
    """Test severity calculation from score."""
    assert CheckResult.calculate_severity(9) == Severity.INFO
    assert CheckResult.calculate_severity(7) == Severity.LOW
    assert CheckResult.calculate_severity(5) == Severity.MEDIUM
    assert CheckResult.calculate_severity(3) == Severity.HIGH
    assert CheckResult.calculate_severity(1) == Severity.CRITICAL


def test_scan_result_creation():
    """Test ScanResult creation."""
    result = ScanResult(
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        score=7.5,
        risk_level=RiskLevel.LOW,
        scan_date=datetime.now(),
        checks=[],
    )

    assert result.repo_name == "owner/repo"
    assert result.score == 7.5
    assert result.risk_level == RiskLevel.LOW


def test_risk_level_calculation():
    """Test risk level calculation from score."""
    assert ScanResult.calculate_risk_level(9.0) == RiskLevel.LOW
    assert ScanResult.calculate_risk_level(7.0) == RiskLevel.MEDIUM
    assert ScanResult.calculate_risk_level(5.0) == RiskLevel.HIGH
    assert ScanResult.calculate_risk_level(2.0) == RiskLevel.CRITICAL


def test_scan_result_has_critical_issues():
    """Test detection of critical issues."""
    check1 = CheckResult(
        name="Test1",
        score=2,
        status=Status.FAIL,
        reason="Critical issue",
        documentation_url="",
        severity=Severity.CRITICAL,
    )

    check2 = CheckResult(
        name="Test2",
        score=8,
        status=Status.PASS,
        reason="OK",
        documentation_url="",
        severity=Severity.INFO,
    )

    result = ScanResult(
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        score=5.0,
        risk_level=RiskLevel.HIGH,
        scan_date=datetime.now(),
        checks=[check1, check2],
    )

    assert result.has_critical_issues() is True


def test_scan_summary_from_results():
    """Test ScanSummary creation from results."""
    result1 = ScanResult(
        repo_name="owner/repo1",
        repo_url="https://github.com/owner/repo1",
        score=8.0,
        risk_level=RiskLevel.LOW,
        scan_date=datetime.now(),
        checks=[],
    )

    result2 = ScanResult(
        repo_name="owner/repo2",
        repo_url="https://github.com/owner/repo2",
        score=6.0,
        risk_level=RiskLevel.MEDIUM,
        scan_date=datetime.now(),
        checks=[],
    )

    summary = ScanSummary.from_results([result1, result2])

    assert summary.total_repos == 2
    assert summary.successful_scans == 2
    assert summary.failed_scans == 0
    assert summary.average_score == 7.0
