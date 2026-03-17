from __future__ import annotations

import subprocess

from atlas_core import (
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxMode,
)


class DockerSandboxRunner:
    def __init__(
        self,
        *,
        docker_binary: str = "docker",
        pids_limit: int = 64,
        memory_limit: str = "128m",
        cpus: str = "0.50",
    ) -> None:
        self._docker_binary = docker_binary
        self._pids_limit = pids_limit
        self._memory_limit = memory_limit
        self._cpus = cpus

    def run(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        command = self._docker_command(request)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=request.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxExecutionResult(
                mode=SandboxMode.DOCKER,
                command=request.command,
                image=request.image,
                exit_code=124,
                stdout=_normalize_text(exc.stdout),
                stderr=_normalize_text(exc.stderr),
                timed_out=True,
                metadata={"dockerCommand": " ".join(command)},
            )

        return SandboxExecutionResult(
            mode=SandboxMode.DOCKER,
            command=request.command,
            image=request.image,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            metadata={"dockerCommand": " ".join(command)},
        )

    def _docker_command(self, request: SandboxExecutionRequest) -> list[str]:
        command = [
            self._docker_binary,
            "run",
            "--rm",
            "--init",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            f"--pids-limit={self._pids_limit}",
            f"--memory={self._memory_limit}",
            f"--cpus={self._cpus}",
            f"--workdir={request.working_directory}",
        ]
        if request.network_disabled:
            command.extend(["--network", "none"])
        if request.read_only_root:
            command.append("--read-only")
            command.extend(["--tmpfs", "/tmp:rw,noexec,nosuid,size=16m"])
        for mount in request.mounts:
            command.extend(["--mount", mount])
        for key, value in sorted(request.environment.items()):
            command.extend(["--env", f"{key}={value}"])
        command.append(request.image)
        command.extend(request.command)
        return command


def _normalize_text(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
