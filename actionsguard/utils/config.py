"""Configuration management for ActionsGuard."""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    """Configuration for ActionsGuard scanner."""

    github_token: Optional[str] = field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN")
    )
    output_dir: str = "./reports"
    formats: List[str] = field(default_factory=lambda: ["json", "html", "csv", "markdown"])
    checks: List[str] = field(
        default_factory=lambda: [
            "Dangerous-Workflow",
            "Token-Permissions",
            "Pinned-Dependencies",
        ]
    )
    fail_on_critical: bool = False
    verbose: bool = False
    parallel_scans: int = 5
    scorecard_timeout: int = 300  # 5 minutes

    def validate(self) -> None:
        """Validate configuration."""
        if not self.github_token:
            raise ValueError(
                "GitHub token not found. Set GITHUB_TOKEN environment variable "
                "or use --token flag."
            )

    @property
    def all_checks(self) -> bool:
        """Check if all scorecard checks should be run."""
        return "all" in [c.lower() for c in self.checks]
