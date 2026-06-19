import subprocess
import sys
import tempfile
from pathlib import Path


def run(command, **kwargs):
    try:
        return subprocess.run(command, check=True, text=True, **kwargs)
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, end="")
        if error.stderr:
            print(error.stderr, end="", file=sys.stderr)
        raise


def main():
    repo_root = Path(__file__).resolve().parents[1]
    app_dir = repo_root / "quantara"

    export_command = [
        "poetry",
        "export",
        "--format",
        "requirements.txt",
        "--without-hashes",
        "--with",
        "dev",
    ]
    export_result = run(export_command, cwd=app_dir, capture_output=True)

    requirements_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as requirements:
            requirements.write(export_result.stdout)
            requirements_path = requirements.name

        audit_command = [
            sys.executable,
            "-m",
            "pip_audit",
            "--requirement",
            requirements_path,
            "--progress-spinner=off",
            "--desc=off",
        ]
        run(audit_command)
    finally:
        if requirements_path:
            Path(requirements_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
