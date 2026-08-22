"""Primary Python entry point for DataSpectre CLI.

Run from the project directory with ``python3 dataspectre.py``.
"""

from __future__ import annotations

from cli.app import main


if __name__ == "__main__":
    raise SystemExit(main())
