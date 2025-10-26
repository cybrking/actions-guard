"""Tests for CLI interface."""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from actionsguard.cli import cli
from actionsguard.models import ScanResult, ScanSummary, RiskLevel, CheckResult, Status, Severity


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_scan_result():
    """Create a mock scan result."""
    return ScanResult(
        repo_name="owner/test-repo",
        repo_url="https://github.com/owner/test-repo",
        score=7.5,
        risk_level=RiskLevel.MEDIUM,
        scan_date=datetime.now(),
        checks=[
            CheckResult(
                name="Test-Check",
                score=7,
                status=Status.PASS,
                reason="Test passed",
                documentation_url="https://example.com",
                severity=Severity.LOW,
            )
        ],
        metadata={"has_workflows": True},
    )


@pytest.fixture
def mock_scan_summary(mock_scan_result):
    """Create a mock scan summary."""
    return ScanSummary.from_results([mock_scan_result], scan_duration=10.0)


def test_cli_version(runner):
    """Test version command."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "actionsguard" in result.output.lower()


def test_cli_help(runner):
    """Test help command."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "ActionsGuard" in result.output


def test_cli_verbose_flag(runner):
    """Test verbose flag."""
    result = runner.invoke(cli, ["--verbose", "--help"])
    assert result.exit_code == 0


def test_cli_json_logs_flag(runner):
    """Test JSON logs flag."""
    result = runner.invoke(cli, ["--json-logs", "--help"])
    assert result.exit_code == 0


def test_scan_help(runner):
    """Test scan command help."""
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--repo" in result.output
    assert "--org" in result.output
    assert "--user" in result.output


def test_scan_missing_arguments(runner):
    """Test scan without required arguments."""
    result = runner.invoke(cli, ["scan"])
    assert result.exit_code == 2
    assert "Error" in result.output


def test_scan_both_repo_and_org(runner):
    """Test scan with both repo and org (should fail)."""
    result = runner.invoke(
        cli,
        ["scan", "--repo", "owner/repo", "--org", "org-name"]
    )
    assert result.exit_code == 2
    assert "Error" in result.output


def test_scan_all_three_sources(runner):
    """Test scan with repo, org, and user (should fail)."""
    result = runner.invoke(
        cli,
        ["scan", "--repo", "owner/repo", "--org", "org", "--user", "user"]
    )
    assert result.exit_code == 2
    assert "Error" in result.output


def test_scan_single_repo_success(runner, mock_scan_summary):
    """Test successful scan of a single repository."""
    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_single_repository.return_value = mock_scan_summary.results[0]
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter') as mock_json:
            with patch('actionsguard.cli.HTMLReporter') as mock_html:
                with patch('actionsguard.cli.CSVReporter') as mock_csv:
                    with patch('actionsguard.cli.MarkdownReporter') as mock_md:
                        # Setup reporters
                        mock_json.return_value.generate_report.return_value = Path("/tmp/report.json")
                        mock_html.return_value.generate_report.return_value = Path("/tmp/report.html")
                        mock_csv.return_value.generate_report.return_value = Path("/tmp/report.csv")
                        mock_md.return_value.generate_report.return_value = Path("/tmp/report.md")

                        result = runner.invoke(
                            cli,
                            ["scan", "--repo", "owner/test-repo", "--token", "fake_token"]
                        )

                        assert result.exit_code == 0
                        mock_scanner.scan_single_repository.assert_called_once_with("owner/test-repo")


def test_scan_org_success(runner, mock_scan_summary):
    """Test successful scan of an organization."""
    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_organization.return_value = mock_scan_summary
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter'), \
             patch('actionsguard.cli.HTMLReporter'), \
             patch('actionsguard.cli.CSVReporter'), \
             patch('actionsguard.cli.MarkdownReporter'):

            result = runner.invoke(
                cli,
                ["scan", "--org", "test-org", "--token", "fake_token"]
            )

            assert result.exit_code == 0
            mock_scanner.scan_organization.assert_called_once()
            call_args = mock_scanner.scan_organization.call_args
            assert call_args[1]['org_name'] == "test-org"


def test_scan_user_success(runner, mock_scan_summary):
    """Test successful scan of a user account."""
    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_user.return_value = mock_scan_summary
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter'), \
             patch('actionsguard.cli.HTMLReporter'), \
             patch('actionsguard.cli.CSVReporter'), \
             patch('actionsguard.cli.MarkdownReporter'):

            result = runner.invoke(
                cli,
                ["scan", "--user", "test-user", "--token", "fake_token"]
            )

            assert result.exit_code == 0
            mock_scanner.scan_user.assert_called_once()


