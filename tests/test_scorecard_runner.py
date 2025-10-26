"""Tests for ScorecardRunner class."""

import pytest
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock

from actionsguard.scorecard_runner import ScorecardRunner
from actionsguard.models import CheckResult, Status, Severity


@pytest.fixture
def runner():
    """Create a ScorecardRunner instance without checking installation."""
    return ScorecardRunner(timeout=300, check_install=False)


@pytest.fixture
def sample_scorecard_output():
    """Create sample Scorecard JSON output."""
    return {
        "date": "2024-01-15",
        "repo": {
            "name": "github.com/owner/repo",
            "commit": "abc123def456"
        },
        "scorecard": {
            "version": "v4.13.1",
            "commit": "xyz789"
        },
        "score": 7.5,
        "checks": [
            {
                "name": "Dangerous-Workflow",
                "score": 10,
                "reason": "No dangerous workflow patterns found",
                "documentation": {
                    "url": "https://github.com/ossf/scorecard/blob/main/docs/checks.md#dangerous-workflow",
                    "short": "Determines if the project's GitHub Action workflows avoid dangerous patterns."
                },
                "details": []
            },
            {
                "name": "Token-Permissions",
                "score": 0,
                "reason": "non read-only tokens detected in GitHub workflows",
                "documentation": {
                    "url": "https://github.com/ossf/scorecard/blob/main/docs/checks.md#token-permissions",
                    "short": "Determines if the project's workflows follow the principle of least privilege."
                },
                "details": [
                    {
                        "msg": "no token permissions found",
                        "path": ".github/workflows/ci.yml",
                        "type": "Warn"
                    }
                ]
            },
            {
                "name": "Code-Review",
                "score": -1,
                "reason": "no pull request found",
                "documentation": {
                    "url": "https://github.com/ossf/scorecard/blob/main/docs/checks.md#code-review"
                },
                "details": []
            },
            {
                "name": "Vulnerabilities",
                "score": 8,
                "reason": "1 existing vulnerabilities detected",
                "documentation": {
                    "url": "https://github.com/ossf/scorecard/blob/main/docs/checks.md#vulnerabilities"
                },
                "details": []
            }
        ]
    }


def test_runner_initialization_no_check():
    """Test runner initialization without installation check."""
    runner = ScorecardRunner(timeout=600, check_install=False)
    assert runner.timeout == 600


def test_runner_initialization_with_check():
    """Test runner initialization with installation check."""
    with patch('shutil.which', return_value='/usr/bin/scorecard'):
        runner = ScorecardRunner(timeout=300, check_install=True)
        assert runner.timeout == 300


def test_runner_initialization_not_installed():
    """Test runner initialization when scorecard is not installed."""
    with patch('shutil.which', return_value=None):
        with pytest.raises(RuntimeError, match="OpenSSF Scorecard not found"):
            ScorecardRunner(timeout=300, check_install=True)


def test_run_scorecard_successful(runner, sample_scorecard_output):
    """Test successful scorecard execution."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(sample_scorecard_output)
    mock_result.stderr = ""

    with patch('subprocess.run', return_value=mock_result) as mock_run:
        result = runner.run_scorecard(
            repo_url="https://github.com/owner/repo",
            checks=["Dangerous-Workflow", "Token-Permissions"],
            github_token="ghp_test_token"
        )

        assert result == sample_scorecard_output

        # Verify command was constructed correctly
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "scorecard" in cmd
        assert "--repo=https://github.com/owner/repo" in cmd
        assert "--format=json" in cmd
        assert "--show-details" in cmd
        assert "--checks=Dangerous-Workflow" in cmd
        assert "--checks=Token-Permissions" in cmd

        # Verify environment variables
        env = call_args[1]['env']
        assert env['GITHUB_TOKEN'] == "ghp_test_token"
        assert env['GITHUB_AUTH_TOKEN'] == "ghp_test_token"


def test_run_scorecard_all_checks(runner, sample_scorecard_output):
    """Test running scorecard with all checks."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(sample_scorecard_output)

    with patch('subprocess.run', return_value=mock_result) as mock_run:
        result = runner.run_scorecard(repo_url="owner/repo", checks=None)

        # Verify no --checks flag when running all checks
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--checks=" not in ' '.join(cmd)


