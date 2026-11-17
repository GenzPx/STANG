# Installation Guide

## Requirements

- **Operating systems**: Linux, macOS, Windows
- **Minimum Python version**: 3.10
- **Recommended Python version**: 3.12
- **Required system packages**: None beyond Python
- **Optional dependencies**: `pytest`, `pytest-cov`, `mypy`, `ruff` (install via `[dev]`)
- **Supported backend**: Local filesystem (`.stg` files)
- **Hardware**: Minimal; any machine that can run Python 3.10

## Installation

### From Source

```bash
git clone <repository>
cd stang
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Then install:

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Verification

```bash
stang --version
```

Expected output:

```text
stang 2.1.0
```

```bash
stang --help
```

Expected output: a list of available commands.

```bash
stang verify some-file.stg
```

Expected output:

```text
some-file.stg: VALID
```
