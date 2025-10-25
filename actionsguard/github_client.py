"""GitHub API client wrapper for ActionsGuard."""

import logging
import time
from typing import List, Optional, Callable, Any
from functools import wraps

from github import Github, GithubException, RateLimitExceededException
from github.Repository import Repository
from github.Organization import Organization


logger = logging.getLogger("actionsguard")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            delay = base_delay

            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)

                except RateLimitExceededException as e:
                    # Special handling for rate limits - wait until reset
                    if retries >= max_retries:
                        logger.error("Rate limit exceeded. Max retries reached.")
                        raise

                    # Get self from args if this is a method
                    self_obj = args[0] if args and hasattr(args[0], 'github') else None
                    if self_obj and hasattr(self_obj, 'github'):
                        rate_limit = self_obj.github.get_rate_limit()
                        reset_time = rate_limit.core.reset
                        sleep_time = min((reset_time - time.time()) + 10, max_delay)

                        logger.warning(
                            f"Rate limit exceeded. Waiting {sleep_time:.0f}s "
                            f"until reset (attempt {retries + 1}/{max_retries})"
                        )
                        time.sleep(max(sleep_time, 0))
                    else:
                        # Fallback to exponential backoff
                        logger.warning(f"Rate limit exceeded. Retrying in {delay:.1f}s")
                        time.sleep(delay)

                    retries += 1
                    delay = min(delay * exponential_base, max_delay)

                except GithubException as e:
                    # Retry on specific transient errors
                    if e.status in (500, 502, 503, 504):  # Server errors
                        if retries >= max_retries:
                            logger.error(f"GitHub server error {e.status}. Max retries reached.")
                            raise

                        logger.warning(
                            f"GitHub server error {e.status}. Retrying in {delay:.1f}s "
                            f"(attempt {retries + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        retries += 1
                        delay = min(delay * exponential_base, max_delay)

                    elif e.status == 403 and 'rate limit' in str(e).lower():
                        # Secondary rate limit or abuse detection
                        if retries >= max_retries:
                            logger.error("Secondary rate limit exceeded. Max retries reached.")
                            raise

                        retry_after = delay * (retries + 1)  # Increasing delay
                        logger.warning(
                            f"Secondary rate limit hit. Backing off for {retry_after:.0f}s "
                            f"(attempt {retries + 1}/{max_retries})"
                        )
                        time.sleep(retry_after)
                        retries += 1
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        # Don't retry on client errors (4xx except rate limits)
                        raise

                except (ConnectionError, TimeoutError) as e:
                    # Network errors - retry with backoff
                    if retries >= max_retries:
                        logger.error(f"Network error: {e}. Max retries reached.")
                        raise

                    logger.warning(
                        f"Network error: {e}. Retrying in {delay:.1f}s "
                        f"(attempt {retries + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    retries += 1
                    delay = min(delay * exponential_base, max_delay)

            # Should not reach here, but just in case
            raise Exception(f"Max retries ({max_retries}) exceeded")

        return wrapper
    return decorator


class GitHubClient:
    """Wrapper around PyGithub for ActionsGuard operations."""

    def __init__(self, token: str):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token

        Raises:
            ValueError: If token is invalid
        """
        self.github = Github(token)
        self._validate_token()

    def _validate_token(self) -> None:
        """
        Validate GitHub token.

        Raises:
            ValueError: If token is invalid or lacks required permissions
        """
        try:
            user = self.github.get_user()
            logger.debug(f"Authenticated as: {user.login}")
        except GithubException as e:
            if e.status == 401:
                raise ValueError(
                    "Invalid GitHub token. Check token has 'repo' and 'read:org' scopes."
                )
            raise

    def get_organization_repos(
        self,
        org_name: str,
        exclude: Optional[List[str]] = None,
        only: Optional[List[str]] = None
    ) -> List[Repository]:
        """
        Get repositories from an organization with filtering.

        Args:
            org_name: Organization name
            exclude: List of repo names to exclude
            only: List of repo names to include (if set, only these repos)

        Returns:
            List of Repository objects

        Raises:
            ValueError: If organization not found or no access
        """
        exclude = exclude or []
        only = only or []

        try:
            org = self.github.get_organization(org_name)
            logger.info(f"Fetching repositories from organization: {org_name}")

            repos = []
            for repo in self._paginate_with_retry(org.get_repos):
                # Skip archived repos
                if repo.archived:
                    logger.debug(f"Skipping archived repo: {repo.name}")
                    continue

                # Apply filtering
                if only and repo.name not in only:
                    continue

                if repo.name in exclude:
                    logger.debug(f"Excluding repo: {repo.name}")
                    continue

                repos.append(repo)

            logger.info(f"Found {len(repos)} repositories to scan")
            return repos

        except GithubException as e:
            if e.status == 404:
                raise ValueError(
                    f"Organization '{org_name}' not found. "
                    "Check the name and ensure you have access."
                )
            elif e.status == 403:
                raise ValueError(
                    f"No permission to access organization '{org_name}'. "
                    "Check token has 'read:org' scope."
                )
            raise

    def get_user_repos(
        self,
        username: Optional[str] = None,
        exclude: Optional[List[str]] = None,
        only: Optional[List[str]] = None,
        include_forks: bool = False
    ) -> List[Repository]:
        """
        Get repositories from a user account with filtering.

        Args:
            username: GitHub username (if None, uses authenticated user)
            exclude: List of repo names to exclude
            only: List of repo names to include (if set, only these repos)
            include_forks: Whether to include forked repositories (default: False)

        Returns:
            List of Repository objects

        Raises:
            ValueError: If user not found or no access
        """
        exclude = exclude or []
        only = only or []

        try:
            # Get authenticated user to check if username matches
            auth_user = self.github.get_user()

            if username:
                # Check if username is the authenticated user
                if username.lower() == auth_user.login.lower():
                    logger.info(f"Fetching repositories from authenticated user: {username} (using authenticated endpoint)")
                    user = auth_user
                else:
                    logger.info(f"Fetching repositories from user: {username}")
                    user = self.github.get_user(username)
            else:
                user = auth_user
                logger.info(f"Fetching repositories from authenticated user: {user.login}")

            repos = []
            total_repos = 0
            skipped_archived = 0
            skipped_forks = 0
            skipped_filtered = 0

            for repo in self._paginate_with_retry(user.get_repos):
                total_repos += 1

                # Skip archived repos
                if repo.archived:
                    skipped_archived += 1
                    logger.debug(f"Skipping archived repo: {repo.name}")
                    continue

                # Skip forks unless explicitly included in 'only' list or include_forks is True
                if repo.fork and not include_forks and not (only and repo.name in only):
                    skipped_forks += 1
                    logger.debug(f"Skipping forked repo: {repo.name}")
                    continue

                # Apply filtering
                if only and repo.name not in only:
                    skipped_filtered += 1
                    continue

                if repo.name in exclude:
                    skipped_filtered += 1
                    logger.debug(f"Excluding repo: {repo.name}")
                    continue

                repos.append(repo)

            logger.info(
                f"Found {len(repos)} repositories to scan "
                f"(total: {total_repos}, archived: {skipped_archived}, "
                f"forks: {skipped_forks}, filtered: {skipped_filtered})"
            )
            return repos

        except GithubException as e:
            if e.status == 404:
                raise ValueError(
                    f"User '{username}' not found. "
                    "Check the username and ensure the account exists."
                )
            elif e.status == 403:
                raise ValueError(
                    f"No permission to access user '{username}' repositories."
                )
            raise

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    def get_repository(self, repo_full_name: str) -> Repository:
        """
        Get a single repository by full name (owner/repo).

        Args:
            repo_full_name: Repository in format 'owner/repo'

        Returns:
            Repository object

        Raises:
            ValueError: If repository not found or no access
        """
        try:
            repo = self.github.get_repo(repo_full_name)
            logger.debug(f"Fetched repository: {repo.full_name}")
            return repo

        except GithubException as e:
            if e.status == 404:
                raise ValueError(
                    f"Repository '{repo_full_name}' not found. "
                    "Check the name and ensure you have access."
                )
            elif e.status == 403:
                raise ValueError(
                    f"No permission to access repository '{repo_full_name}'."
                )
            raise

    def check_rate_limit(self) -> None:
        """Check and log current rate limit status."""
        rate_limit = self.github.get_rate_limit()
        core = rate_limit.core

        logger.debug(
            f"GitHub API rate limit: {core.remaining}/{core.limit} "
            f"(resets at {core.reset})"
        )

        if core.remaining < 100:
            logger.warning(
                f"Low rate limit: {core.remaining} requests remaining. "
                f"Resets at {core.reset}"
            )

    def _paginate_with_retry(
        self,
        method,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        """
        Paginate through GitHub API results with exponential backoff retry.

        Args:
            method: PyGithub method to call
            max_retries: Maximum number of retries
            base_delay: Initial delay in seconds for exponential backoff
            max_delay: Maximum delay in seconds

        Yields:
            Items from paginated results
        """
        retries = 0
        delay = base_delay

        while retries <= max_retries:
            try:
                for item in method():
                    yield item
                break  # Success, exit retry loop

            except RateLimitExceededException:
                if retries >= max_retries:
                    logger.error("Rate limit exceeded. Max retries reached.")
                    raise

                rate_limit = self.github.get_rate_limit()
                reset_time = rate_limit.core.reset
                sleep_time = min((reset_time - time.time()) + 10, max_delay)

                logger.warning(
                    f"Rate limit exceeded. Waiting {sleep_time:.0f}s until reset "
                    f"(attempt {retries + 1}/{max_retries})"
                )
                time.sleep(max(sleep_time, 0))
                retries += 1

            except GithubException as e:
                # Retry on server errors with exponential backoff
                if e.status in (500, 502, 503, 504):
                    if retries >= max_retries:
                        logger.error(f"GitHub server error {e.status}. Max retries reached.")
                        raise

                    logger.warning(
                        f"GitHub server error {e.status}. Retrying in {delay:.1f}s "
                        f"(attempt {retries + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    retries += 1
                    delay = min(delay * 2.0, max_delay)  # Exponential backoff
                else:
                    logger.error(f"GitHub API error: {e}")
                    raise

            except (ConnectionError, TimeoutError) as e:
                if retries >= max_retries:
                    logger.error(f"Network error: {e}. Max retries reached.")
                    raise

                logger.warning(
                    f"Network error: {e}. Retrying in {delay:.1f}s "
                    f"(attempt {retries + 1}/{max_retries})"
                )
                time.sleep(delay)
                retries += 1
                delay = min(delay * 2.0, max_delay)

    @retry_with_backoff(max_retries=2, base_delay=0.5, max_delay=10.0)
    def has_workflows(self, repo: Repository) -> bool:
        """
        Check if repository has GitHub Actions workflows.

        Args:
            repo: Repository object

        Returns:
            True if repo has .github/workflows directory
        """
        try:
            contents = repo.get_contents(".github/workflows")
            return len(contents) > 0 if isinstance(contents, list) else True
        except GithubException:
            return False
