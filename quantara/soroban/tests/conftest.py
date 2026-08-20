"""Make the repository root importable for adapter tests.

The adapter tests import ``quantara.soroban...`` while pytest is invoked
from ``quantara/`` (``cd quantara && poetry run pytest web_app/tests
soroban/tests``).  The ``quantara`` package lives one level above the
project directory, so it is not on ``sys.path`` by default; this conftest
adds the repository root so the documented test command works.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
