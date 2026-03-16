from __future__ import annotations

from datetime import UTC, datetime

from atlas_core import (
    ActorType,
    Artifact,
    ArtifactKind,
    EnvironmentRef,
    Run,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunStatus,
    ScenarioRef,
    TaskRef,
)
from atlas_core.serialization import (
    deserialize_artifact,
    deserialize_run_event,
    serialize_artifact,
    serialize_run_event,
)


def _timestamp() -> datetime:
    return datetime(2026, 3, 15, 12, 0, tzinfo=UTC)


def _run() -> Run:
    return Run(
        run_id="run_123",
        environment=EnvironmentRef(
            environment_id="env_helpdesk",
            environment_name="Northstar Helpdesk",
            environment_version="v1",
        ),
        scenario=ScenarioRef(
            scenario_id="scn_123",
            environment_id="env_helpdesk",
            scenario_name="travel-lockout",
            scenario_seed="seed-123",
        ),
        task=TaskRef(
            task_id="task_123",
            scenario_id="scn_123",
            task_kind="access_restoration",
            task_title="Restore employee access after travel lockout",
        ),
        status=RunStatus.PENDING,
        created_at=_timestamp(),
        updated_at=_timestamp(),
    )


def test_run_event_serialization_round_trip_is_explicit() -> None:
    run = _run()
    event = RunEvent(
        event_id="evt_001",
        run_id=run.run_id,
        sequence=0,
        occurred_at=_timestamp(),
        source=RunEventSource.WORKER,
        actor_type=ActorType.WORKER,
        correlation_id="corr_123",
        event_type=RunEventType.RUN_CREATED,
        payload=RunCreatedPayload(
            event_type=RunEventType.RUN_CREATED,
            run=run,
        ),
    )

    document = serialize_run_event(event)

    assert document["schema_version"] == 1
    assert document["payload"]["schema_version"] == 1
    assert document["correlation_id"] == "corr_123"
    assert deserialize_run_event(document) == event


def test_artifact_serialization_round_trip_preserves_attachment_fields() -> None:
    artifact = Artifact(
        artifact_id="artifact_001",
        run_id="run_123",
        step_id="step_001",
        kind=ArtifactKind.LOG,
        uri="minio://atlas-artifacts/run_123/log.json",
        content_type="application/json",
        created_at=_timestamp(),
        metadata={"producer": "dummy-worker", "role": "context-log"},
    )

    document = serialize_artifact(artifact)

    assert document["schema_version"] == 1
    assert document["run_id"] == "run_123"
    assert document["step_id"] == "step_001"
    assert deserialize_artifact(document) == artifact
