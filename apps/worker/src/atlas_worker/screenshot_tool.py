from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from browser_runner import BrowserAutomationRunner, PlaywrightBrowserRunner, BrowserRunnerConfig

from atlas_core import (
    ActorType,
    Artifact,
    ArtifactAttachedPayload,
    ArtifactKind,
    LocalArtifactStore,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunService,
    ToolRequest,
    ToolResult,
    ToolResultOutcome,
)


class ScreenshotToolExecutor:
    def __init__(
        self,
        *,
        run_service: RunService,
        artifact_store: LocalArtifactStore,
        runner: BrowserAutomationRunner | None = None,
    ) -> None:
        self._run_service = run_service
        self._artifact_store = artifact_store
        self._runner = runner or PlaywrightBrowserRunner(BrowserRunnerConfig())

    def execute(self, request: ToolRequest) -> ToolResult:
        run_id = request.metadata.get("run_id")
        step_id = request.metadata.get("step_id")
        label = request.arguments.get("label")

        if not isinstance(run_id, str) or not run_id:
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.INVALID_REQUEST,
                error_message="screenshot_capture requires request.metadata.run_id",
            )
        if step_id is not None and not isinstance(step_id, str):
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.INVALID_REQUEST,
                error_message="screenshot_capture request.metadata.step_id must be a string when provided",
            )
        if label is not None and not isinstance(label, str):
            return ToolResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                outcome=ToolResultOutcome.INVALID_REQUEST,
                error_message="screenshot_capture label must be a string when provided",
            )

        screenshot = self._runner.capture_screenshot(label)
        artifact_id = f"artifact_{uuid4().hex}"
        stored = self._artifact_store.save_bytes(
            run_id=run_id,
            artifact_id=artifact_id,
            filename=screenshot.default_filename,
            content=screenshot.screenshot_bytes,
        )
        created_at = datetime.now(UTC)
        artifact = Artifact(
            artifact_id=artifact_id,
            run_id=run_id,
            step_id=step_id,
            kind=ArtifactKind.SCREENSHOT,
            uri=str(stored.path),
            content_type=screenshot.content_type,
            created_at=created_at,
            display_name=label or screenshot.default_filename,
            description=f"Screenshot captured from {screenshot.current_url}",
            sha256=stored.sha256_hex,
            size_bytes=stored.size_bytes,
            metadata={
                "currentUrl": screenshot.current_url,
                "pageTitle": screenshot.title,
                "scope": request.arguments.get("scope", "page"),
            },
        )
        attached = self._run_service.attach_artifact(
            run_id=run_id,
            artifact=artifact,
            step_id=step_id,
        )
        sequence = self._run_service.next_event_sequence(run_id)
        self._run_service.append_run_event(
            RunEvent(
                event_id=f"{artifact_id}-attached",
                run_id=run_id,
                sequence=sequence,
                occurred_at=created_at,
                source=RunEventSource.WORKER,
                actor_type=ActorType.WORKER,
                correlation_id=request.request_id,
                event_type=RunEventType.ARTIFACT_ATTACHED,
                payload=ArtifactAttachedPayload(
                    event_type=RunEventType.ARTIFACT_ATTACHED,
                    run_id=run_id,
                    step_id=step_id,
                    artifact=attached,
                ),
            )
        )

        return ToolResult(
            request_id=request.request_id,
            tool_name=request.tool_name,
            outcome=ToolResultOutcome.SUCCESS,
            result={
                "artifactId": attached.artifact_id,
                "uri": attached.uri,
                "contentType": attached.content_type,
                "sizeBytes": attached.size_bytes,
            },
            artifact_ids=(attached.artifact_id,),
            metadata={
                "runId": run_id,
                "stepId": step_id,
                "currentUrl": screenshot.current_url,
            },
        )

    def close(self) -> None:
        self._runner.close()
