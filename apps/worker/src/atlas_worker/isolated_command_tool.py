from __future__ import annotations

from atlas_core import (
    SandboxExecutionRequest,
    SandboxRunner,
    ToolExecutionMetadata,
    ToolRequest,
    ToolResult,
    ToolResultOutcome,
    ToolSpec,
)


class IsolatedCommandToolExecutor:
    _IMAGE = "atlas-bastion/sandbox-tools:local"

    def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            outcome=ToolResultOutcome.FATAL_ERROR,
            error_message="isolated_command must be executed through Bastion's sandbox wrapper",
            metadata={"sandboxRequired": True},
        )

    def execute_in_sandbox(
        self,
        request: ToolRequest,
        *,
        sandbox_runner: SandboxRunner,
    ) -> ToolResult:
        action = str(request.arguments.get("action", ""))
        sandbox_request = _sandbox_request_for_action(action, request)
        sandbox_result = sandbox_runner.run(sandbox_request)
        if sandbox_result.exit_code != 0:
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.FATAL_ERROR,
                error_message=(
                    "sandboxed command timed out"
                    if sandbox_result.timed_out
                    else f"sandboxed command exited with code {sandbox_result.exit_code}"
                ),
                metadata={
                    "sandbox": {
                        "mode": sandbox_result.mode.value,
                        "image": sandbox_result.image,
                        "command": list(sandbox_result.command),
                        "stderr": sandbox_result.stderr,
                        "timedOut": sandbox_result.timed_out,
                    }
                },
            )
        return ToolResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            outcome=ToolResultOutcome.SUCCESS,
            result={
                "stdout": sandbox_result.stdout.strip(),
                "action": action,
            },
            metadata={
                "sandbox": {
                    "mode": sandbox_result.mode.value,
                    "image": sandbox_result.image,
                    "command": list(sandbox_result.command),
                }
            },
        )


def isolated_command_tool_spec() -> ToolSpec:
    return ToolSpec(
        name="isolated_command",
        description="Run one Bastion-allowlisted helper command inside a Docker sandbox.",
        input_schema={
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {"type": "string", "enum": ["python_version", "sha256_text"]},
                "text": {"type": "string"},
            },
        },
        result_schema={
            "type": "object",
            "properties": {
                "stdout": {"type": "string"},
                "action": {"type": "string"},
            },
        },
        execution_metadata=ToolExecutionMetadata(
            read_only=True,
            idempotent=True,
            requires_browser=False,
            timeout_seconds=10,
            tags=("phase5", "sandboxed", "limited_terminal"),
        ),
    )


def _sandbox_request_for_action(action: str, request: ToolRequest) -> SandboxExecutionRequest:
    if action == "python_version":
        return SandboxExecutionRequest(
            command=("python3", "--version"),
            image=IsolatedCommandToolExecutor._IMAGE,
            timeout_seconds=5,
            metadata={"toolName": request.tool_name, "action": action},
        )
    if action == "sha256_text":
        text = str(request.arguments.get("text", ""))
        return SandboxExecutionRequest(
            command=(
                "python3",
                "-c",
                "import hashlib,sys;print(hashlib.sha256(sys.argv[1].encode()).hexdigest())",
                text,
            ),
            image=IsolatedCommandToolExecutor._IMAGE,
            timeout_seconds=5,
            metadata={"toolName": request.tool_name, "action": action},
        )
    raise ValueError(f"unsupported isolated command action {action}")
