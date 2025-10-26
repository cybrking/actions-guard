"""Tests for GitHub client and retry logic."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from github import GithubException, RateLimitExceededException

from actionsguard.github_client import GitHubClient, retry_with_backoff


@pytest.fixture
def mock_github_token():
    """Mock GitHub token."""
    return "ghp_test_token_1234567890"


@pytest.fixture
def mock_github_client(mock_github_token):
    """Create a mock GitHub client."""
    with patch('actionsguard.github_client.Github') as mock_github:
        # Mock the get_user() call for token validation
        mock_user = Mock()
        mock_user.login = "test_user"
        mock_github.return_value.get_user.return_value = mock_user

        client = GitHubClient(mock_github_token)
        yield client


def test_client_initialization(mock_github_token):
    """Test GitHub client initialization."""
    with patch('actionsguard.github_client.Github') as mock_github:
        mock_user = Mock()
        mock_user.login = "test_user"
        mock_github.return_value.get_user.return_value = mock_user

        client = GitHubClient(mock_github_token)

        assert client.github is not None
        mock_github.assert_called_once_with(mock_github_token)


def test_client_invalid_token():
    """Test client initialization with invalid token."""
    with patch('actionsguard.github_client.Github') as mock_github:
        # Simulate 401 unauthorized
        mock_github.return_value.get_user.side_effect = GithubException(
            status=401,
            data={"message": "Bad credentials"},
            headers={}
        )

        with pytest.raises(ValueError, match="Invalid GitHub token"):
            GitHubClient("invalid_token")


def test_retry_decorator_success():
    """Test retry decorator with successful call."""
    call_count = [0]

    @retry_with_backoff(max_retries=3, base_delay=0.1)
    def successful_function():
        call_count[0] += 1
        return "success"

    result = successful_function()

    assert result == "success"
    assert call_count[0] == 1  # Should succeed on first try


def test_retry_decorator_with_rate_limit():
    """Test retry decorator with rate limit exception."""
    call_count = [0]

    @retry_with_backoff(max_retries=3, base_delay=0.1, max_delay=0.5)
    def rate_limited_function(self):
        call_count[0] += 1
        if call_count[0] < 2:
            raise RateLimitExceededException(
                status=403,
                data={"message": "Rate limit exceeded"},
                headers={}
            )
        return "success"

    # Create mock object with github attribute
    mock_self = Mock()
    mock_rate_limit = Mock()
    mock_rate_limit.core.reset = time.time() + 0.2  # Reset in 0.2 seconds
    mock_self.github.get_rate_limit.return_value = mock_rate_limit

    result = rate_limited_function(mock_self)

    assert result == "success"
    assert call_count[0] == 2  # Should succeed on second try


def test_retry_decorator_max_retries_exceeded():
    """Test retry decorator when max retries is exceeded."""
    call_count = [0]

    @retry_with_backoff(max_retries=2, base_delay=0.05)
    def always_fails():
        call_count[0] += 1
        raise GithubException(
            status=500,
            data={"message": "Server error"},
            headers={}
        )

    with pytest.raises(GithubException):
        always_fails()

    assert call_count[0] == 3  # Initial + 2 retries


def test_retry_decorator_server_error():
    """Test retry with server errors (500, 502, 503, 504)."""
    for error_code in [500, 502, 503, 504]:
        call_count = [0]

        @retry_with_backoff(max_retries=2, base_delay=0.05)
        def server_error_function():
            call_count[0] += 1
            if call_count[0] < 2:
                raise GithubException(
                    status=error_code,
                    data={"message": f"Server error {error_code}"},
                    headers={}
                )
            return "success"

        result = server_error_function()
        assert result == "success"
        assert call_count[0] == 2


def test_retry_decorator_client_error_no_retry():
    """Test that client errors (4xx except rate limit) don't retry."""
    call_count = [0]

    @retry_with_backoff(max_retries=3, base_delay=0.05)
    def client_error_function():
        call_count[0] += 1
        raise GithubException(
            status=404,
            data={"message": "Not found"},
            headers={}
        )

    with pytest.raises(GithubException):
        client_error_function()

    # Should not retry on 404
    assert call_count[0] == 1


def test_retry_decorator_network_error():
    """Test retry with network errors."""
    call_count = [0]

    @retry_with_backoff(max_retries=2, base_delay=0.05)
    def network_error_function():
        call_count[0] += 1
        if call_count[0] < 2:
            raise ConnectionError("Network error")
        return "success"

    result = network_error_function()
    assert result == "success"
    assert call_count[0] == 2


def test_has_workflows_true(mock_github_client):
    """Test detecting workflows in repository."""
    mock_repo = Mock()
    mock_repo.get_contents.return_value = [Mock()]  # Non-empty list

    result = mock_github_client.has_workflows(mock_repo)

    assert result is True
    mock_repo.get_contents.assert_called_once_with(".github/workflows")


