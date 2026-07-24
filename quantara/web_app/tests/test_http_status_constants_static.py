import re
from pathlib import Path


API_ROOT = Path("quantara/web_app/api")
LITERAL_STATUS_RE = re.compile(
    r"(status_code\s*=\s*(400|401|404|422)\b|HTTPException\(\s*(400|401|404|422)\s*,)"
)


def test_api_http_exceptions_use_status_constants():
    offenders: list[str] = []

    for path in API_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if LITERAL_STATUS_RE.search(text):
            offenders.append(str(path))

    assert offenders == []