"""Cross-platform project commands used by Make and Windows hosts."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = ROOT / ".venv"


def venv_python() -> Path:
    """Return the platform-specific Python executable inside the local venv."""
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(command: list[str], cwd: Path = ROOT) -> None:
    """Run a checked child command in the supplied project directory."""
    subprocess.run(command, cwd=cwd, check=True)


def install() -> None:
    """Create the venv and install pinned backend and frontend dependencies."""
    if not venv_python().exists():
        run([sys.executable, "-m", "venv", str(VENV)])
    run([str(venv_python()), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(venv_python()), "-m", "pip", "install", "-r", "requirements.txt"], BACKEND)
    run(["npm", "install"], FRONTEND)


def test() -> None:
    """Run the currently available backend and frontend tests."""
    run([str(venv_python()), "-m", "pytest", "tests"], BACKEND)
    run(["npm", "run", "test"], FRONTEND)


def seed() -> None:
    """Apply migrations, then regenerate and load the synthetic dataset."""
    run([str(venv_python()), "-m", "alembic", "upgrade", "head"], BACKEND)
    run([str(venv_python()), "-m", "app.db.seed"], BACKEND)
    run([str(venv_python()), "-m", "scripts.verify_seed"], BACKEND)


def train() -> None:
    """Train all six algorithms for all three tasks and write artefacts/charts."""
    run([str(venv_python()), "-m", "ml.train"], BACKEND)


def dev() -> None:
    """Run both local development servers until the user interrupts the command."""
    backend = subprocess.Popen([str(venv_python()), "-m", "uvicorn", "app.main:app", "--reload"], cwd=BACKEND)
    frontend = subprocess.Popen(["npm", "run", "dev", "--", "--host", "127.0.0.1"], cwd=FRONTEND)
    try:
        backend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        backend.terminate()
        frontend.terminate()
        backend.wait()
        frontend.wait()


def unavailable(phase: str) -> None:
    """Prevent phase-gated commands from implying unimplemented functionality."""
    raise SystemExit(f"{phase} is not available until its implementation phase is complete.")


def main() -> None:
    """Dispatch the requested project command."""
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "seed", "train", "dev", "test", "demo"))
    command = parser.parse_args().command
    if command == "install":
        install()
    elif command == "test":
        test()
    elif command == "dev":
        dev()
    elif command == "seed":
        seed()
    elif command == "train":
        train()
    elif command == "demo":
        install()
        seed()
        train()
        dev()
    else:
        unavailable(command)


if __name__ == "__main__":
    main()
