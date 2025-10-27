"""Tests for reporter classes."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from actionsguard.reporters.json_reporter import JSONReporter
from actionsguard.reporters.html_reporter import HTMLReporter
from actionsguard.reporters.csv_reporter import CSVReporter
from actionsguard.reporters.markdown_reporter import MarkdownReporter
from actionsguard.models import ScanResult, ScanSummary, RiskLevel, CheckResult, Status, Severity


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_results():
    """Create sample scan results."""
    return [
        ScanResult(
            repo_name="owner/critical-repo",
            repo_url="https://github.com/owner/critical-repo",
            score=2.0,
            risk_level=RiskLevel.CRITICAL,
            scan_date=datetime(2024, 1, 15, 10, 30, 0),
            checks=[
                CheckResult(
                    name="Dangerous-Workflow",
                    score=0,
                    status=Status.FAIL,
                    reason="Dangerous patterns found",
                    documentation_url="https://example.com/dangerous",
                    severity=Severity.CRITICAL,
                )
            ],
            metadata={"has_workflows": True},
        ),
        ScanResult(
            repo_name="owner/medium-repo",
            repo_url="https://github.com/owner/medium-repo",
            score=6.5,
            risk_level=RiskLevel.MEDIUM,
            scan_date=datetime(2024, 1, 15, 10, 35, 0),
            checks=[
                CheckResult(
                    name="Token-Permissions",
                    score=5,
                    status=Status.WARN,
                    reason="Some permissions issues",
                    documentation_url="https://example.com/permissions",
                    severity=Severity.MEDIUM,
                )
            ],
            metadata={"has_workflows": True},
        ),
        ScanResult(
            repo_name="owner/low-repo",
            repo_url="https://github.com/owner/low-repo",
            score=9.0,
            risk_level=RiskLevel.LOW,
            scan_date=datetime(2024, 1, 15, 10, 40, 0),
            checks=[
                CheckResult(
                    name="Pinned-Dependencies",
                    score=9,
                    status=Status.PASS,
                    reason="Dependencies well pinned",
                    documentation_url="https://example.com/pinned",
                    severity=Severity.LOW,
                )
            ],
            metadata={"has_workflows": True},
        ),
        ScanResult(
            repo_name="owner/error-repo",
            repo_url="https://github.com/owner/error-repo",
            score=0.0,
            risk_level=RiskLevel.CRITICAL,
            scan_date=datetime(2024, 1, 15, 10, 45, 0),
            checks=[],
            error="Failed to scan: API error",
        ),
    ]


@pytest.fixture
def sample_summary(sample_results):
    """Create a sample scan summary."""
    return ScanSummary.from_results(sample_results, scan_duration=120.5)


# JSONReporter Tests
def test_json_reporter_initialization(temp_output_dir):
    """Test JSON reporter initialization."""
    reporter = JSONReporter(temp_output_dir)
    assert reporter.output_dir == Path(temp_output_dir)
    assert reporter.output_dir.exists()


def test_json_reporter_get_extension():
    """Test JSON reporter extension."""
    reporter = JSONReporter("./test")
    assert reporter.get_extension() == ".json"


def test_json_reporter_generate_report(temp_output_dir, sample_summary):
    """Test JSON report generation."""
    reporter = JSONReporter(temp_output_dir)
    output_path = reporter.generate_report(sample_summary, filename="test_report")

    assert output_path.exists()
    assert output_path.name == "test_report.json"

    # Validate JSON structure
    with open(output_path, "r") as f:
        report_data = json.load(f)

    assert report_data["schema_version"] == JSONReporter.SCHEMA_VERSION
    assert report_data["tool"] == "ActionsGuard"
    assert report_data["report_type"] == "security_scan"
    assert "generated_at" in report_data
    assert "summary" in report_data

    # Validate summary data
    summary_data = report_data["summary"]
    assert summary_data["total_repos"] == 4
    assert summary_data["successful_scans"] == 3
    assert summary_data["failed_scans"] == 1
    assert summary_data["critical_count"] == 1  # 1 critical-severity check
    assert summary_data["medium_count"] == 1  # 1 medium-severity check
    assert summary_data["low_count"] == 1  # 1 low-severity check


def test_json_reporter_default_filename(temp_output_dir, sample_summary):
    """Test JSON report with default filename."""
    reporter = JSONReporter(temp_output_dir)
    output_path = reporter.generate_report(sample_summary)

    assert output_path.name == "report.json"


def test_json_reporter_creates_directory():
    """Test that JSON reporter creates output directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "nested" / "dir"
        reporter = JSONReporter(str(output_dir))

        assert output_dir.exists()


