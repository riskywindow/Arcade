from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from atlas_core import (
    ActorType,
    Artifact,
    ArtifactAttachedPayload,
    ArtifactKind,
    EnvironmentRef,
    GradeOutcome,
    GradeResult,
    Run,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunReadyPayload,
    RunRepository,
    RunService,
    RunStartedPayload,
    RunStatus,
    RunStep,
    RunStepCreatedPayload,
    RunStepStatus,
    ScenarioRef,
    TaskRef,
    ToolCall,
    ToolCallRecordedPayload,
    ToolCallStatus,
    open_run_store_connection,
)
from atlas_worker.config import WorkerConfig


@dataclass(frozen=True)
class DummyRunSpec:
    run_id: str = "dummy-run-001"
    agent_id: str = "dummy-agent"
    base_time: datetime = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
    environment_name: str = "Northstar Helpdesk"
    scenario_name: str = "dummy-travel-lockout"
    task_title: str = "Restore employee access after travel lockout"


@dataclass(frozen=True)
class DummyExecutionResult:
    run_id: str
    final_status: RunStatus
    event_count: int
    artifact_count: int


def build_dummy_run(spec: DummyRunSpec) -> Run:
    return Run(
        run_id=spec.run_id,
        environment=EnvironmentRef(
            environment_id="env_helpdesk",
            environment_name=spec.environment_name,
            environment_version="v1",
        ),
        scenario=ScenarioRef(
            scenario_id="scenario_dummy_001",
            environment_id="env_helpdesk",
            scenario_name=spec.scenario_name,
            scenario_seed="seed-dummy-001",
        ),
        task=TaskRef(
            task_id="task_dummy_001",
            scenario_id="scenario_dummy_001",
            task_kind="access_restoration",
            task_title=spec.task_title,
        ),
        status=RunStatus.PENDING,
        created_at=spec.base_time,
        updated_at=spec.base_time,
        active_agent_id=spec.agent_id,
    )


