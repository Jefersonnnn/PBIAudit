# Contributing Guidelines

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/powerbi-governance.git`
3. Create a branch: `git checkout -b feature/amazing-feature`
4. Install development dependencies: `poetry install --with dev`
5. Make your changes
6. Test: `poetry run pytest`
7. Push and open a Pull Request

## Development Setup

See [Development Guide](docs/DEVELOPMENT.md) for detailed setup instructions.

## Code Style

- Follow PEP 8 with Black formatting
- 120 character line length
- Type hints required
- Docstrings for all public functions

### Formatting

```bash
# Auto-fix issues
poetry run ruff check --fix .

# Format with Black
poetry run black src/ tests/

# Sort imports
poetry run isort src/ tests/
```

## Testing Requirements

- Minimum 80% coverage for new code
- All tests must pass
- Add tests for bug fixes and features

```bash
# Run tests
poetry run pytest

# With coverage report
poetry run pytest --cov=src/powerbi_governance --cov-report=html
```

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `refactor` - Code refactoring
- `perf` - Performance improvements
- `test` - Test additions/changes
- `chore` - Build/dependency changes

### Examples

```
feat(workspace): add workspace sync job
fix(auth): handle token expiration correctly
docs(setup): update installation guide
refactor(database): simplify session management
```

## Pull Request Process

1. Ensure all tests pass: `poetry run pytest`
2. Ensure code is formatted: `poetry run ruff check --fix .`
3. Ensure types are correct: `poetry run mypy src/powerbi_governance`
4. Update documentation as needed
5. Request review from maintainers

## Reporting Bugs

Use GitHub Issues with:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Python/OS version
- Error logs/tracebacks

## Feature Requests

Use GitHub Issues with:
- Clear use case
- Proposed solution (if any)
- Relevant examples

## Questions

- GitHub Discussions
- GitHub Issues (label: `question`)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- CHANGELOG.md
- README.md
- GitHub contributors page

---

Thank you for contributing! 🎉
