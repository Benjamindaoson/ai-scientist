"""Run the canonical offline v4 integration check."""

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


if __name__ == "__main__":
    raise SystemExit(
        subprocess.call(
            [sys.executable, str(PROJECT_ROOT / "test_v4_integration.py")],
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    )
