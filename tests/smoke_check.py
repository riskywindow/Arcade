from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "infra" / "docker-compose.yml"
EXPECTED_INFRA_SERVICES = {"postgres", "redis", "minio"}


def run_step(name: str, command: list[str]) -> None:
    print(f"[smoke] {name}", flush=True)
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def running_infra_services() -> set[str]:
    completed = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "ps",
            "--services",
            "--status",
            "running",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise SystemExit(
            f"[smoke] infra check failed. Could not inspect Docker Compose services. {message}"
        )

    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def check_infra() -> None:
    print("[smoke] local infrastructure", flush=True)
    running = running_infra_services()
    missing = sorted(EXPECTED_INFRA_SERVICES - running)

    if missing:
        missing_list = ", ".join(missing)
        raise SystemExit(
            "[smoke] infra is not ready. "
            f"Missing running services: {missing_list}. "
            "Start them with `make infra-up` and retry."
        )

    print("[smoke] local infrastructure ready", flush=True)


def main() -> None:
    run_step(
        "api /health smoke",
        [
            "uv",
            "run",
            "pytest",
            "tests/test_api_health.py",
            "-q",
        ],
    )
    run_step(
        "worker boot smoke",
        [
            "uv",
            "run",
            "pytest",
            "tests/test_worker_boot.py",
            "-q",
        ],
    )
    run_step(
        "console render smoke",
        [
            "pnpm",
            "--filter",
            "@atlas/console",
            "test",
        ],
    )
    check_infra()
    print("[smoke] scaffold healthy", flush=True)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            raise SystemExit(1) from exc
        raise