def execute_dummy_run(run_service: RunService, spec: DummyRunSpec) -> DummyExecutionResult:
    run = run_service.create_run(build_dummy_run(spec))
    step = RunStep(
        step_id=f"{spec.run_id}-step-001",
        run_id=run.run_id,
        step_index=1,
        title="Assemble access recovery context",
        status=RunStepStatus.COMPLETED,
        started_at=spec.base_time + timedelta(seconds=10),
        completed_at=spec.base_time + timedelta(seconds=15),
    )
    artifact = Artifact(
        artifact_id=f"{spec.run_id}-artifact-001",
        kind=ArtifactKind.LOG,
        uri=f"minio://atlas-artifacts/{spec.run_id}/dummy-log.json",
        content_type="application/json",
        created_at=spec.base_time + timedelta(seconds=25),
        metadata={"source": "dummy-worker", "kind": "context-log"},
    )
    tool_call = ToolCall(
        tool_call_id=f"{spec.run_id}-tool-001",
        tool_name="identity_api",
        action="lookup_account",
        arguments={"employee_id": "emp_123"},
        status=ToolCallStatus.SUCCEEDED,
        result={
            "account_state": "locked",
            "recommended_action": "temporary_access_recovery",
        },
    )

    events = [
        RunEvent(
            event_id=f"{spec.run_id}-event-000",
            run_id=run.run_id,
            sequence=0,
            occurred_at=spec.base_time,
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{spec.run_id}-corr",
            event_type=RunEventType.RUN_CREATED,
            payload=RunCreatedPayload(
                event_type=RunEventType.RUN_CREATED,
                run=run,
            ),
        ),
        RunEvent(
            event_id=f"{spec.run_id}-event-001",
            run_id=run.run_id,
            sequence=1,
            occurred_at=spec.base_time + timedelta(seconds=5),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{spec.run_id}-corr",
            event_type=RunEventType.RUN_READY,
            payload=RunReadyPayload(
                event_type=RunEventType.RUN_READY,
                run_id=run.run_id,
                status=RunStatus.READY,
            ),
        ),
        RunEvent(
            event_id=f"{spec.run_id}-event-002",
            run_id=run.run_id,
            sequence=2,
            occurred_at=spec.base_time + timedelta(seconds=10),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{spec.run_id}-corr",
            event_type=RunEventType.RUN_STARTED,
            payload=RunStartedPayload(
                event_type=RunEventType.RUN_STARTED,
                run_id=run.run_id,
                status=RunStatus.RUNNING,
                started_at=spec.base_time + timedelta(seconds=10),
            ),
        ),
        RunEvent(
            event_id=f"{spec.run_id}-event-003",
            run_id=run.run_id,
            sequence=3,
            occurred_at=spec.base_time + timedelta(seconds=15),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{spec.run_id}-corr",
            event_type=RunEventType.RUN_STEP_CREATED,
            payload=RunStepCreatedPayload(
                event_type=RunEventType.RUN_STEP_CREATED,
                run_id=run.run_id,
                step=step,
            ),
        ),
        RunEvent(
            event_id=f"{spec.run_id}-event-004",
            run_id=run.run_id,
            sequence=4,
            occurred_at=spec.base_time + timedelta(seconds=20),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{spec.run_id}-corr",
            event_type=RunEventType.TOOL_CALL_RECORDED,
            payload=ToolCallRecordedPayload(
                event_type=RunEventType.TOOL_CALL_RECORDED,
                run_id=run.run_id,
                step_id=step.step_id,
                tool_call=tool_call,
            ),
        ),
    ]

    for event in events:
        run_service.append_run_event(event)

    attached_artifact = run_service.attach_artifact(
        run_id=run.run_id,
        artifact=artifact,
        step_id=step.step_id,
    )
    run_service.append_run_event(
        RunEvent(
            event_id=f"{spec.run_id}-event-005",
            run_id=run.run_id,
            sequence=5,
            occurred_at=spec.base_time + timedelta(seconds=25),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{spec.run_id}-corr",
            event_type=RunEventType.ARTIFACT_ATTACHED,
            payload=ArtifactAttachedPayload(
                event_type=RunEventType.ARTIFACT_ATTACHED,
                run_id=run.run_id,
                step_id=step.step_id,
                artifact=attached_artifact,
            ),
        )
    )
    run_service.append_run_event(
        RunEvent(
            event_id=f"{spec.run_id}-event-006",
            run_id=run.run_id,
            sequence=6,
            occurred_at=spec.base_time + timedelta(seconds=30),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{spec.run_id}-corr",
            event_type=RunEventType.RUN_COMPLETED,
            payload=RunCompletedPayload(
                event_type=RunEventType.RUN_COMPLETED,
                run_id=run.run_id,
                final_status=RunStatus.SUCCEEDED,
                completed_at=spec.base_time + timedelta(seconds=30),
                grade_result=GradeResult(
                    outcome=GradeOutcome.NOT_GRADED,
                    summary="Dummy execution completed without hidden grading.",
                ),
            ),
        )
    )

    finalized = run_service.get_run(run.run_id)
    return DummyExecutionResult(
        run_id=finalized.run_id,
        final_status=finalized.status,
        event_count=len(run_service.list_run_events(run.run_id)),
        artifact_count=len(run_service.list_run_artifacts(run.run_id)),
    )


def execute_dummy_run_from_config(
    config: WorkerConfig,
    spec: DummyRunSpec,
    *,
    schema_name: str | None = None,
) -> DummyExecutionResult:
    conn = open_run_store_connection(config.infrastructure.postgres_dsn(), autocommit=True)
    if schema_name:
        conn.execute("select set_config('search_path', %s, false)", (schema_name,))
    try:
        service = RunService(RunRepository(conn))
        return execute_dummy_run(service, spec)
    finally:
        conn.close()
