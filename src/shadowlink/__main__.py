"""Allow running shadowlink directly via `python -m shadowlink`."""

from __future__ import annotations

import sys

from shadowlink.cli.main import main

if __name__ == "__main__":
    sys.exit(main())

