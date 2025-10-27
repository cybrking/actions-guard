"""Tests for Scanner class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from actionsguard.scanner import Scanner
from actionsguard.models import ScanResult, ScanSummary, RiskLevel, CheckResult, Status, Severity
from actionsguard.utils.config import Config


@pytest.fixture
def mock_config():
    """Create a mock config."""
    return Config(
        github_token="ghp_test_token",
        output_dir="./test-reports",
        checks=["Dangerous-Workflow", "Token-Permissions"],
        parallel_scans=2,
        scorecard_timeout=300,
        use_cache=False,  # Disable cache for most tests
    )


@pytest.fixture
def mock_config_with_cache():
    """Create a mock config with caching enabled."""
    return Config(
        github_token="ghp_test_token",
        checks=["Dangerous-Workflow"],
        use_cache=True,
        cache_ttl=24,
    )


@pytest.fixture
def mock_repo():
    """Create a mock repository."""
    repo = Mock()
    repo.full_name = "owner/test-repo"
    repo.name = "test-repo"
    repo.html_url = "https://github.com/owner/test-repo"
    return repo


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
                name="Dangerous-Workflow",
                score=8,
                status=Status.PASS,
                reason="No dangerous patterns found",
                documentation_url="https://example.com/doc",
                severity=Severity.LOW,
            )
        ],
        workflows=[],
        metadata={"has_workflows": True},
    )


@pytest.fixture
def scanner(mock_config):
    """Create a Scanner instance with mocked dependencies."""
    with patch("actionsguard.scanner.GitHubClient"), patch(
        "actionsguard.scanner.ScorecardRunner"
    ), patch("actionsguard.scanner.WorkflowAnalyzer"):
        scanner = Scanner(mock_config, show_progress=False)
        yield scanner


def test_scanner_initialization(mock_config):
    """Test scanner initialization."""
    with patch("actionsguard.scanner.GitHubClient") as mock_gh, patch(
        "actionsguard.scanner.ScorecardRunner"
    ) as mock_sc, patch("actionsguard.scanner.WorkflowAnalyzer") as mock_wa:

        scanner = Scanner(mock_config, show_progress=True)

        assert scanner.config == mock_config
        assert scanner.show_progress is True
        assert scanner.cache is None  # Cache disabled in mock_config
        mock_gh.assert_called_once_with(mock_config.github_token)
        mock_sc.assert_called_once_with(timeout=mock_config.scorecard_timeout)
        mock_wa.assert_called_once()


def test_scanner_initialization_with_cache(mock_config_with_cache):
    """Test scanner initialization with cache enabled."""
    with patch("actionsguard.scanner.GitHubClient"), patch(
        "actionsguard.scanner.ScorecardRunner"
    ), patch("actionsguard.scanner.WorkflowAnalyzer"), patch(
        "actionsguard.scanner.ResultCache"
    ) as mock_cache:

        scanner = Scanner(mock_config_with_cache)

        assert scanner.cache is not None
        mock_cache.assert_called_once_with(ttl_hours=24)


def test_scan_repository_with_cache_hit(mock_config_with_cache, mock_repo, mock_scan_result):
    """Test scanning repository with cache hit."""
    with patch("actionsguard.scanner.GitHubClient"), patch(
        "actionsguard.scanner.ScorecardRunner"
    ), patch("actionsguard.scanner.WorkflowAnalyzer"), patch(
        "actionsguard.scanner.ResultCache"
    ) as mock_cache_class:

        # Setup cache to return cached result
        mock_cache = Mock()
        mock_cache.get.return_value = mock_scan_result
        mock_cache_class.return_value = mock_cache

        scanner = Scanner(mock_config_with_cache, show_progress=False)
        result = scanner.scan_repository(mock_repo)

        assert result == mock_scan_result
        mock_cache.get.assert_called_once_with("owner/test-repo", ["Dangerous-Workflow"])
        # Should not run scorecard if cached
        scanner.scorecard_runner.run_scorecard.assert_not_called()


def test_scan_repository_no_workflows(scanner, mock_repo):
    """Test scanning repository with no workflows."""
    scanner.github_client.has_workflows.return_value = False

    result = scanner.scan_repository(mock_repo)

    assert result.repo_name == "owner/test-repo"
    assert result.score == 10.0
    assert result.risk_level == RiskLevel.LOW
    assert result.metadata["has_workflows"] is False
    assert len(result.checks) == 0


def test_scan_repository_successful(scanner, mock_repo):
    """Test successful repository scan."""
    # Setup mocks
    scanner.github_client.has_workflows.return_value = True

    scorecard_data = {
        "score": 7.5,
        "checks": [
            {
                "name": "Dangerous-Workflow",
                "score": 8,
                "reason": "No dangerous patterns",
                "documentation": {"url": "https://example.com"},
                "details": [],
            }
        ],
        "scorecard": {"version": "4.0.0"},
        "repo": {"name": "owner/test-repo"},
    }

    scanner.scorecard_runner.run_scorecard.return_value = scorecard_data
    scanner.scorecard_runner.get_overall_score.return_value = 7.5
    scanner.scorecard_runner.get_metadata.return_value = {"scorecard_version": "4.0.0"}
    scanner.scorecard_runner.parse_results.return_value = [
        CheckResult(
            name="Dangerous-Workflow",
            score=8,
            status=Status.PASS,
            reason="No dangerous patterns",
            documentation_url="https://example.com",
            severity=Severity.LOW,
        )
    ]
    scanner.workflow_analyzer.analyze_scorecard_results.return_value = []

    result = scanner.scan_repository(mock_repo)

    assert result.repo_name == "owner/test-repo"
    assert result.score == 7.5
    assert result.risk_level == RiskLevel.MEDIUM
    assert result.metadata["has_workflows"] is True
    assert len(result.checks) == 1

    scanner.scorecard_runner.run_scorecard.assert_called_once()
    scanner.workflow_analyzer.analyze_scorecard_results.assert_called_once()


def test_scan_repository_with_error(scanner, mock_repo):
    """Test repository scan with error."""
    scanner.github_client.has_workflows.side_effect = Exception("API Error")

    result = scanner.scan_repository(mock_repo)

    assert result.repo_name == "owner/test-repo"
    assert result.score == 0.0
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.error == "API Error"
    assert len(result.checks) == 0


def test_scan_repositories_empty_list(scanner):
    """Test scanning empty repository list."""
    results = scanner.scan_repositories([])

    assert results == []


def test_scan_repositories_sequential(scanner, mock_repo):
    """Test scanning repositories sequentially."""
    scanner.github_client.has_workflows.return_value = False

    repos = [mock_repo]
    results = scanner.scan_repositories(repos, parallel=False)

    assert len(results) == 1
    assert results[0].repo_name == "owner/test-repo"


def test_scan_repositories_parallel(scanner, mock_repo):
    """Test scanning repositories in parallel."""
    scanner.github_client.has_workflows.return_value = False

    # Create multiple repos
    repo1 = Mock()
    repo1.full_name = "owner/repo1"
    repo1.name = "repo1"
    repo1.html_url = "https://github.com/owner/repo1"

    repo2 = Mock()
    repo2.full_name = "owner/repo2"
    repo2.name = "repo2"
    repo2.html_url = "https://github.com/owner/repo2"

    repos = [repo1, repo2]
    results = scanner.scan_repositories(repos, parallel=True)

    assert len(results) == 2
    repo_names = {r.repo_name for r in results}
    assert "owner/repo1" in repo_names
    assert "owner/repo2" in repo_names


def test_scan_repositories_parallel_with_progress(mock_config):
    """Test scanning with progress bar enabled."""
    with patch("actionsguard.scanner.GitHubClient"), patch(
        "actionsguard.scanner.ScorecardRunner"
    ), patch("actionsguard.scanner.WorkflowAnalyzer"), patch(
        "actionsguard.scanner.Progress"
    ) as mock_progress:

        # Setup progress mock
        mock_progress_instance = MagicMock()
        mock_progress.return_value.__enter__.return_value = mock_progress_instance

        scanner = Scanner(mock_config, show_progress=True)
        scanner.github_client.has_workflows.return_value = False

        # Create at least 2 repos to trigger parallel execution
        repo1 = Mock()
        repo1.full_name = "owner/repo1"
        repo1.name = "repo1"
        repo1.html_url = "https://github.com/owner/repo1"

        repo2 = Mock()
        repo2.full_name = "owner/repo2"
        repo2.name = "repo2"
        repo2.html_url = "https://github.com/owner/repo2"

        repos = [repo1, repo2]
        results = scanner.scan_repositories(repos, parallel=True)

        assert len(results) == 2
        # Verify progress bar was used
        mock_progress.assert_called_once()
        mock_progress_instance.add_task.assert_called_once()
        assert mock_progress_instance.update.call_count >= 2  # At least one update per repo


def test_scan_repositories_parallel_with_exception(scanner):
    """Test parallel scan handling executor exceptions."""
    # Create a repo that will cause an exception in the future
    bad_repo = Mock()
    bad_repo.full_name = "owner/bad-repo"
    bad_repo.name = "bad-repo"
    bad_repo.html_url = "https://github.com/owner/bad-repo"

    # Make has_workflows raise an exception
    scanner.github_client.has_workflows.side_effect = Exception("Test error")

    results = scanner.scan_repositories([bad_repo], parallel=True)

    assert len(results) == 1
    assert results[0].error == "Test error"
    assert results[0].risk_level == RiskLevel.CRITICAL


def test_scan_organization_no_repos(scanner):
    """Test scanning organization with no repositories."""
    scanner.github_client.get_organization_repos.return_value = []

    summary = scanner.scan_organization("test-org")

    assert summary.total_repos == 0
    assert summary.successful_scans == 0
    assert summary.failed_scans == 0
    assert summary.average_score == 0.0


def test_scan_organization_successful(scanner, mock_repo):
    """Test successful organization scan."""
    scanner.github_client.get_organization_repos.return_value = [mock_repo]
    scanner.github_client.has_workflows.return_value = False

    summary = scanner.scan_organization("test-org", exclude=["repo1"], only=["test-repo"])

    assert summary.total_repos == 1
    assert summary.successful_scans == 1
    assert summary.failed_scans == 0

    # Verify filters were passed
    scanner.github_client.get_organization_repos.assert_called_once_with(
        org_name="test-org",
        exclude=["repo1"],
        only=["test-repo"],
    )


def test_scan_user_no_repos(scanner):
    """Test scanning user with no repositories."""
    scanner.github_client.get_user_repos.return_value = []

    summary = scanner.scan_user("test-user")

    assert summary.total_repos == 0
    assert summary.successful_scans == 0


def test_scan_user_successful(scanner, mock_repo):
    """Test successful user scan."""
    scanner.github_client.get_user_repos.return_value = [mock_repo]
    scanner.github_client.has_workflows.return_value = False

    summary = scanner.scan_user(
        username="test-user", exclude=["repo1"], only=["test-repo"], include_forks=True
    )

    assert summary.total_repos == 1
    assert summary.successful_scans == 1

    # Verify filters were passed
    scanner.github_client.get_user_repos.assert_called_once_with(
        username="test-user",
        exclude=["repo1"],
        only=["test-repo"],
        include_forks=True,
    )


def test_scan_user_authenticated_user(scanner, mock_repo):
    """Test scanning authenticated user (username=None)."""
    scanner.github_client.get_user_repos.return_value = [mock_repo]
    scanner.github_client.has_workflows.return_value = False

    summary = scanner.scan_user(username=None)

    assert summary.total_repos == 1
    scanner.github_client.get_user_repos.assert_called_once_with(
        username=None,
        exclude=None,
        only=None,
        include_forks=False,
    )


def test_scan_single_repository(scanner, mock_repo):
    """Test scanning a single repository by name."""
    scanner.github_client.get_repository.return_value = mock_repo
    scanner.github_client.has_workflows.return_value = False

    result = scanner.scan_single_repository("owner/test-repo")

    assert result.repo_name == "owner/test-repo"
    scanner.github_client.get_repository.assert_called_once_with("owner/test-repo")


def test_scan_summary_from_results():
    """Test ScanSummary.from_results creation."""
    results = [
        ScanResult(
            repo_name="repo1",
            repo_url="https://github.com/owner/repo1",
            score=8.0,
            risk_level=RiskLevel.LOW,
            scan_date=datetime.now(),
            checks=[
                CheckResult(
                    name="Test1",
                    score=8,
                    status=Status.PASS,
                    reason="OK",
                    documentation_url="",
                    severity=Severity.LOW,
                )
            ],
        ),
        ScanResult(
            repo_name="repo2",
            repo_url="https://github.com/owner/repo2",
            score=3.0,
            risk_level=RiskLevel.CRITICAL,
            scan_date=datetime.now(),
            checks=[
                CheckResult(
                    name="Test2",
                    score=0,
                    status=Status.FAIL,
                    reason="Failed",
                    documentation_url="",
                    severity=Severity.CRITICAL,
                )
            ],
        ),
        ScanResult(
            repo_name="repo3",
            repo_url="https://github.com/owner/repo3",
            score=0.0,
            risk_level=RiskLevel.CRITICAL,
            scan_date=datetime.now(),
            checks=[],
            error="Failed to scan",
        ),
    ]

    summary = ScanSummary.from_results(results, scan_duration=10.5)

    assert summary.total_repos == 3
    assert summary.successful_scans == 2  # repo1 and repo2 (no error)
    assert summary.failed_scans == 1  # repo3 has error
    assert summary.average_score == 5.5  # (8.0 + 3.0) / 2
    assert summary.critical_count == 1  # 1 critical check in repo2
    assert summary.low_count == 1  # 1 low check in repo1
    assert summary.scan_duration == 10.5
    assert len(summary.results) == 3


def test_scan_repository_caches_result(mock_config_with_cache, mock_repo):
    """Test that scan results are cached when cache is enabled."""
    with patch("actionsguard.scanner.GitHubClient"), patch(
        "actionsguard.scanner.ScorecardRunner"
    ), patch("actionsguard.scanner.WorkflowAnalyzer"), patch(
        "actionsguard.scanner.ResultCache"
    ) as mock_cache_class:

        # Setup cache to return None (no cached result)
        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache_class.return_value = mock_cache

        scanner = Scanner(mock_config_with_cache, show_progress=False)
        scanner.github_client.has_workflows.return_value = False

        result = scanner.scan_repository(mock_repo)

        # Verify result was cached
        mock_cache.set.assert_called_once()
        args = mock_cache.set.call_args[0]
        assert args[0] == "owner/test-repo"
        assert args[1] == ["Dangerous-Workflow"]
        assert args[2] == result


def test_scan_repository_no_cache_on_error(mock_config_with_cache, mock_repo):
    """Test that errors are not cached."""
    with patch("actionsguard.scanner.GitHubClient"), patch(
        "actionsguard.scanner.ScorecardRunner"
    ), patch("actionsguard.scanner.WorkflowAnalyzer"), patch(
        "actionsguard.scanner.ResultCache"
    ) as mock_cache_class:

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache_class.return_value = mock_cache

        scanner = Scanner(mock_config_with_cache, show_progress=False)
        scanner.github_client.has_workflows.side_effect = Exception("API Error")

        result = scanner.scan_repository(mock_repo)

        # Verify result was NOT cached (because it has an error)
        mock_cache.set.assert_not_called()
        assert result.error == "API Error"