# HTMLReporter Tests
def test_html_reporter_initialization(temp_output_dir):
    """Test HTML reporter initialization."""
    with patch("actionsguard.reporters.html_reporter.Environment"):
        reporter = HTMLReporter(temp_output_dir)
        assert reporter.output_dir == Path(temp_output_dir)


def test_html_reporter_get_extension():
    """Test HTML reporter extension."""
    with patch("actionsguard.reporters.html_reporter.Environment"):
        reporter = HTMLReporter("./test")
        assert reporter.get_extension() == ".html"


def test_html_reporter_generate_report(temp_output_dir, sample_summary):
    """Test HTML report generation."""
    # Mock the Jinja2 environment and template
    mock_template = Mock()
    mock_template.render.return_value = "<html><body>Test Report</body></html>"

    mock_env = Mock()
    mock_env.get_template.return_value = mock_template

    with patch("actionsguard.reporters.html_reporter.Environment", return_value=mock_env):
        reporter = HTMLReporter(temp_output_dir)
        output_path = reporter.generate_report(sample_summary, filename="test_report")

        assert output_path.exists()
        assert output_path.name == "test_report.html"

        # Verify template was called with correct data
        mock_env.get_template.assert_called_once_with("report_enhanced.html")
        mock_template.render.assert_called_once()

        # Verify template received correct data
        template_data = mock_template.render.call_args[1]
        assert template_data["summary"] == sample_summary
        assert "generated_at" in template_data
        assert "exec_summary" in template_data

        # Verify repos were categorized correctly
        assert len(template_data["critical_repos"]) == 1
        assert template_data["critical_repos"][0].repo_name == "owner/critical-repo"
        assert len(template_data["medium_repos"]) == 1
        assert len(template_data["low_repos"]) == 1
        assert len(template_data["error_repos"]) == 1

        # Read generated file
        with open(output_path, "r") as f:
            content = f.read()
        assert "Test Report" in content


def test_html_reporter_executive_summary(temp_output_dir, sample_summary):
    """Test HTML reporter includes executive summary."""
    mock_template = Mock()
    mock_template.render.return_value = "<html></html>"

    mock_env = Mock()
    mock_env.get_template.return_value = mock_template

    with patch("actionsguard.reporters.html_reporter.Environment", return_value=mock_env):
        reporter = HTMLReporter(temp_output_dir)
        reporter.generate_report(sample_summary)

        template_data = mock_template.render.call_args[1]
        exec_summary = template_data["exec_summary"]

        # Executive summary should have key information
        assert "total_repositories" in exec_summary  # Actual key name
        assert "issue_counts" in exec_summary  # Contains critical/high/medium/low counts


# CSVReporter Tests
def test_csv_reporter_initialization(temp_output_dir):
    """Test CSV reporter initialization."""
    from actionsguard.reporters.csv_reporter import CSVReporter

    reporter = CSVReporter(temp_output_dir)
    assert reporter.output_dir == Path(temp_output_dir)


def test_csv_reporter_get_extension():
    """Test CSV reporter extension."""
    from actionsguard.reporters.csv_reporter import CSVReporter

    reporter = CSVReporter("./test")
    assert reporter.get_extension() == ".csv"


