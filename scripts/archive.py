"""Run the bounded Linux archive publication or archive-only rebuild command."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime.archive_runtime.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
