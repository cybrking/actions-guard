"""GitHub API client wrapper for ActionsGuard."""

import logging
import time
from typing import List, Optional

from github import Github, GithubException, RateLimitExceededException
from github.Repository import Repository
from github.Organization import Organization


logger = logging.getLogger("actionsguard")


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

    def _paginate_with_retry(self, method, max_retries: int = 3):
        """
        Paginate through GitHub API results with retry on rate limit.

        Args:
            method: PyGithub method to call
            max_retries: Maximum number of retries

        Yields:
            Items from paginated results
        """
        retries = 0
        while retries < max_retries:
            try:
                for item in method():
                    yield item
                break  # Success, exit retry loop

            except RateLimitExceededException:
                retries += 1
                if retries >= max_retries:
                    logger.error("Rate limit exceeded. Max retries reached.")
                    raise

                rate_limit = self.github.get_rate_limit()
                reset_time = rate_limit.core.reset
                sleep_time = (reset_time - time.time()) + 10  # Add 10s buffer

                logger.warning(
                    f"Rate limit exceeded. Waiting {sleep_time:.0f} seconds "
                    f"until reset at {reset_time}"
                )
                time.sleep(max(sleep_time, 0))

            except GithubException as e:
                logger.error(f"GitHub API error: {e}")
                raise

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
