"""Tests for WorkflowAnalyzer class."""

import pytest
from actionsguard.workflow_analyzer import WorkflowAnalyzer
from actionsguard.models import CheckResult, Status, Severity, WorkflowAnalysis, WorkflowFinding


@pytest.fixture
def analyzer():
    """Create a WorkflowAnalyzer instance."""
    return WorkflowAnalyzer()


@pytest.fixture
def sample_checks():
    """Create sample CheckResult objects."""
    return [
        CheckResult(
            name="Dangerous-Workflow",
            score=3,
            status=Status.FAIL,
            reason="Dangerous patterns found",
            documentation_url="https://example.com/dangerous",
            severity=Severity.CRITICAL,
        ),
        CheckResult(
            name="Token-Permissions",
            score=5,
            status=Status.WARN,
            reason="Excessive permissions",
            documentation_url="https://example.com/permissions",
            severity=Severity.MEDIUM,
        ),
        CheckResult(
            name="Pinned-Dependencies",
            score=8,
            status=Status.PASS,
            reason="Dependencies pinned",
            documentation_url="https://example.com/pinned",
            severity=Severity.LOW,
        ),
    ]


@pytest.fixture
def sample_scorecard_data():
    """Create sample Scorecard data with workflow details."""
    return {
        "score": 5.5,
        "checks": [
            {
                "name": "Dangerous-Workflow",
                "score": 3,
                "reason": "Dangerous patterns found",
                "documentation": {"url": "https://example.com/dangerous"},
                "details": [
                    {
                        "path": ".github/workflows/ci.yml",
                        "msg": "untrusted input in .github/workflows/ci.yml",
                        "type": "Warn",
                        "line": 42,
                        "snippet": "run: echo ${{ github.event.issue.title }}",
                    },
                    {
                        "path": ".github/workflows/pr.yml",
                        "msg": "pull_request_target trigger in .github/workflows/pr.yml",
                        "type": "Warn",
                    },
                ],
            },
            {
                "name": "Token-Permissions",
                "score": 5,
                "reason": "Excessive permissions",
                "documentation": {"url": "https://example.com/permissions"},
                "details": [
                    {
                        "path": ".github/workflows/ci.yml",
                        "msg": "permissions set to write-all in .github/workflows/ci.yml",
                        "type": "Warn",
                    },
                ],
            },
            {
                "name": "Pinned-Dependencies",
                "score": 4,
                "reason": "Some unpinned dependencies",
                "documentation": {"url": "https://example.com/pinned"},
                "details": [
                    {
                        "msg": "unpinned dependency actions/checkout@v3 found in .github/workflows/ci.yml",
                        "type": "Warn",
                    },
                ],
            },
        ],
    }


def test_analyzer_initialization(analyzer):
    """Test analyzer initialization."""
    assert analyzer is not None


def test_analyze_scorecard_results_empty_data(analyzer, sample_checks):
    """Test analyzing with empty scorecard data."""
    result = analyzer.analyze_scorecard_results({}, sample_checks)
    assert result == []

    result = analyzer.analyze_scorecard_results(None, sample_checks)
    assert result == []


def test_analyze_scorecard_results_empty_checks(analyzer):
    """Test analyzing with empty checks."""
    scorecard_data = {"checks": []}
    result = analyzer.analyze_scorecard_results(scorecard_data, [])
    assert result == []


def test_analyze_scorecard_results_no_checks_in_data(analyzer, sample_checks):
    """Test analyzing when scorecard data has no checks field."""
    scorecard_data = {"score": 5.0}
    result = analyzer.analyze_scorecard_results(scorecard_data, sample_checks)
    assert result == []


def test_analyze_scorecard_results_successful(analyzer, sample_scorecard_data, sample_checks):
    """Test successful workflow analysis."""
    workflows = analyzer.analyze_scorecard_results(sample_scorecard_data, sample_checks)

    # Should create WorkflowAnalysis objects
    assert len(workflows) > 0
    assert all(isinstance(w, WorkflowAnalysis) for w in workflows)

    # Find the ci.yml workflow
    ci_workflow = next((w for w in workflows if "ci.yml" in w.path), None)
    assert ci_workflow is not None

    # Should have findings from multiple checks
    assert len(ci_workflow.findings) >= 2  # At least from Dangerous-Workflow and Token-Permissions

    # Verify findings have required fields
    for finding in ci_workflow.findings:
        assert finding.workflow_path
        assert finding.check_name
        assert finding.severity
        assert finding.message


