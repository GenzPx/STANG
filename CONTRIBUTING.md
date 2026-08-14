# Contributing to STANG

Thank you for your interest in STANG! This document outlines how to contribute.

## Getting Started

1. Fork the repository.
2. Clone your fork:
   ```bash
   git clone https://github.com/<your-username>/stang.git
   cd stang
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

## Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
2. Make your changes.
3. Add or update tests.
4. Run the test suite:
   ```bash
   pytest
   ```
5. Lint and type-check:
   ```bash
   ruff check .
   mypy stang
   ```
6. Commit using clear messages:
   ```bash
   git commit -m "feat: add raw dumper option"
   ```
7. Push and open a Pull Request.

## Reporting Issues

Use the issue tracker. Include:

- A clear title and description.
- Steps to reproduce.
- Expected vs. actual behavior.
- Python version and operating system.

## Feature Requests

Open an issue with the label `enhancement` and describe:

- The use case.
- Proposed API or CLI changes.
- Potential impact on the file format.

## Code Style

- PEP 8 with `ruff` defaults.
- Type hints on public functions.
- Docstrings for modules, classes, and public methods.

## Code of Conduct

Please read `CODE_OF_CONDUCT.md`.