def test_run_scorecard_without_token(runner, sample_scorecard_output):
    """Test running scorecard without GitHub token."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(sample_scorecard_output)

    with patch('subprocess.run', return_value=mock_result) as mock_run:
        runner.run_scorecard(repo_url="owner/repo", github_token=None)

        # Should not have GITHUB_TOKEN in additional env
        # (but will inherit from parent process)
        call_args = mock_run.call_args
        env_additions = {k: v for k, v in call_args[1]['env'].items()
                        if k not in subprocess.os.environ}
        assert 'GITHUB_TOKEN' not in env_additions


def test_run_scorecard_execution_failure(runner):
    """Test scorecard execution failure."""
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error: repository not found"

    with patch('subprocess.run', return_value=mock_result):
        with pytest.raises(RuntimeError, match="Scorecard execution failed"):
            runner.run_scorecard(repo_url="owner/nonexistent")


def test_run_scorecard_timeout(runner):
    """Test scorecard timeout."""
    with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('scorecard', 300)):
        with pytest.raises(TimeoutError, match="timed out after 300 seconds"):
            runner.run_scorecard(repo_url="owner/repo")


def test_run_scorecard_invalid_json(runner):
    """Test scorecard with invalid JSON output."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Not valid JSON"

    with patch('subprocess.run', return_value=mock_result):
        with pytest.raises(RuntimeError, match="Failed to parse scorecard output"):
            runner.run_scorecard(repo_url="owner/repo")


def test_parse_results(runner, sample_scorecard_output):
    """Test parsing scorecard results."""
    checks = runner.parse_results(sample_scorecard_output)

    assert len(checks) == 4

    # Test first check (Dangerous-Workflow)
    dangerous_check = checks[0]
    assert dangerous_check.name == "Dangerous-Workflow"
    assert dangerous_check.score == 10
    assert dangerous_check.status == Status.PASS
    assert dangerous_check.reason == "No dangerous workflow patterns found"
    assert dangerous_check.severity == Severity.INFO  # score 10 -> INFO
    assert "dangerous-workflow" in dangerous_check.documentation_url.lower()

    # Test second check (Token-Permissions)
    token_check = checks[1]
    assert token_check.name == "Token-Permissions"
    assert token_check.score == 0
    assert token_check.status == Status.FAIL
    assert token_check.severity == Severity.CRITICAL
    assert len(token_check.details["details"]) == 1

    # Test skipped check (Code-Review)
    review_check = checks[2]
    assert review_check.name == "Code-Review"
    assert review_check.score == 0  # -1 converted to 0
    assert review_check.status == Status.SKIP

    # Test warning check (Vulnerabilities)
    vuln_check = checks[3]
    assert vuln_check.name == "Vulnerabilities"
    assert vuln_check.score == 8
    assert vuln_check.status == Status.PASS


def test_parse_results_score_mapping(runner):
    """Test score to status mapping."""
    scorecard_data = {
        "checks": [
            {"name": "Check1", "score": 10, "reason": "Perfect", "documentation": {"url": ""}},
            {"name": "Check2", "score": 8, "reason": "Good", "documentation": {"url": ""}},
            {"name": "Check3", "score": 7, "reason": "Acceptable", "documentation": {"url": ""}},
            {"name": "Check4", "score": 6, "reason": "Warning", "documentation": {"url": ""}},
            {"name": "Check5", "score": 4, "reason": "Warning", "documentation": {"url": ""}},
            {"name": "Check6", "score": 3, "reason": "Failing", "documentation": {"url": ""}},
            {"name": "Check7", "score": 0, "reason": "Critical", "documentation": {"url": ""}},
            {"name": "Check8", "score": -1, "reason": "Skipped", "documentation": {"url": ""}},
        ]
    }

    checks = runner.parse_results(scorecard_data)

    # score >= 7 -> PASS
    assert checks[0].status == Status.PASS  # 10
    assert checks[1].status == Status.PASS  # 8
    assert checks[2].status == Status.PASS  # 7

    # 4 <= score < 7 -> WARN
    assert checks[3].status == Status.WARN  # 6
    assert checks[4].status == Status.WARN  # 4

    # score < 4 -> FAIL
    assert checks[5].status == Status.FAIL  # 3
    assert checks[6].status == Status.FAIL  # 0

    # score == -1 -> SKIP
    assert checks[7].status == Status.SKIP  # -1


def test_parse_results_severity_calculation(runner):
    """Test severity calculation based on scores."""
    scorecard_data = {
        "checks": [
            {"name": "Critical", "score": 0, "reason": "", "documentation": {"url": ""}},
            {"name": "High", "score": 3, "reason": "", "documentation": {"url": ""}},
            {"name": "Medium", "score": 6, "reason": "", "documentation": {"url": ""}},
            {"name": "Low", "score": 9, "reason": "", "documentation": {"url": ""}},
            {"name": "Skipped", "score": -1, "reason": "", "documentation": {"url": ""}},
        ]
    }

    checks = runner.parse_results(scorecard_data)

    # CheckResult.calculate_severity mapping:
    # 8-10: INFO, 6-7: LOW, 4-5: MEDIUM, 2-3: HIGH, 0-1: CRITICAL
    assert checks[0].severity == Severity.CRITICAL  # score 0
    assert checks[1].severity == Severity.HIGH  # score 3
    assert checks[2].severity == Severity.LOW  # score 6
    assert checks[3].severity == Severity.INFO  # score 9
    # For skipped (-1), it uses score 10 for severity calculation
    assert checks[4].severity == Severity.INFO  # skipped uses 10 -> INFO


