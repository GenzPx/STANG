"""Allow running STANG as a module: python -m stang."""

from __future__ import annotations

import sys

from stang.cli import main

if __name__ == "__main__":
    sys.exit(main())