def test_csv_reporter_generate_report(temp_output_dir, sample_summary):
    """Test CSV report generation."""
    from actionsguard.reporters.csv_reporter import CSVReporter
    import csv

    reporter = CSVReporter(temp_output_dir)
    output_path = reporter.generate_report(sample_summary, filename="test_report")

    assert output_path.exists()
    assert output_path.name == "test_report.csv"

    # Read and validate CSV
    with open(output_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should have one row per repository
    assert len(rows) == 4

    # Validate header
    assert "Repository" in reader.fieldnames
    assert "Score" in reader.fieldnames
    assert "Risk Level" in reader.fieldnames

    # Validate data
    repo_names = {row["Repository"] for row in rows}
    assert "owner/critical-repo" in repo_names
    assert "owner/medium-repo" in repo_names
    assert "owner/low-repo" in repo_names
    assert "owner/error-repo" in repo_names

    # Check error handling
    error_row = next(r for r in rows if r["Repository"] == "owner/error-repo")
    assert error_row["Error"] == "Failed to scan: API error"


# MarkdownReporter Tests
def test_markdown_reporter_initialization(temp_output_dir):
    """Test Markdown reporter initialization."""
    from actionsguard.reporters.markdown_reporter import MarkdownReporter

    reporter = MarkdownReporter(temp_output_dir)
    assert reporter.output_dir == Path(temp_output_dir)


def test_markdown_reporter_get_extension():
    """Test Markdown reporter extension."""
    from actionsguard.reporters.markdown_reporter import MarkdownReporter

    reporter = MarkdownReporter("./test")
    assert reporter.get_extension() == ".md"


def test_markdown_reporter_generate_report(temp_output_dir, sample_summary):
    """Test Markdown report generation."""
    from actionsguard.reporters.markdown_reporter import MarkdownReporter

    reporter = MarkdownReporter(temp_output_dir)
    output_path = reporter.generate_report(sample_summary, filename="test_report")

    assert output_path.exists()
    assert output_path.name == "test_report.md"

    # Read and validate markdown
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Validate structure
    assert "ActionsGuard Security Report" in content or "Security" in content
    assert "owner/critical-repo" in content
    assert "owner/medium-repo" in content
    assert "owner/low-repo" in content

    # Should contain summary info
    assert "Total Repositories" in content or "total" in content.lower()
    assert "Risk" in content or "risk" in content.lower()


def test_markdown_reporter_contains_executive_summary(temp_output_dir, sample_summary):
    """Test Markdown report contains executive summary."""
    from actionsguard.reporters.markdown_reporter import MarkdownReporter

    reporter = MarkdownReporter(temp_output_dir)
    output_path = reporter.generate_report(sample_summary)

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Should have executive summary section
    exec_summary = sample_summary.get_executive_summary()
    assert any(key.replace("_", " ").title() in content for key in exec_summary.keys())


# Integration Tests
def test_all_reporters_generate_successfully(temp_output_dir, sample_summary):
    """Test that all reporters can generate reports successfully."""
    from actionsguard.reporters.csv_reporter import CSVReporter
    from actionsguard.reporters.markdown_reporter import MarkdownReporter

    reporters = {
        "json": JSONReporter(temp_output_dir),
        "csv": CSVReporter(temp_output_dir),
        "markdown": MarkdownReporter(temp_output_dir),
    }

    # HTML requires mocking template
    mock_template = Mock()
    mock_template.render.return_value = "<html></html>"
    mock_env = Mock()
    mock_env.get_template.return_value = mock_template

    with patch("actionsguard.reporters.html_reporter.Environment", return_value=mock_env):
        reporters["html"] = HTMLReporter(temp_output_dir)

    # Generate all reports
    outputs = {}
    for name, reporter in reporters.items():
        outputs[name] = reporter.generate_report(sample_summary, filename=f"test_{name}")

    # Verify all were created
    assert all(path.exists() for path in outputs.values())

    # Verify extensions
    assert outputs["json"].suffix == ".json"
    assert outputs["html"].suffix == ".html"
    assert outputs["csv"].suffix == ".csv"
    assert outputs["markdown"].suffix == ".md"


def test_reporters_handle_empty_results(temp_output_dir):
    """Test that reporters handle empty scan results."""
    empty_summary = ScanSummary(
        total_repos=0,
        successful_scans=0,
        failed_scans=0,
        average_score=0.0,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        results=[],
        scan_duration=0.0,
    )

    from actionsguard.reporters.csv_reporter import CSVReporter
    from actionsguard.reporters.markdown_reporter import MarkdownReporter

    # Test JSON
    json_reporter = JSONReporter(temp_output_dir)
    json_path = json_reporter.generate_report(empty_summary)
    assert json_path.exists()

    # Test CSV
    csv_reporter = CSVReporter(temp_output_dir)
    csv_path = csv_reporter.generate_report(empty_summary)
    assert csv_path.exists()

    # Test Markdown
    md_reporter = MarkdownReporter(temp_output_dir)
    md_path = md_reporter.generate_report(empty_summary)
    assert md_path.exists()

    # Test HTML
    mock_template = Mock()
    mock_template.render.return_value = "<html></html>"
    mock_env = Mock()
    mock_env.get_template.return_value = mock_template

    with patch("actionsguard.reporters.html_reporter.Environment", return_value=mock_env):
        html_reporter = HTMLReporter(temp_output_dir)
        html_path = html_reporter.generate_report(empty_summary)
        assert html_path.exists()


def test_json_reporter_unicode_handling(temp_output_dir):
    """Test JSON reporter handles unicode characters correctly."""
    results = [
        ScanResult(
            repo_name="owner/unicode-repo",
            repo_url="https://github.com/owner/unicode-repo",
            score=8.0,
            risk_level=RiskLevel.LOW,
            scan_date=datetime.now(),
            checks=[
                CheckResult(
                    name="Test-Check",
                    score=8,
                    status=Status.PASS,
                    reason="✓ All checks passed 🎉",
                    documentation_url="https://example.com",
                    severity=Severity.LOW,
                )
            ],
        )
    ]

    summary = ScanSummary.from_results(results, scan_duration=10.0)

    reporter = JSONReporter(temp_output_dir)
    output_path = reporter.generate_report(summary)

    # Should not raise encoding errors
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Unicode should be preserved
    check_reason = data["summary"]["results"][0]["checks"][0]["reason"]
    assert "✓" in check_reason
    assert "🎉" in check_reason