def test_has_workflows_false(mock_github_client):
    """Test detecting no workflows in repository."""
    mock_repo = Mock()
    mock_repo.get_contents.side_effect = GithubException(
        status=404,
        data={},
        headers={}
    )

    result = mock_github_client.has_workflows(mock_repo)

    assert result is False


def test_get_repository(mock_github_client):
    """Test getting a single repository."""
    mock_repo = Mock()
    mock_repo.full_name = "owner/repo"

    mock_github_client.github.get_repo.return_value = mock_repo

    result = mock_github_client.get_repository("owner/repo")

    assert result == mock_repo
    mock_github_client.github.get_repo.assert_called_once_with("owner/repo")


def test_get_repository_not_found(mock_github_client):
    """Test getting non-existent repository."""
    mock_github_client.github.get_repo.side_effect = GithubException(
        status=404,
        data={},
        headers={}
    )

    with pytest.raises(ValueError, match="not found"):
        mock_github_client.get_repository("owner/nonexistent")


def test_check_rate_limit(mock_github_client):
    """Test rate limit checking."""
    mock_rate_limit = Mock()
    mock_rate_limit.core.remaining = 4500
    mock_rate_limit.core.limit = 5000
    mock_rate_limit.core.reset = Mock()

    mock_github_client.github.get_rate_limit.return_value = mock_rate_limit

    # Should not raise
    mock_github_client.check_rate_limit()


def test_check_rate_limit_low_warning(mock_github_client):
    """Test rate limit warning when low."""
    mock_rate_limit = Mock()
    mock_rate_limit.core.remaining = 50  # Low
    mock_rate_limit.core.limit = 5000
    mock_rate_limit.core.reset = Mock()

    mock_github_client.github.get_rate_limit.return_value = mock_rate_limit

    # Should not raise even with low rate limit
    mock_github_client.check_rate_limit()

    # Verify the rate limit check was called
    mock_github_client.github.get_rate_limit.assert_called_once()


def test_get_user_repos(mock_github_client):
    """Test getting user repositories."""
    mock_repo1 = Mock()
    mock_repo1.name = "repo1"
    mock_repo1.fork = False
    mock_repo1.archived = False

    mock_repo2 = Mock()
    mock_repo2.name = "repo2"
    mock_repo2.fork = True
    mock_repo2.archived = False

    mock_repo3 = Mock()
    mock_repo3.name = "repo3"
    mock_repo3.fork = False
    mock_repo3.archived = True

    mock_user = Mock()
    mock_user.login = "test_user"
    mock_user.get_repos.return_value = [mock_repo1, mock_repo2, mock_repo3]

    mock_github_client.github.get_user.return_value = mock_user

    # Test without including forks
    repos = mock_github_client.get_user_repos(username="test_user", include_forks=False)

    # Should only return repo1 (not fork, not archived)
    assert len(repos) == 1
    assert repos[0].name == "repo1"


def test_get_user_repos_include_forks(mock_github_client):
    """Test getting user repositories including forks."""
    mock_repo1 = Mock()
    mock_repo1.name = "repo1"
    mock_repo1.fork = False
    mock_repo1.archived = False

    mock_repo2 = Mock()
    mock_repo2.name = "repo2"
    mock_repo2.fork = True
    mock_repo2.archived = False

    mock_user = Mock()
    mock_user.login = "test_user"
    mock_user.get_repos.return_value = [mock_repo1, mock_repo2]

    mock_github_client.github.get_user.return_value = mock_user

    repos = mock_github_client.get_user_repos(username="test_user", include_forks=True)

    # Should return both (forks included)
    assert len(repos) == 2


def test_get_user_repos_with_filters(mock_github_client):
    """Test getting user repositories with filters."""
    mock_repo1 = Mock()
    mock_repo1.name = "repo1"
    mock_repo1.fork = False
    mock_repo1.archived = False

    mock_repo2 = Mock()
    mock_repo2.name = "repo2"
    mock_repo2.fork = False
    mock_repo2.archived = False

    mock_repo3 = Mock()
    mock_repo3.name = "repo3"
    mock_repo3.fork = False
    mock_repo3.archived = False

    mock_user = Mock()
    mock_user.login = "test_user"
    mock_user.get_repos.return_value = [mock_repo1, mock_repo2, mock_repo3]

    mock_github_client.github.get_user.return_value = mock_user

    # Test with 'only' filter
    repos = mock_github_client.get_user_repos(
        username="test_user",
        only=["repo1", "repo3"]
    )

    assert len(repos) == 2
    assert repos[0].name in ["repo1", "repo3"]
    assert repos[1].name in ["repo1", "repo3"]

    # Test with 'exclude' filter
    repos = mock_github_client.get_user_repos(
        username="test_user",
        exclude=["repo2"]
    )

    assert len(repos) == 2
    assert all(r.name != "repo2" for r in repos)
