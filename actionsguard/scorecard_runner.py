"""OpenSSF Scorecard runner for ActionsGuard."""

import json
import logging
import subprocess
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime

from actionsguard.models import CheckResult, Status, Severity


logger = logging.getLogger("actionsguard")


class ScorecardRunner:
    """Runner for OpenSSF Scorecard CLI."""

    def __init__(self, timeout: int = 300):
        """
        Initialize Scorecard runner.

        Args:
            timeout: Maximum time (seconds) to run scorecard
        """
        self.timeout = timeout
        self._check_installation()

    def _check_installation(self) -> None:
        """
        Check if scorecard CLI is installed.

        Raises:
            RuntimeError: If scorecard is not found
        """
        if not shutil.which("scorecard"):
            raise RuntimeError(
                "OpenSSF Scorecard not found. Install it with:\n"
                "  go install github.com/ossf/scorecard/v5/cmd/scorecard@latest\n"
                "Or download from: https://github.com/ossf/scorecard/releases"
            )
        logger.debug("Scorecard CLI found")

    def run_scorecard(
        self,
        repo_url: str,
        checks: Optional[List[str]] = None,
        github_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run Scorecard on a repository.

        Args:
            repo_url: Repository URL or full name (owner/repo)
            checks: List of specific checks to run (None = all checks)
            github_token: GitHub token for API access

        Returns:
            Scorecard results as dictionary

        Raises:
            RuntimeError: If scorecard execution fails
            TimeoutError: If scorecard times out
        """
        # Build command
        cmd = [
            "scorecard",
            f"--repo={repo_url}",
            "--format=json",
            "--show-details",
        ]

        # Add specific checks if requested
        if checks:
            for check in checks:
                cmd.append(f"--checks={check}")

        # Set environment
        env = {}
        if github_token:
            env["GITHUB_TOKEN"] = github_token
            env["GITHUB_AUTH_TOKEN"] = github_token

        logger.debug(f"Running scorecard: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**subprocess.os.environ, **env}
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Scorecard failed: {error_msg}")
                raise RuntimeError(f"Scorecard execution failed: {error_msg}")

            # Parse JSON output
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse scorecard output: {e}")
                logger.debug(f"Output was: {result.stdout[:500]}")
                raise RuntimeError(f"Failed to parse scorecard output: {e}")

        except subprocess.TimeoutExpired:
            logger.error(f"Scorecard timed out after {self.timeout} seconds")
            raise TimeoutError(
                f"Scorecard execution timed out after {self.timeout} seconds"
            )

    def parse_results(self, scorecard_data: Dict[str, Any]) -> List[CheckResult]:
        """
        Parse Scorecard JSON output into CheckResult objects.

        Args:
            scorecard_data: Raw scorecard JSON data

        Returns:
            List of CheckResult objects
        """
        checks = []

        for check in scorecard_data.get("checks", []):
            name = check.get("name", "Unknown")
            score = check.get("score", 0)
            reason = check.get("reason", "No reason provided")
            doc_url = check.get("documentation", {}).get("url", "")

            # Map score to status
            if score == -1:
                status = Status.SKIP
            elif score >= 7:
                status = Status.PASS
            elif score >= 4:
                status = Status.WARN
            else:
                status = Status.FAIL

            # Calculate severity based on score
            severity = CheckResult.calculate_severity(score if score != -1 else 10)

            # Extract details
            details = {
                "short": check.get("documentation", {}).get("short", ""),
                "details": check.get("details", []),
            }

            checks.append(
                CheckResult(
                    name=name,
                    score=max(score, 0),  # Convert -1 to 0 for skipped
                    status=status,
                    reason=reason,
                    documentation_url=doc_url,
                    severity=severity,
                    details=details,
                )
            )

        return checks

    def get_overall_score(self, scorecard_data: Dict[str, Any]) -> float:
        """
        Extract overall score from scorecard results.

        Args:
            scorecard_data: Raw scorecard JSON data

        Returns:
            Overall score (0.0-10.0)
        """
        score = scorecard_data.get("score", 0.0)
        return float(score)

    def get_metadata(self, scorecard_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from scorecard results.

        Args:
            scorecard_data: Raw scorecard JSON data

        Returns:
            Metadata dictionary
        """
        return {
            "scorecard_version": scorecard_data.get("scorecard", {}).get("version", "unknown"),
            "scorecard_commit": scorecard_data.get("scorecard", {}).get("commit", "unknown"),
            "repo": scorecard_data.get("repo", {}).get("name", ""),
            "commit": scorecard_data.get("repo", {}).get("commit", ""),
            "scan_timestamp": scorecard_data.get("date", datetime.now().isoformat()),
        }
