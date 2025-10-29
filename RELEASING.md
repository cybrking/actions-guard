# Release Process for ActionsGuard

This document describes how to create new releases and publish them to PyPI automatically.

## Overview

ActionsGuard uses GitHub Actions to automatically publish to PyPI when a new version tag is pushed. The workflow:

1. Runs all tests
2. Builds distribution packages
3. Publishes to PyPI using Trusted Publishing
4. Builds and pushes Docker images
5. Creates a GitHub Release

## Prerequisites

### One-Time Setup: Configure PyPI Trusted Publishing

Trusted Publishing is the secure, recommended way to publish to PyPI without using API tokens.

1. Go to https://pypi.org/manage/account/publishing/
2. Scroll to "Add a new pending publisher"
3. Fill in the following:
   - **PyPI Project Name:** `actionsguard`
   - **Owner:** `cybrking`
   - **Repository name:** `actions-guard`
   - **Workflow name:** `release.yml`
   - **Environment name:** (leave blank)
4. Click "Add"

> **Note:** You only need to do this once. After the first successful publish, PyPI will automatically trust future releases from this workflow.

## Creating a New Release

### Step 1: Update Version Number

Update the version in `/home/user/actions-guard/pyproject.toml`:

```toml
[project]
name = "actionsguard"
version = "1.0.1"  # Update this
```

Also update `/home/user/actions-guard/actionsguard/__version__.py`:

```python
__version__ = "1.0.1"  # Update this
```

### Step 2: Update CHANGELOG.md

Add release notes to `CHANGELOG.md`:

```markdown
## [1.0.1] - 2025-01-15

### Added
- New feature description

### Fixed
- Bug fix description

### Changed
- Changes description
```

### Step 3: Commit Changes

```bash
git add pyproject.toml actionsguard/__version__.py CHANGELOG.md
git commit -m "Bump version to 1.0.1"
git push origin main
```

### Step 4: Create and Push Version Tag

```bash
# Create an annotated tag
git tag -a v1.0.1 -m "Release version 1.0.1"

# Push the tag to GitHub
git push origin v1.0.1
```

### Step 5: Monitor the Workflow

1. Go to https://github.com/cybrking/actions-guard/actions
2. Watch the "Release" workflow run
3. Verify all jobs complete successfully:
   - ✅ Run Tests
   - ✅ Publish to PyPI
   - ✅ Build and Push Docker Image
   - ✅ Create GitHub Release

### Step 6: Verify Publication

1. **Check PyPI:** https://pypi.org/project/actionsguard/
2. **Test installation:**
   ```bash
   pip install --upgrade actionsguard
   actionsguard --version
   ```
3. **Check GitHub Release:** https://github.com/cybrking/actions-guard/releases

## Version Numbering

ActionsGuard follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version (1.x.x): Incompatible API changes
- **MINOR** version (x.1.x): New functionality in a backward compatible manner
- **PATCH** version (x.x.1): Backward compatible bug fixes

Examples:
- Bug fix: `1.0.0` → `1.0.1`
- New feature: `1.0.1` → `1.1.0`
- Breaking change: `1.1.0` → `2.0.0`

## Troubleshooting

### Workflow Fails with "PyPI Trusted Publishing not configured"

**Solution:** Complete the PyPI Trusted Publishing setup (see Prerequisites above).

### Tests Fail During Release

**Solution:**
1. Cancel the release
2. Delete the tag: `git tag -d v1.0.1 && git push origin :refs/tags/v1.0.1`
3. Fix the failing tests
4. Retry the release process

### Wrong Version Number Released

**Solution:**
1. Yank the incorrect version on PyPI: https://pypi.org/manage/project/actionsguard/releases/
2. Fix the version number
3. Create a new tag with the correct version

### Docker Build Fails

**Solution:** The Docker build failure won't prevent PyPI publication. You can:
1. Fix the Dockerfile issue
2. Create a new patch release, or
3. Manually build and push the Docker image

## Manual Release (Emergency)

If the automated workflow fails and you need to publish immediately:

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build packages
python -m build

# Upload to PyPI (requires API token)
python -m twine upload dist/*
```

**Username:** `__token__`
**Password:** Your PyPI API token

## Rollback a Release

PyPI doesn't allow deleting or replacing releases. If you need to rollback:

1. **Yank the bad release** on PyPI (keeps it available but discourages use)
2. **Release a new version** with the fixes
3. **Communicate** the issue to users via GitHub Release notes

## Quick Reference

```bash
# Update version files
vim pyproject.toml actionsguard/__version__.py CHANGELOG.md

# Commit and push
git add -A
git commit -m "Bump version to X.Y.Z"
git push origin main

# Create and push tag
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z

# Monitor: https://github.com/cybrking/actions-guard/actions
# Verify: https://pypi.org/project/actionsguard/
```

---

**Questions?** Open an issue at https://github.com/cybrking/actions-guard/issues