def test_parse_results_with_details(runner):
    """Test parsing results preserves details."""
    scorecard_data = {
        "checks": [
            {
                "name": "Test-Check",
                "score": 5,
                "reason": "Some issues found",
                "documentation": {
                    "url": "https://example.com",
                    "short": "Short description"
                },
                "details": [
                    {"msg": "Issue 1", "type": "Warn"},
                    {"msg": "Issue 2", "type": "Info"}
                ]
            }
        ]
    }

    checks = runner.parse_results(scorecard_data)

    assert len(checks) == 1
    assert checks[0].details["short"] == "Short description"
    assert len(checks[0].details["details"]) == 2
    assert checks[0].details["details"][0]["msg"] == "Issue 1"


def test_get_overall_score(runner, sample_scorecard_output):
    """Test extracting overall score."""
    score = runner.get_overall_score(sample_scorecard_output)
    assert score == 7.5


def test_get_overall_score_missing(runner):
    """Test extracting overall score when missing."""
    score = runner.get_overall_score({})
    assert score == 0.0


def test_get_overall_score_as_int(runner):
    """Test extracting overall score when it's an integer."""
    score = runner.get_overall_score({"score": 8})
    assert score == 8.0
    assert isinstance(score, float)


def test_get_metadata(runner, sample_scorecard_output):
    """Test extracting metadata."""
    metadata = runner.get_metadata(sample_scorecard_output)

    assert metadata["scorecard_version"] == "v4.13.1"
    assert metadata["scorecard_commit"] == "xyz789"
    assert metadata["repo"] == "github.com/owner/repo"
    assert metadata["commit"] == "abc123def456"
    assert metadata["scan_timestamp"] == "2024-01-15"


def test_get_metadata_missing_fields(runner):
    """Test extracting metadata with missing fields."""
    metadata = runner.get_metadata({})

    assert metadata["scorecard_version"] == "unknown"
    assert metadata["scorecard_commit"] == "unknown"
    assert metadata["repo"] == ""
    assert metadata["commit"] == ""
    # scan_timestamp should have a default value
    assert "scan_timestamp" in metadata


def test_get_metadata_partial_data(runner):
    """Test extracting metadata with partial data."""
    partial_data = {
        "scorecard": {"version": "v4.0.0"},
        "repo": {"name": "test/repo"}
    }

    metadata = runner.get_metadata(partial_data)

    assert metadata["scorecard_version"] == "v4.0.0"
    assert metadata["scorecard_commit"] == "unknown"
    assert metadata["repo"] == "test/repo"
    assert metadata["commit"] == ""


def test_parse_results_empty_checks(runner):
    """Test parsing results with no checks."""
    checks = runner.parse_results({"checks": []})
    assert checks == []


def test_parse_results_missing_optional_fields(runner):
    """Test parsing results with missing optional fields."""
    scorecard_data = {
        "checks": [
            {
                "name": "Minimal-Check",
                "score": 5,
                # Missing reason, documentation, details
            }
        ]
    }

    checks = runner.parse_results(scorecard_data)

    assert len(checks) == 1
    assert checks[0].name == "Minimal-Check"
    assert checks[0].score == 5
    assert checks[0].reason == "No reason provided"
    assert checks[0].documentation_url == ""
    assert checks[0].details["short"] == ""
    assert checks[0].details["details"] == []


def test_run_scorecard_command_construction(runner):
    """Test scorecard command is constructed correctly."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = '{"score": 5.0, "checks": []}'

    with patch('subprocess.run', return_value=mock_result) as mock_run:
        runner.run_scorecard(
            repo_url="github.com/test/repo",
            checks=["Check1", "Check2", "Check3"],
            github_token="token123"
        )

        cmd = mock_run.call_args[0][0]

        # Verify all components
        assert cmd[0] == "scorecard"
        assert "--repo=github.com/test/repo" in cmd
        assert "--format=json" in cmd
        assert "--show-details" in cmd
        assert "--checks=Check1" in cmd
        assert "--checks=Check2" in cmd
        assert "--checks=Check3" in cmd


def test_runner_timeout_parameter(runner):
    """Test that timeout is passed to subprocess."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = '{"score": 5.0, "checks": []}'

    with patch('subprocess.run', return_value=mock_result) as mock_run:
        runner.run_scorecard(repo_url="test/repo")

        # Verify timeout was passed
        assert mock_run.call_args[1]['timeout'] == 300


def test_custom_timeout():
    """Test runner with custom timeout."""
    runner = ScorecardRunner(timeout=600, check_install=False)

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = '{"score": 5.0, "checks": []}'

    with patch('subprocess.run', return_value=mock_result) as mock_run:
        runner.run_scorecard(repo_url="test/repo")

        # Verify custom timeout was used
        assert mock_run.call_args[1]['timeout'] == 600