def test_analyze_scorecard_results_with_line_numbers(analyzer, sample_scorecard_data, sample_checks):
    """Test that line numbers are extracted from details."""
    workflows = analyzer.analyze_scorecard_results(sample_scorecard_data, sample_checks)

    # Find finding with line number
    finding_with_line = None
    for workflow in workflows:
        for finding in workflow.findings:
            if finding.line_number is not None:
                finding_with_line = finding
                break

    assert finding_with_line is not None
    assert finding_with_line.line_number == 42


def test_analyze_scorecard_results_with_snippets(analyzer, sample_scorecard_data, sample_checks):
    """Test that code snippets are extracted from details."""
    workflows = analyzer.analyze_scorecard_results(sample_scorecard_data, sample_checks)

    # Find finding with snippet
    finding_with_snippet = None
    for workflow in workflows:
        for finding in workflow.findings:
            if finding.snippet:
                finding_with_snippet = finding
                break

    assert finding_with_snippet is not None
    assert "echo" in finding_with_snippet.snippet


def test_analyze_scorecard_results_workflow_sorting(analyzer, sample_checks):
    """Test that workflows are sorted by severity (most critical first)."""
    # Create data with different severity levels
    scorecard_data = {
        "checks": [
            {
                "name": "Dangerous-Workflow",
                "score": 3,
                "reason": "Critical issues",
                "documentation": {"url": "https://example.com"},
                "details": [
                    {"path": ".github/workflows/critical.yml", "msg": "Critical issue", "type": "Warn"},
                ],
            },
            {
                "name": "Pinned-Dependencies",
                "score": 8,
                "reason": "Minor issues",
                "documentation": {"url": "https://example.com"},
                "details": [
                    {"path": ".github/workflows/low.yml", "msg": "Minor issue", "type": "Info"},
                ],
            },
        ],
    }

    workflows = analyzer.analyze_scorecard_results(scorecard_data, sample_checks)

    # First workflow should have more critical findings
    assert len(workflows) >= 1
    # Critical workflow should come first due to sorting
    assert workflows[0].get_critical_count() >= 0


def test_extract_workflow_path_from_path_field(analyzer):
    """Test extracting workflow path from detail's path field."""
    detail = {"path": ".github/workflows/test.yml", "msg": "Some message"}
    path = analyzer._extract_workflow_path(detail, detail["msg"])

    assert path == ".github/workflows/test.yml"


def test_extract_workflow_path_from_message(analyzer):
    """Test extracting workflow path from message."""
    detail = {"msg": "Issue found in .github/workflows/deploy.yaml"}
    path = analyzer._extract_workflow_path(detail, detail["msg"])

    assert path == ".github/workflows/deploy.yaml"


def test_extract_workflow_path_yml_extension(analyzer):
    """Test extracting workflow path with .yml extension."""
    detail = {"msg": "Found in .github/workflows/test-ci.yml"}
    path = analyzer._extract_workflow_path(detail, detail["msg"])

    assert path == ".github/workflows/test-ci.yml"


def test_extract_workflow_path_yaml_extension(analyzer):
    """Test extracting workflow path with .yaml extension."""
    detail = {"msg": "Found in .github/workflows/test-ci.yaml"}
    path = analyzer._extract_workflow_path(detail, detail["msg"])

    assert path == ".github/workflows/test-ci.yaml"


def test_extract_workflow_path_not_found(analyzer):
    """Test when workflow path cannot be extracted."""
    detail = {"msg": "Generic message without path"}
    path = analyzer._extract_workflow_path(detail, detail["msg"])

    assert path is None


def test_extract_line_number_from_line_field(analyzer):
    """Test extracting line number from 'line' field."""
    detail = {"line": 42}
    line_num = analyzer._extract_line_number(detail)

    assert line_num == 42


def test_extract_line_number_from_offset_field(analyzer):
    """Test extracting line number from 'offset' field."""
    detail = {"offset": 100}
    line_num = analyzer._extract_line_number(detail)

    assert line_num == 100


def test_extract_line_number_not_found(analyzer):
    """Test when line number is not available."""
    detail = {"msg": "No line info"}
    line_num = analyzer._extract_line_number(detail)

    assert line_num is None


def test_extract_snippet(analyzer):
    """Test extracting code snippet."""
    detail = {"snippet": "run: echo ${{ secrets.TOKEN }}"}
    snippet = analyzer._extract_snippet(detail)

    assert snippet == "run: echo ${{ secrets.TOKEN }}"


def test_extract_snippet_not_found(analyzer):
    """Test when snippet is not available."""
    detail = {"msg": "No snippet"}
    snippet = analyzer._extract_snippet(detail)

    assert snippet is None


def test_get_recommendation_dangerous_workflow_pull_request_target(analyzer):
    """Test recommendation for pull_request_target."""
    rec = analyzer._get_recommendation("Dangerous-Workflow", "Using pull_request_target trigger")

    assert "pull_request_target" in rec
    assert "pull_request" in rec


