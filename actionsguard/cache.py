"""Result caching for ActionsGuard to avoid re-scanning recently scanned repositories."""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from actionsguard.models import ScanResult

logger = logging.getLogger("actionsguard")


class ResultCache:
    """Cache scan results to avoid re-scanning recently scanned repositories."""

    def __init__(self, cache_dir: str = "./.actionsguard_cache", ttl_hours: int = 24):
        """
        Initialize result cache.

        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live in hours for cached results (default: 24)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Create .gitignore in cache directory
        gitignore = self.cache_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n!.gitignore\n")

    def _get_cache_key(self, repo_name: str, checks: list) -> str:
        """
        Generate cache key for a repository and check combination.

        Args:
            repo_name: Repository full name (owner/repo)
            checks: List of checks being run

        Returns:
            Cache key string
        """
        # Create hash of repo_name + sorted checks
        check_str = ",".join(sorted(checks))
        key_input = f"{repo_name}:{check_str}"
        return hashlib.sha256(key_input.encode()).hexdigest()[:16]

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get path to cache file for a given key."""
        return self.cache_dir / f"{cache_key}.json"

    def get(self, repo_name: str, checks: list) -> Optional[ScanResult]:
        """
        Get cached result for a repository if available and fresh.

        Args:
            repo_name: Repository full name
            checks: List of checks being run

        Returns:
            Cached ScanResult if available and fresh, None otherwise
        """
        cache_key = self._get_cache_key(repo_name, checks)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            logger.debug(f"No cache found for {repo_name}")
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Check if cache is still fresh
            cached_time = datetime.fromisoformat(data["cached_at"])
            age = datetime.now() - cached_time

            if age > self.ttl:
                logger.debug(f"Cache expired for {repo_name} (age: {age})")
                # Clean up expired cache
                cache_path.unlink()
                return None

            logger.info(f"Using cached result for {repo_name} (age: {age})")

            # Reconstruct ScanResult from cached data
            result_data = data["result"]
            # Convert ISO format back to datetime
            result_data["scan_date"] = datetime.fromisoformat(result_data["scan_date"])

            # Import here to avoid circular dependency
            from actionsguard.models import (
                ScanResult,
                CheckResult,
                WorkflowAnalysis,
                WorkflowFinding,
                RiskLevel,
                Status,
                Severity,
            )

            # Reconstruct checks
            checks_list = []
            for check_data in result_data.get("checks", []):
                checks_list.append(
                    CheckResult(
                        name=check_data["name"],
                        score=check_data["score"],
                        status=Status(check_data["status"]),
                        reason=check_data["reason"],
                        documentation_url=check_data["documentation_url"],
                        severity=Severity(check_data["severity"]),
                        details=check_data.get("details"),
                    )
                )

            # Reconstruct workflows
            workflows_list = []
            for workflow_data in result_data.get("workflows", []):
                findings = []
                for finding_data in workflow_data.get("findings", []):
                    findings.append(
                        WorkflowFinding(
                            workflow_path=finding_data["workflow_path"],
                            check_name=finding_data["check_name"],
                            severity=Severity(finding_data["severity"]),
                            message=finding_data["message"],
                            line_number=finding_data.get("line_number"),
                            snippet=finding_data.get("snippet"),
                            recommendation=finding_data.get("recommendation"),
                        )
                    )

                workflows_list.append(
                    WorkflowAnalysis(
                        path=workflow_data["path"],
                        findings=findings,
                        score=workflow_data.get("score"),
                    )
                )

            result = ScanResult(
                repo_name=result_data["repo_name"],
                repo_url=result_data["repo_url"],
                score=result_data["score"],
                risk_level=RiskLevel(result_data["risk_level"]),
                scan_date=result_data["scan_date"],
                checks=checks_list,
                workflows=workflows_list,
                metadata=result_data.get("metadata", {}),
                error=result_data.get("error"),
            )

            return result

        except Exception as e:
            logger.warning(f"Failed to load cache for {repo_name}: {e}")
            # Clean up corrupted cache
            if cache_path.exists():
                cache_path.unlink()
            return None

    def set(self, repo_name: str, checks: list, result: ScanResult) -> None:
        """
        Cache a scan result.

        Args:
            repo_name: Repository full name
            checks: List of checks that were run
            result: ScanResult to cache
        """
        cache_key = self._get_cache_key(repo_name, checks)
        cache_path = self._get_cache_path(cache_key)

        try:
            # Convert result to dict for JSON storage
            result_dict = result.to_dict()

            cache_data = {
                "cached_at": datetime.now().isoformat(),
                "repo_name": repo_name,
                "checks": checks,
                "result": result_dict,
            }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug(f"Cached result for {repo_name}")

        except Exception as e:
            logger.warning(f"Failed to cache result for {repo_name}: {e}")

    def clear(self, repo_name: Optional[str] = None) -> int:
        """
        Clear cached results.

        Args:
            repo_name: If provided, clear only this repo. Otherwise clear all.

        Returns:
            Number of cache entries cleared
        """
        if repo_name:
            # Clear specific repo (all check combinations)
            count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    if data.get("repo_name") == repo_name:
                        cache_file.unlink()
                        count += 1
                except Exception:
                    pass
            logger.info(f"Cleared {count} cache entries for {repo_name}")
            return count
        else:
            # Clear all cache
            count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
            logger.info(f"Cleared all {count} cache entries")
            return count

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total = 0
        fresh = 0
        expired = 0
        total_size = 0

        for cache_file in self.cache_dir.glob("*.json"):
            total += 1
            total_size += cache_file.stat().st_size

            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                cached_time = datetime.fromisoformat(data["cached_at"])
                age = datetime.now() - cached_time

                if age <= self.ttl:
                    fresh += 1
                else:
                    expired += 1
            except Exception:
                expired += 1

        return {
            "total_entries": total,
            "fresh_entries": fresh,
            "expired_entries": expired,
            "total_size_bytes": total_size,
            "cache_dir": str(self.cache_dir),
            "ttl_hours": self.ttl.total_seconds() / 3600,
        }
