"""Tests for configuration management."""

import pytest
import tempfile
import os
from pathlib import Path

from actionsguard.utils.config import Config


@pytest.fixture
def temp_config_file():
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yield f.name
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


def test_config_defaults():
    """Test default configuration values."""
    config = Config()

    assert config.output_dir == "./reports"
    assert "json" in config.formats
    assert "html" in config.formats
    assert "Dangerous-Workflow" in config.checks
    assert config.fail_on_critical is False
    assert config.verbose is False
    assert config.parallel_scans == 5
    assert config.scorecard_timeout == 300
    assert config.use_cache is True
    assert config.cache_ttl == 24


def test_config_with_custom_values():
    """Test configuration with custom values."""
    config = Config(
        output_dir="./custom-reports",
        formats=["json"],
        checks=["all"],
        fail_on_critical=True,
        verbose=True,
        parallel_scans=10,
        use_cache=False,
    )

    assert config.output_dir == "./custom-reports"
    assert config.formats == ["json"]
    assert config.checks == ["all"]
    assert config.fail_on_critical is True
    assert config.verbose is True
    assert config.parallel_scans == 10
    assert config.use_cache is False


def test_config_all_checks_property():
    """Test all_checks property."""
    config1 = Config(checks=["Dangerous-Workflow"])
    assert config1.all_checks is False

    config2 = Config(checks=["all"])
    assert config2.all_checks is True

    config3 = Config(checks=["All"])  # Case insensitive
    assert config3.all_checks is True


def test_config_validate_with_token(monkeypatch):
    """Test config validation with token."""
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")

    config = Config()
    config.validate()  # Should not raise


def test_config_validate_without_token(monkeypatch):
    """Test config validation without token."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    config = Config(github_token=None)

    with pytest.raises(ValueError, match="GitHub token not found"):
        config.validate()


def test_config_from_yaml_file(temp_config_file):
    """Test loading config from YAML file."""
    yaml_content = """
output_dir: ./test-reports
formats:
  - json
  - html
checks:
  - Dangerous-Workflow
  - Token-Permissions
fail_on_critical: true
verbose: false
parallel_scans: 3
use_cache: false
cache_ttl: 12
"""

    with open(temp_config_file, "w") as f:
        f.write(yaml_content)

    config = Config.from_file(temp_config_file)

    assert config.output_dir == "./test-reports"
    assert config.formats == ["json", "html"]
    assert "Dangerous-Workflow" in config.checks
    assert "Token-Permissions" in config.checks
    assert config.fail_on_critical is True
    assert config.verbose is False
    assert config.parallel_scans == 3
    assert config.use_cache is False
    assert config.cache_ttl == 12


def test_config_from_json_file():
    """Test loading config from JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json_content = """{
  "output_dir": "./json-reports",
  "formats": ["json"],
  "checks": ["all"],
  "fail_on_critical": true,
  "parallel_scans": 8,
  "use_cache": true,
  "cache_ttl": 48
}"""
        f.write(json_content)
        f.flush()

        try:
            config = Config.from_file(f.name)

            assert config.output_dir == "./json-reports"
            assert config.formats == ["json"]
            assert config.checks == ["all"]
            assert config.fail_on_critical is True
            assert config.parallel_scans == 8
            assert config.use_cache is True
            assert config.cache_ttl == 48
        finally:
            os.unlink(f.name)


def test_config_from_file_not_found():
    """Test loading config from non-existent file."""
    with pytest.raises(FileNotFoundError):
        Config.from_file("/nonexistent/config.yml")


def test_config_from_file_invalid_format():
    """Test loading config from invalid file format."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("some content")
        f.flush()

        try:
            with pytest.raises(ValueError, match="Unsupported config file format"):
                Config.from_file(f.name)
        finally:
            os.unlink(f.name)


def test_config_from_file_invalid_yaml():
    """Test loading config from invalid YAML."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write("invalid: yaml: content::")
        f.flush()

        try:
            with pytest.raises(ValueError, match="Invalid YAML"):
                Config.from_file(f.name)
        finally:
            os.unlink(f.name)


def test_config_from_file_invalid_json():
    """Test loading config from invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"invalid": json}')
        f.flush()

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                Config.from_file(f.name)
        finally:
            os.unlink(f.name)


def test_config_from_file_env_var_precedence(temp_config_file, monkeypatch):
    """Test that environment variable takes precedence over config file."""
    yaml_content = """
github_token: file_token
output_dir: ./reports
"""

    with open(temp_config_file, "w") as f:
        f.write(yaml_content)

    # Set environment variable
    monkeypatch.setenv("GITHUB_TOKEN", "env_token")

    config = Config.from_file(temp_config_file)

    # Env var should take precedence
    assert config.github_token == "env_token"


def test_config_to_dict():
    """Test converting config to dictionary."""
    config = Config(output_dir="./test", formats=["json"], checks=["check1"], fail_on_critical=True)

    config_dict = config.to_dict()

    assert config_dict["output_dir"] == "./test"
    assert config_dict["formats"] == ["json"]
    assert config_dict["checks"] == ["check1"]
    assert config_dict["fail_on_critical"] is True


def test_config_from_dict():
    """Test creating config from dictionary."""
    data = {
        "output_dir": "./dict-reports",
        "formats": ["html"],
        "checks": ["check1", "check2"],
        "parallel_scans": 7,
        "unknown_field": "should be ignored",
    }

    config = Config.from_dict(data)

    assert config.output_dir == "./dict-reports"
    assert config.formats == ["html"]
    assert config.checks == ["check1", "check2"]
    assert config.parallel_scans == 7
    # Unknown fields should be filtered out
    assert not hasattr(config, "unknown_field")


def test_config_to_file_yaml(temp_config_file):
    """Test saving config to YAML file."""
    config = Config(
        output_dir="./test-save",
        formats=["json", "html"],
        checks=["check1"],
        fail_on_critical=True,
        github_token="should_not_save",  # Should not be saved
    )

    yaml_path = temp_config_file.replace(".yml", "_save.yml")

    try:
        config.to_file(yaml_path)

        # Load and verify
        with open(yaml_path, "r") as f:
            import yaml

            data = yaml.safe_load(f)

        assert data["output_dir"] == "./test-save"
        assert data["fail_on_critical"] is True
        # Token should be None for security
        assert data["github_token"] is None

    finally:
        if os.path.exists(yaml_path):
            os.unlink(yaml_path)


def test_config_to_file_json():
    """Test saving config to JSON file."""
    config = Config(output_dir="./json-save", formats=["json"], github_token="should_not_save")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json_path = f.name

    try:
        config.to_file(json_path)

        # Load and verify
        with open(json_path, "r") as f:
            import json

            data = json.load(f)

        assert data["output_dir"] == "./json-save"
        # Token should be None
        assert data["github_token"] is None

    finally:
        if os.path.exists(json_path):
            os.unlink(json_path)