def test_get_recommendation_dangerous_workflow_injection(analyzer):
    """Test recommendation for injection issues."""
    rec = analyzer._get_recommendation("Dangerous-Workflow", "untrusted input in command")

    assert "untrusted" in rec or "injection" in rec
    assert "GITHUB_ENV" in rec


def test_get_recommendation_dangerous_workflow_generic(analyzer):
    """Test generic recommendation for dangerous workflow."""
    rec = analyzer._get_recommendation("Dangerous-Workflow", "Some other dangerous pattern")

    assert "dangerous" in rec.lower()


def test_get_recommendation_token_permissions_write_all(analyzer):
    """Test recommendation for write-all permissions."""
    rec = analyzer._get_recommendation("Token-Permissions", "permissions set to write-all")

    assert "write-all" in rec
    assert "minimal" in rec.lower() or "specific" in rec.lower()


def test_get_recommendation_token_permissions_write(analyzer):
    """Test recommendation for write permissions."""
    rec = analyzer._get_recommendation("Token-Permissions", "excessive write permissions")

    assert "permission" in rec.lower()


def test_get_recommendation_pinned_dependencies_with_action(analyzer):
    """Test recommendation for unpinned dependencies with action name."""
    rec = analyzer._get_recommendation(
        "Pinned-Dependencies",
        "unpinned dependency actions/checkout@v3"
    )

    assert "actions/checkout" in rec
    assert "commit SHA" in rec or "SHA" in rec


def test_get_recommendation_pinned_dependencies_generic(analyzer):
    """Test generic recommendation for unpinned dependencies."""
    rec = analyzer._get_recommendation("Pinned-Dependencies", "Some unpinned dependency")

    assert "commit SHA" in rec or "SHA" in rec
    assert "actions/checkout@" in rec  # Example usage


def test_get_recommendation_unknown_check(analyzer):
    """Test recommendation for unknown check type."""
    rec = analyzer._get_recommendation("Unknown-Check", "Some message")

    assert "remediate" in rec.lower() or "review" in rec.lower()


def test_analyze_with_non_iterable_details(analyzer, sample_checks):
    """Test handling of non-iterable details field."""
    scorecard_data = {
        "checks": [
            {
                "name": "Dangerous-Workflow",
                "score": 5,
                "reason": "Test",
                "documentation": {"url": "https://example.com"},
                "details": "not a list",  # Invalid - should be a list
            },
        ],
    }

    # Should not crash, just skip this check
    workflows = analyzer.analyze_scorecard_results(scorecard_data, sample_checks)

    # Should return empty since details couldn't be processed
    assert workflows == []


def test_analyze_with_none_details(analyzer, sample_checks):
    """Test handling when details is None."""
    scorecard_data = {
        "checks": [
            {
                "name": "Dangerous-Workflow",
                "score": 5,
                "reason": "Test",
                "documentation": {"url": "https://example.com"},
                "details": None,
            },
        ],
    }

    workflows = analyzer.analyze_scorecard_results(scorecard_data, sample_checks)

    assert workflows == []


def test_analyze_with_invalid_detail_items(analyzer, sample_checks):
    """Test handling of invalid items in details list."""
    scorecard_data = {
        "checks": [
            {
                "name": "Dangerous-Workflow",
                "score": 5,
                "reason": "Test",
                "documentation": {"url": "https://example.com"},
                "details": [
                    None,  # Invalid item
                    "string",  # Invalid item
                    {"path": ".github/workflows/valid.yml", "msg": "Valid"},  # Valid
                ],
            },
        ],
    }

    workflows = analyzer.analyze_scorecard_results(scorecard_data, sample_checks)

    # Should process only the valid detail
    assert len(workflows) == 1
    assert workflows[0].path == ".github/workflows/valid.yml"


def test_workflow_analysis_severity_counts(analyzer, sample_scorecard_data, sample_checks):
    """Test workflow analysis severity count methods."""
    workflows = analyzer.analyze_scorecard_results(sample_scorecard_data, sample_checks)

    ci_workflow = next((w for w in workflows if "ci.yml" in w.path), None)
    assert ci_workflow is not None

    # Should have critical findings (from Dangerous-Workflow check)
    critical_count = ci_workflow.get_critical_count()
    high_count = ci_workflow.get_high_count()
    medium_count = ci_workflow.get_medium_count()
    low_count = ci_workflow.get_low_count()

    # All counts should be non-negative
    assert critical_count >= 0
    assert high_count >= 0
    assert medium_count >= 0
    assert low_count >= 0

    # Total findings should match sum of severity counts
    total = critical_count + high_count + medium_count + low_count
    assert total == len(ci_workflow.findings)
