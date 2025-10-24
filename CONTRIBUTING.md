# Contributing to ActionsGuard

Thank you for your interest in contributing to ActionsGuard! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:

1. A clear, descriptive title
2. Steps to reproduce the issue
3. Expected behavior
4. Actual behavior
5. Environment details (OS, Python version, etc.)
6. Relevant logs or screenshots

### Suggesting Features

Feature requests are welcome! Please create an issue with:

1. A clear description of the feature
2. Use case and motivation
3. Proposed implementation approach (if applicable)
4. Any alternatives you've considered

### Pull Requests

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Set up development environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Make your changes**
   - Write clear, commented code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

4. **Run tests and quality checks**
   ```bash
   # Run tests
   pytest tests/ -v --cov=actionsguard

   # Format code
   black actionsguard/ tests/

   # Lint
   flake8 actionsguard/ tests/

   # Type check
   mypy actionsguard/
   ```

5. **Commit your changes**
   ```bash
   git commit -m "Add feature: description"
   ```

   Use clear commit messages:
   - `feat: Add new feature`
   - `fix: Fix bug in scanner`
   - `docs: Update README`
   - `test: Add tests for reporter`
   - `refactor: Improve code structure`

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request**
   - Provide a clear title and description
   - Reference any related issues
   - Ensure all CI checks pass

## Development Guidelines

### Code Style

- Follow PEP 8 style guide
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible
- Use meaningful variable and function names

### Testing

- Write tests for all new functionality
- Maintain test coverage above 80%
- Use pytest fixtures for common test setups
- Mock external dependencies (GitHub API, Scorecard CLI)

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all public APIs
- Include examples in docstrings
- Update CHANGELOG.md with your changes

## Project Structure

```
actionsguard/
├── actionsguard/          # Main package
│   ├── cli.py            # CLI interface
│   ├── scanner.py        # Core scanning logic
│   ├── github_client.py  # GitHub API wrapper
│   ├── scorecard_runner.py # Scorecard integration
│   ├── models.py         # Data models
│   ├── reporters/        # Report generators
│   └── utils/            # Utility modules
├── tests/                # Test suite
├── .github/              # GitHub workflows
└── docs/                 # Documentation
```

## Development Workflow

1. Check existing issues or create a new one
2. Discuss your approach in the issue
3. Fork and create a feature branch
4. Implement your changes with tests
5. Run all quality checks
6. Submit a pull request
7. Address review feedback
8. Celebrate your contribution!

## Need Help?

- Check the [documentation](https://github.com/your-username/actionsguard/wiki)
- Ask in [GitHub Discussions](https://github.com/your-username/actionsguard/discussions)
- Reach out in the pull request or issue comments

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for making ActionsGuard better!
