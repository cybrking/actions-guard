# Changelog

All notable changes to ActionsGuard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2025-01-29

### Changed
- Updated all documentation to use Python 3 commands (`python3` and `pip3`)
- Updated README.md installation and development instructions
- Updated CONTRIBUTING.md setup instructions
- Updated QUICKSTART.md installation steps
- Updated CI/CD integration examples for GitHub Actions, GitLab CI, and Jenkins

## [1.0.1] - 2025-01-15

### Added
- Automated PyPI publishing via GitHub Actions with Trusted Publishing
- Comprehensive release process documentation (RELEASING.md)

### Changed
- Updated README to reflect PyPI availability as primary installation method
- Improved documentation structure

### Fixed
- Updated repository URLs from placeholder to actual URLs
- Added missing pyyaml dependency to package requirements

## [1.0.0] - 2024-10-24

### Added
- Initial release of ActionsGuard
- CLI tool for scanning GitHub Actions workflows
- Support for scanning single repositories
- Support for scanning entire organizations
- Integration with OpenSSF Scorecard
- Multiple report formats (JSON, HTML, CSV, Markdown)
- Parallel repository scanning
- GitHub Action for CI/CD integration
- Comprehensive documentation and examples
- MIT License

### Features
- Repository filtering (exclude/only)
- Custom security check selection
- Configurable output directory and formats
- Fail-on-critical mode for CI/CD
- Beautiful HTML reports with risk scoring
- Rich CLI with progress indicators
- Rate limit handling
- Error recovery and reporting

### Checks
- Dangerous-Workflow detection
- Token-Permissions verification
- Pinned-Dependencies checking
- Support for all 18 OpenSSF Scorecard checks

[1.0.0]: https://github.com/your-username/actionsguard/releases/tag/v1.0.0
