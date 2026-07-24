from pathlib import Path


PRODUCTION_ROOTS = (
    Path("quantara/web_app"),
    Path("quantara/soroban"),
)

EXCLUDED_PARTS = {"tests", "test_integration", "__pycache__"}


def test_production_python_paths_do_not_use_print():
    offenders: list[str] = []

    for root in PRODUCTION_ROOTS:
        for path in root.rglob("*.py"):
            if any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8")
            if "print(" in text:
                offenders.append(str(path))

    assert offenders == []