def test_scan_with_exclude_filter(runner, mock_scan_summary):
    """Test scan with exclude filter."""
    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_organization.return_value = mock_scan_summary
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter'), \
             patch('actionsguard.cli.HTMLReporter'), \
             patch('actionsguard.cli.CSVReporter'), \
             patch('actionsguard.cli.MarkdownReporter'):

            result = runner.invoke(
                cli,
                ["scan", "--org", "test-org", "--exclude", "repo1,repo2", "--token", "fake_token"]
            )

            assert result.exit_code == 0
            call_args = mock_scanner.scan_organization.call_args
            assert call_args[1]['exclude'] == ["repo1", "repo2"]


def test_scan_with_only_filter(runner, mock_scan_summary):
    """Test scan with only filter."""
    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_organization.return_value = mock_scan_summary
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter'), \
             patch('actionsguard.cli.HTMLReporter'), \
             patch('actionsguard.cli.CSVReporter'), \
             patch('actionsguard.cli.MarkdownReporter'):

            result = runner.invoke(
                cli,
                ["scan", "--org", "test-org", "--only", "important-repo", "--token", "fake_token"]
            )

            assert result.exit_code == 0
            call_args = mock_scanner.scan_organization.call_args
            assert call_args[1]['only'] == ["important-repo"]


def test_scan_with_custom_formats(runner, mock_scan_summary):
    """Test scan with custom output formats."""
    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_single_repository.return_value = mock_scan_summary.results[0]
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter') as mock_json, \
             patch('actionsguard.cli.HTMLReporter') as mock_html:

            mock_json.return_value.generate_report.return_value = Path("/tmp/report.json")
            mock_html.return_value.generate_report.return_value = Path("/tmp/report.html")

            result = runner.invoke(
                cli,
                ["scan", "--repo", "owner/repo", "--format", "json,html", "--token", "fake_token"]
            )

            assert result.exit_code == 0
            # Should only create JSON and HTML reporters
            mock_json.assert_called_once()
            mock_html.assert_called_once()


def test_scan_with_custom_checks(runner, mock_scan_summary):
    """Test scan with custom checks."""
    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_single_repository.return_value = mock_scan_summary.results[0]
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter'), \
             patch('actionsguard.cli.HTMLReporter'), \
             patch('actionsguard.cli.CSVReporter'), \
             patch('actionsguard.cli.MarkdownReporter'):

            result = runner.invoke(
                cli,
                ["scan", "--repo", "owner/repo", "--checks", "Dangerous-Workflow,Token-Permissions", "--token", "fake_token"]
            )

            assert result.exit_code == 0
            # Verify scanner was created with config that has the custom checks
            scanner_init_call = mock_scanner_class.call_args
            config = scanner_init_call[0][0]
            assert config.checks == ["Dangerous-Workflow", "Token-Permissions"]


def test_scan_with_config_file(runner, mock_scan_summary):
    """Test scan with configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
github_token: config_token
output_dir: ./test-reports
formats:
  - json
  - html
checks:
  - Dangerous-Workflow
""")
        config_path = f.name

    try:
        with patch('actionsguard.cli.Scanner') as mock_scanner_class:
            mock_scanner = Mock()
            mock_scanner.scan_single_repository.return_value = mock_scan_summary.results[0]
            mock_scanner_class.return_value = mock_scanner

            with patch('actionsguard.cli.JSONReporter'), \
                 patch('actionsguard.cli.HTMLReporter'), \
                 patch('actionsguard.cli.CSVReporter'), \
                 patch('actionsguard.cli.MarkdownReporter'):

                result = runner.invoke(
                    cli,
                    ["scan", "--repo", "owner/repo", "--config", config_path]
                )

                assert result.exit_code == 0
                assert "Loaded configuration" in result.output
    finally:
        os.unlink(config_path)


def test_scan_with_invalid_config_file(runner):
    """Test scan with invalid configuration file."""
    result = runner.invoke(
        cli,
        ["scan", "--repo", "owner/repo", "--config", "/nonexistent/config.yaml"]
    )

    assert result.exit_code == 2
    # Click validates file existence before our code runs
    assert "does not exist" in result.output or "Error" in result.output


def test_scan_with_fail_on_critical(runner):
    """Test scan with fail-on-critical flag."""
    critical_result = ScanResult(
        repo_name="owner/critical-repo",
        repo_url="https://github.com/owner/critical-repo",
        score=1.0,
        risk_level=RiskLevel.CRITICAL,
        scan_date=datetime.now(),
        checks=[
            CheckResult(
                name="Dangerous-Workflow",
                score=0,
                status=Status.FAIL,
                reason="Critical issue",
                documentation_url="https://example.com",
                severity=Severity.CRITICAL,
            )
        ],
    )

    critical_summary = ScanSummary.from_results([critical_result], scan_duration=10.0)

    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_single_repository.return_value = critical_result
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter'), \
             patch('actionsguard.cli.HTMLReporter'), \
             patch('actionsguard.cli.CSVReporter'), \
             patch('actionsguard.cli.MarkdownReporter'):

            result = runner.invoke(
                cli,
                ["scan", "--repo", "owner/critical-repo", "--fail-on-critical", "--token", "fake_token"]
            )

            # Should exit with error code due to critical findings
            assert result.exit_code == 1


