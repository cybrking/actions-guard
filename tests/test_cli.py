"""Tests for CLI interface."""

import pytest
from click.testing import CliRunner

from actionsguard.cli import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


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


def test_scan_help(runner):
    """Test scan command help."""
    result = runner.invoke(cli, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--repo" in result.output
    assert "--org" in result.output


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
