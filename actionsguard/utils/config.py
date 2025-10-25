"""Configuration management for ActionsGuard."""

import os
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


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
    json_logs: bool = False  # Use structured JSON logging
    parallel_scans: int = 5
    scorecard_timeout: int = 300  # 5 minutes

    def validate(self) -> None:
        """Validate configuration."""
        if not self.github_token:
            raise ValueError(
                "GitHub token not found. Set GITHUB_TOKEN environment variable "
                "or use --token flag.\n\n"
                "💡 Quick fix:\n"
                "   export GITHUB_TOKEN='your_token_here'\n\n"
                "🔍 Debug: Run 'echo $GITHUB_TOKEN' to check if token is set"
            )

    @property
    def all_checks(self) -> bool:
        """Check if all scorecard checks should be run."""
        return "all" in [c.lower() for c in self.checks]

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """
        Load configuration from YAML or JSON file.

        Args:
            config_path: Path to configuration file (.yml, .yaml, or .json)

        Returns:
            Config instance loaded from file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If file format is unsupported or invalid
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Determine file type from extension
        ext = path.suffix.lower()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                if ext in ('.yml', '.yaml'):
                    data = yaml.safe_load(f)
                elif ext == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(
                        f"Unsupported config file format: {ext}. "
                        "Use .yml, .yaml, or .json"
                    )

            if not isinstance(data, dict):
                raise ValueError("Configuration file must contain a dictionary/object")

            # Create config from loaded data
            # Filter out unknown keys
            valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}

            # Merge with environment variables (env vars take precedence)
            if os.getenv("GITHUB_TOKEN"):
                filtered_data["github_token"] = os.getenv("GITHUB_TOKEN")

            return cls(**filtered_data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """
        Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Config instance
        """
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of config
        """
        return asdict(self)

    def to_file(self, config_path: str) -> None:
        """
        Save configuration to YAML or JSON file.

        Args:
            config_path: Path to save configuration file (.yml, .yaml, or .json)

        Raises:
            ValueError: If file format is unsupported
        """
        path = Path(config_path)
        ext = path.suffix.lower()

        data = self.to_dict()

        # Don't save the token to file for security
        if 'github_token' in data:
            data['github_token'] = None

        try:
            with open(path, 'w', encoding='utf-8') as f:
                if ext in ('.yml', '.yaml'):
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
                elif ext == '.json':
                    json.dump(data, f, indent=2)
                else:
                    raise ValueError(
                        f"Unsupported config file format: {ext}. "
                        "Use .yml, .yaml, or .json"
                    )
        except Exception as e:
            raise ValueError(f"Failed to write config file: {e}")
