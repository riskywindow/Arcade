from __future__ import annotations

from datetime import UTC, datetime

from atlas_core import (
    ActorType,
    AuditRecordedPayload,
    Artifact,
    ArtifactKind,
    EnvironmentRef,
    Run,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunStopRequestedPayload,
    RunStatus,
    ScenarioRef,
    TaskRef,
)
from atlas_core.bastion import AuditEventKind, AuditRecordEnvelope
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


def test_audit_recorded_event_serialization_round_trip_preserves_audit_envelope() -> None:
    event = RunEvent(
        event_id="evt_audit_001",
        run_id="run_123",
        sequence=1,
        occurred_at=_timestamp(),
        source=RunEventSource.BASTION,
        actor_type=ActorType.BASTION,
        correlation_id="toolreq_123",
        event_type=RunEventType.AUDIT_RECORDED,
        payload=AuditRecordedPayload(
            event_type=RunEventType.AUDIT_RECORDED,
            run_id="run_123",
            audit_record=AuditRecordEnvelope(
                audit_id="audit_123",
                run_id="run_123",
                step_id="step_001",
                request_id="toolreq_123",
                actor_type=ActorType.BASTION,
                event_kind=AuditEventKind.SECRET_BROKERED,
                occurred_at=_timestamp(),
                payload={"secretHandle": "secret-helpdesk-ticket-write-token"},
            ).model_dump(mode="json"),
        ),
    )

    document = serialize_run_event(event)

    assert document["payload"]["schema_version"] == 1
    assert document["payload"]["audit_record"]["event_kind"] == "secret_brokered"
    assert deserialize_run_event(document) == event


def test_run_stop_requested_event_serialization_round_trip_is_explicit() -> None:
    event = RunEvent(
        event_id="evt_stop_001",
        run_id="run_123",
        sequence=1,
        occurred_at=_timestamp(),
        source=RunEventSource.OPERATOR,
        actor_type=ActorType.OPERATOR,
        correlation_id="stop_123",
        event_type=RunEventType.RUN_STOP_REQUESTED,
        payload=RunStopRequestedPayload(
            event_type=RunEventType.RUN_STOP_REQUESTED,
            run_id="run_123",
            stop_request_id="stop_123",
            operator_id="operator_123",
            requested_at=_timestamp(),
            reason="Interrupt the active run.",
        ),
    )

    document = serialize_run_event(event)

    assert document["payload"]["event_type"] == "run.stop_requested"
    assert document["payload"]["stop_request_id"] == "stop_123"
    assert deserialize_run_event(document) == event
