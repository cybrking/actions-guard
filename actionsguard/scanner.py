"""Core scanning logic for ActionsGuard."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional

from github.Repository import Repository

from actionsguard.github_client import GitHubClient
from actionsguard.scorecard_runner import ScorecardRunner
from actionsguard.workflow_analyzer import WorkflowAnalyzer
from actionsguard.models import ScanResult, ScanSummary, RiskLevel
from actionsguard.utils.config import Config


logger = logging.getLogger("actionsguard")


class Scanner:
    """Main scanner for ActionsGuard."""

    def __init__(self, config: Config):
        """
        Initialize scanner.

        Args:
            config: Scanner configuration
        """
        self.config = config
        self.github_client = GitHubClient(config.github_token)
        self.scorecard_runner = ScorecardRunner(timeout=config.scorecard_timeout)
        self.workflow_analyzer = WorkflowAnalyzer()

    def scan_repository(self, repo: Repository) -> ScanResult:
        """
        Scan a single repository.

        Args:
            repo: GitHub repository object

        Returns:
            ScanResult object
        """
        repo_name = repo.full_name
        repo_url = repo.html_url

        logger.info(f"Scanning repository: {repo_name}")

        try:
            # Check if repo has workflows
            if not self.github_client.has_workflows(repo):
                logger.warning(f"Repository {repo_name} has no GitHub Actions workflows")
                return ScanResult(
                    repo_name=repo_name,
                    repo_url=repo_url,
                    score=10.0,  # No workflows = no risk
                    risk_level=RiskLevel.LOW,
                    scan_date=datetime.now(),
                    checks=[],
                    metadata={"has_workflows": False},
                )

            # Run scorecard
            checks_to_run = None if self.config.all_checks else self.config.checks
            scorecard_data = self.scorecard_runner.run_scorecard(
                repo_url=repo_url,
                checks=checks_to_run,
                github_token=self.config.github_token,
            )

            # Parse results
            checks = self.scorecard_runner.parse_results(scorecard_data)
            score = self.scorecard_runner.get_overall_score(scorecard_data)
            metadata = self.scorecard_runner.get_metadata(scorecard_data)
            metadata["has_workflows"] = True

            # Analyze workflows for detailed findings
            workflows = self.workflow_analyzer.analyze_scorecard_results(
                scorecard_data, checks
            )

            result = ScanResult(
                repo_name=repo_name,
                repo_url=repo_url,
                score=score,
                risk_level=ScanResult.calculate_risk_level(score),
                scan_date=datetime.now(),
                checks=checks,
                workflows=workflows,
                metadata=metadata,
            )

            logger.info(
                f"Completed scan for {repo_name}: "
                f"score={score:.1f}, risk={result.risk_level.value}"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to scan {repo_name}: {str(e)}")
            return ScanResult(
                repo_name=repo_name,
                repo_url=repo_url,
                score=0.0,
                risk_level=RiskLevel.CRITICAL,
                scan_date=datetime.now(),
                checks=[],
                error=str(e),
            )

    def scan_repositories(
        self,
        repos: List[Repository],
        parallel: bool = True
    ) -> List[ScanResult]:
        """
        Scan multiple repositories.

        Args:
            repos: List of repository objects
            parallel: Run scans in parallel

        Returns:
            List of ScanResult objects
        """
        if not repos:
            logger.warning("No repositories to scan")
            return []

        logger.info(f"Starting scan of {len(repos)} repositories")
        start_time = time.time()

        if parallel and len(repos) > 1:
            results = self._scan_parallel(repos)
        else:
            results = [self.scan_repository(repo) for repo in repos]

        duration = time.time() - start_time
        logger.info(f"Completed scanning {len(repos)} repositories in {duration:.1f}s")

        return results

    def _scan_parallel(self, repos: List[Repository]) -> List[ScanResult]:
        """
        Scan repositories in parallel.

        Args:
            repos: List of repository objects

        Returns:
            List of ScanResult objects
        """
        results = []
        with ThreadPoolExecutor(max_workers=self.config.parallel_scans) as executor:
            # Submit all tasks
            future_to_repo = {
                executor.submit(self.scan_repository, repo): repo
                for repo in repos
            }

            # Collect results as they complete
            for future in as_completed(future_to_repo):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    repo = future_to_repo[future]
                    logger.error(f"Unexpected error scanning {repo.full_name}: {e}")
                    results.append(
                        ScanResult(
                            repo_name=repo.full_name,
                            repo_url=repo.html_url,
                            score=0.0,
                            risk_level=RiskLevel.CRITICAL,
                            scan_date=datetime.now(),
                            error=str(e),
                        )
                    )

        return results

    def scan_organization(
        self,
        org_name: str,
        exclude: Optional[List[str]] = None,
        only: Optional[List[str]] = None,
    ) -> ScanSummary:
        """
        Scan all repositories in an organization.

        Args:
            org_name: Organization name
            exclude: List of repo names to exclude
            only: List of repo names to include (if set, only these repos)

        Returns:
            ScanSummary object
        """
        start_time = time.time()

        # Get repositories
        repos = self.github_client.get_organization_repos(
            org_name=org_name,
            exclude=exclude,
            only=only,
        )

        if not repos:
            logger.warning(f"No repositories found in organization: {org_name}")
            return ScanSummary(
                total_repos=0,
                successful_scans=0,
                failed_scans=0,
                average_score=0.0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                results=[],
                scan_duration=time.time() - start_time,
            )

        # Scan repositories
        results = self.scan_repositories(repos, parallel=True)

        # Create summary
        duration = time.time() - start_time
        summary = ScanSummary.from_results(results, scan_duration=duration)

        logger.info(
            f"Organization scan complete: {summary.successful_scans} successful, "
            f"{summary.failed_scans} failed, avg score: {summary.average_score:.1f}"
        )

        return summary

    def scan_user(
        self,
        username: Optional[str] = None,
        exclude: Optional[List[str]] = None,
        only: Optional[List[str]] = None,
        include_forks: bool = False,
    ) -> ScanSummary:
        """
        Scan all repositories for a user account.

        Args:
            username: GitHub username (if None, uses authenticated user)
            exclude: List of repo names to exclude
            only: List of repo names to include (if set, only these repos)
            include_forks: Whether to include forked repositories (default: False)

        Returns:
            ScanSummary object
        """
        start_time = time.time()

        # Get repositories
        repos = self.github_client.get_user_repos(
            username=username,
            exclude=exclude,
            only=only,
            include_forks=include_forks,
        )

        if not repos:
            user_display = username if username else "authenticated user"
            logger.warning(f"No repositories found for user: {user_display}")
            return ScanSummary(
                total_repos=0,
                successful_scans=0,
                failed_scans=0,
                average_score=0.0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                results=[],
                scan_duration=time.time() - start_time,
            )

        # Scan repositories
        results = self.scan_repositories(repos, parallel=True)

        # Create summary
        duration = time.time() - start_time
        summary = ScanSummary.from_results(results, scan_duration=duration)

        user_display = username if username else "authenticated user"
        logger.info(
            f"User scan complete for {user_display}: {summary.successful_scans} successful, "
            f"{summary.failed_scans} failed, avg score: {summary.average_score:.1f}"
        )

        return summary

    def scan_single_repository(self, repo_full_name: str) -> ScanResult:
        """
        Scan a single repository by name.

        Args:
            repo_full_name: Repository in format 'owner/repo'

        Returns:
            ScanResult object
        """
        repo = self.github_client.get_repository(repo_full_name)
        return self.scan_repository(repo)