def test_scan_missing_github_token(runner):
    """Test scan without GitHub token."""
    with patch.dict(os.environ, {}, clear=True):
        # Ensure GITHUB_TOKEN is not in environment
        result = runner.invoke(
            cli,
            ["scan", "--repo", "owner/repo"]
        )

        assert result.exit_code == 2
        assert "GitHub token" in result.output or "token" in result.output.lower()


def test_health_command_help(runner):
    """Test health command help."""
    result = runner.invoke(cli, ["health", "--help"])
    assert result.exit_code == 0
    assert "health" in result.output.lower()


def test_health_command_success(runner):
    """Test successful health check."""
    with patch('actionsguard.cli.ScorecardRunner') as mock_scorecard:
        mock_runner = Mock()
        mock_runner.get_version.return_value = "v4.13.1"
        mock_scorecard.return_value = mock_runner

        with patch('actionsguard.github_client.GitHubClient') as mock_gh_class:
            mock_gh = Mock()
            mock_gh.github.get_user.return_value = Mock()
            mock_rate_limit = Mock()
            mock_rate_limit.core.remaining = 5000
            mock_rate_limit.core.limit = 5000
            mock_gh.github.get_rate_limit.return_value = mock_rate_limit

            mock_repo = Mock()
            mock_repo.full_name = "test/repo"
            mock_gh.github.get_user.return_value.get_repos.return_value = [mock_repo]
            mock_gh_class.return_value = mock_gh

            result = runner.invoke(
                cli,
                ["health", "--token", "fake_token"]
            )

            assert result.exit_code == 0
            assert "ready" in result.output.lower() or "✅" in result.output or "✓" in result.output


def test_health_command_scorecard_not_found(runner):
    """Test health check when Scorecard is not installed."""
    with patch('actionsguard.cli.ScorecardRunner') as mock_scorecard:
        mock_scorecard.side_effect = RuntimeError("Scorecard not found")

        result = runner.invoke(cli, ["health"])

        assert result.exit_code == 1
        assert "Scorecard not found" in result.output or "not found" in result.output.lower()


def test_scan_with_include_forks(runner, mock_scan_summary):
    """Test scan with include-forks flag."""
    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_user.return_value = mock_scan_summary
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter'), \
             patch('actionsguard.cli.HTMLReporter'), \
             patch('actionsguard.cli.CSVReporter'), \
             patch('actionsguard.cli.MarkdownReporter'):

            result = runner.invoke(
                cli,
                ["scan", "--user", "test-user", "--include-forks", "--token", "fake_token"]
            )

            assert result.exit_code == 0
            call_args = mock_scanner.scan_user.call_args
            assert call_args[1]['include_forks'] is True


def test_scan_with_custom_output_dir(runner, mock_scan_summary):
    """Test scan with custom output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('actionsguard.cli.Scanner') as mock_scanner_class:
            mock_scanner = Mock()
            mock_scanner.scan_single_repository.return_value = mock_scan_summary.results[0]
            mock_scanner_class.return_value = mock_scanner

            with patch('actionsguard.cli.JSONReporter') as mock_json, \
                 patch('actionsguard.cli.HTMLReporter'), \
                 patch('actionsguard.cli.CSVReporter'), \
                 patch('actionsguard.cli.MarkdownReporter'):

                mock_json.return_value.generate_report.return_value = Path(f"{tmpdir}/report.json")

                result = runner.invoke(
                    cli,
                    ["scan", "--repo", "owner/repo", "--output", tmpdir, "--token", "fake_token"]
                )

                assert result.exit_code == 0
                # Verify output directory was used
                mock_json.assert_called_once_with(tmpdir)


def test_scan_with_parallel_option(runner, mock_scan_summary):
    """Test scan with custom parallel scans."""
    with patch('actionsguard.cli.Scanner') as mock_scanner_class:
        mock_scanner = Mock()
        mock_scanner.scan_organization.return_value = mock_scan_summary
        mock_scanner_class.return_value = mock_scanner

        with patch('actionsguard.cli.JSONReporter'), \
             patch('actionsguard.cli.HTMLReporter'), \
             patch('actionsguard.cli.CSVReporter'), \
             patch('actionsguard.cli.MarkdownReporter'):

            result = runner.invoke(
                cli,
                ["scan", "--org", "test-org", "--parallel", "10", "--token", "fake_token"]
            )

            assert result.exit_code == 0
            # Verify parallel setting was applied to config
            scanner_init_call = mock_scanner_class.call_args
            config = scanner_init_call[0][0]
            assert config.parallel_scans == 10
