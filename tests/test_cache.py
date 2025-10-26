"""Tests for result caching."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from actionsguard.cache import ResultCache
from actionsguard.models import ScanResult, RiskLevel


@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def cache(temp_cache_dir):
    """Create a ResultCache instance."""
    return ResultCache(cache_dir=temp_cache_dir, ttl_hours=24)


@pytest.fixture
def sample_result():
    """Create a sample scan result."""
    return ScanResult(
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        score=7.5,
        risk_level=RiskLevel.MEDIUM,
        scan_date=datetime.now(),
        checks=[],
        workflows=[],
        metadata={"has_workflows": True}
    )


def test_cache_initialization(cache, temp_cache_dir):
    """Test cache directory creation."""
    cache_path = Path(temp_cache_dir)
    assert cache_path.exists()
    assert cache_path.is_dir()

    gitignore = cache_path / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text()
    assert "*" in content


def test_cache_key_generation(cache):
    """Test cache key generation."""
    key1 = cache._get_cache_key("owner/repo", ["check1", "check2"])
    key2 = cache._get_cache_key("owner/repo", ["check2", "check1"])  # Different order
    key3 = cache._get_cache_key("owner/repo", ["check1"])  # Different checks

    # Same checks in different order should produce same key
    assert key1 == key2

    # Different checks should produce different key
    assert key1 != key3


def test_cache_set_and_get(cache, sample_result):
    """Test caching and retrieving results."""
    checks = ["Dangerous-Workflow", "Token-Permissions"]

    # Cache should be empty initially
    cached = cache.get("owner/repo", checks)
    assert cached is None

    # Set cache
    cache.set("owner/repo", checks, sample_result)

    # Retrieve from cache
    cached = cache.get("owner/repo", checks)
    assert cached is not None
    assert cached.repo_name == sample_result.repo_name
    assert cached.score == sample_result.score
    assert cached.risk_level == sample_result.risk_level


def test_cache_expiration(temp_cache_dir, sample_result):
    """Test cache expiration."""
    # Create cache with 1 hour TTL
    cache = ResultCache(cache_dir=temp_cache_dir, ttl_hours=1)
    checks = ["Dangerous-Workflow"]

    # Cache the result
    cache.set("owner/repo", checks, sample_result)

    # Should be available
    cached = cache.get("owner/repo", checks)
    assert cached is not None

    # Manually modify cache file to simulate expired cache
    cache_key = cache._get_cache_key("owner/repo", checks)
    cache_path = cache._get_cache_path(cache_key)

    with open(cache_path, 'r') as f:
        data = json.load(f)

    # Set cache time to 2 hours ago
    expired_time = datetime.now() - timedelta(hours=2)
    data['cached_at'] = expired_time.isoformat()

    with open(cache_path, 'w') as f:
        json.dump(data, f)

    # Should return None for expired cache
    cached = cache.get("owner/repo", checks)
    assert cached is None

    # Cache file should be deleted
    assert not cache_path.exists()


def test_cache_with_different_checks(cache, sample_result):
    """Test that different check combinations are cached separately."""
    checks1 = ["Dangerous-Workflow"]
    checks2 = ["Token-Permissions"]

    # Cache same repo with different checks
    cache.set("owner/repo", checks1, sample_result)

    # Should not find cache for different checks
    cached = cache.get("owner/repo", checks2)
    assert cached is None

    # Should find cache for original checks
    cached = cache.get("owner/repo", checks1)
    assert cached is not None


def test_cache_clear_specific_repo(cache, sample_result):
    """Test clearing cache for specific repository."""
    cache.set("owner/repo1", ["check1"], sample_result)
    cache.set("owner/repo2", ["check1"], sample_result)

    # Clear cache for repo1
    count = cache.clear("owner/repo1")
    assert count >= 1

    # repo1 cache should be cleared
    assert cache.get("owner/repo1", ["check1"]) is None

    # repo2 cache should still exist
    assert cache.get("owner/repo2", ["check1"]) is not None


def test_cache_clear_all(cache, sample_result):
    """Test clearing all cache."""
    cache.set("owner/repo1", ["check1"], sample_result)
    cache.set("owner/repo2", ["check1"], sample_result)

    # Clear all cache
    count = cache.clear()
    assert count == 2

    # Both should be cleared
    assert cache.get("owner/repo1", ["check1"]) is None
    assert cache.get("owner/repo2", ["check1"]) is None


def test_cache_stats(cache, sample_result):
    """Test cache statistics."""
    # Empty cache
    stats = cache.stats()
    assert stats['total_entries'] == 0
    assert stats['fresh_entries'] == 0

    # Add some entries
    cache.set("owner/repo1", ["check1"], sample_result)
    cache.set("owner/repo2", ["check1"], sample_result)

    stats = cache.stats()
    assert stats['total_entries'] == 2
    assert stats['fresh_entries'] == 2
    assert stats['expired_entries'] == 0
    assert stats['total_size_bytes'] > 0
    assert stats['ttl_hours'] == 24


def test_cache_corrupted_file(cache, sample_result, temp_cache_dir):
    """Test handling of corrupted cache files."""
    checks = ["check1"]
    cache.set("owner/repo", checks, sample_result)

    # Corrupt the cache file
    cache_key = cache._get_cache_key("owner/repo", checks)
    cache_path = cache._get_cache_path(cache_key)

    with open(cache_path, 'w') as f:
        f.write("invalid json{")

    # Should return None and clean up corrupted file
    cached = cache.get("owner/repo", checks)
    assert cached is None
    assert not cache_path.exists()


def test_cache_with_workflow_findings(cache):
    """Test caching results with workflow findings."""
    from actionsguard.models import WorkflowAnalysis, WorkflowFinding, Severity

    finding = WorkflowFinding(
        workflow_path=".github/workflows/ci.yml",
        check_name="Dangerous-Workflow",
        severity=Severity.HIGH,
        message="Issue found",
        line_number=10,
        recommendation="Fix it"
    )

    workflow = WorkflowAnalysis(
        path=".github/workflows/ci.yml",
        findings=[finding],
        score=5.0
    )

    result = ScanResult(
        repo_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        score=5.0,
        risk_level=RiskLevel.HIGH,
        scan_date=datetime.now(),
        checks=[],
        workflows=[workflow],
        metadata={}
    )

    checks = ["Dangerous-Workflow"]
    cache.set("owner/repo", checks, result)

    # Retrieve from cache
    cached = cache.get("owner/repo", checks)
    assert cached is not None
    assert len(cached.workflows) == 1
    assert cached.workflows[0].path == ".github/workflows/ci.yml"
    assert len(cached.workflows[0].findings) == 1
    assert cached.workflows[0].findings[0].message == "Issue found"
    assert cached.workflows[0].findings[0].line_number == 10
