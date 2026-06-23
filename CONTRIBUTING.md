# Contributing to Quantara

Thank you for your interest in contributing to Quantara! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Prerequisites**: Docker (v24.0+) & Docker Compose (v2.0+)
2. **Clone the repo** and copy `.env.example` to `.env`
3. **Run `make dev`** to start the full development environment

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Make your changes following the code style guidelines
3. Run tests locally before submitting
4. Update documentation if your changes affect the public API
5. Submit a pull request with a clear description of the changes

## Code Style

- Python: Follow PEP 8, run `pylint` before committing
- JavaScript/React: Follow the existing project conventions
- All code must pass pre-commit hooks (`pylint`, `prettier`, etc.)

## Testing

- **Python backend**: `cd quantara && poetry run pytest web_app/tests`
- **Frontend**: `cd quantara/frontend && yarn test`

## Commit Messages

Use conventional commit format:
- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation
- `refactor:` — code refactoring
- `test:` — adding or updating tests
- `ci:` — CI/CD changes

## Questions?

Open a discussion or issue for any questions about contributing.
