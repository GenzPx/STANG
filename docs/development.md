# Development Guide

## Clone and Install

```bash
git clone <repository>
cd stang
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run Tests

```bash
pytest
ruff check stang tests
mypy stang
```

## Web Studio

```bash
npm install
npm run typecheck
npm run build
npm run conformance   # Python ↔ TypeScript byte-equality on golden fixtures
```

## Coding Conventions

- PEP 8
- Type hints on public APIs
- Google-style docstrings
- `ruff` for linting
- `mypy` for type checking

## Branch Workflow

1. `main` is the stable branch.
2. Create feature branches from `main`.
3. Open Pull Requests for review.

## Adding a Feature

1. Update or add modules under `stang/`.
2. Add tests under `tests/`.
3. Update documentation in `docs/` and `README.md`.
4. Update `CHANGELOG.md`.
