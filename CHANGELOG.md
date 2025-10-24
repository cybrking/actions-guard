# Changelog

All notable changes to ActionsGuard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
