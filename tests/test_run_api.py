from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
import uuid
from collections.abc import Generator
from typing import Any, cast

import psycopg
import pytest
from fastapi.testclient import TestClient

from atlas_api.app import create_app
from atlas_api.config import ApiConfig
from atlas_core import (
    ActorType,
    ApprovalRequestedPayload,
    ApprovalRequestRef,
    ApprovalRequestStatus,
    ApprovalResolvedPayload,
    AuditEventKind,
    AuditRecordedPayload,
    Artifact,
    ArtifactAttachedPayload,
    ArtifactKind,
    DEFAULT_MIGRATIONS_DIR,
    EnvironmentRef,
    GradeOutcome,
    GradeResult,
    PolicyDecision,
    PolicyDecisionOutcome,
    Run,
    RunCompletedPayload,
    RunCreatedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunReadyPayload,
    RunRepository,
    RunResumedPayload,
    RunWaitingApprovalPayload,
    RunService,
    RunStartedPayload,
    RunStatus,
    RunStepCreatedPayload,
    ScenarioRef,
    ServiceConfig,
    TaskRef,
    ToolCall,
    ToolCallRecordedPayload,
    ToolCallStatus,
    apply_migrations,
    benchmark_entry_run_id,
    discover_migrations,
    open_run_store_connection,
)
from atlas_core.bastion import AuditRecordEnvelope
from atlas_core.config import InfrastructureConfig
from atlas_worker.benchmark_runner import execute_benchmark_catalog, get_benchmark_catalog


def _timestamp() -> datetime:
    return datetime(2026, 3, 15, 12, 0, tzinfo=UTC)


def _connect() -> psycopg.Connection[dict[str, object]] | None:
    try:
        return open_run_store_connection(
            InfrastructureConfig.from_env().postgres_dsn(),
            autocommit=True,
        )
    except psycopg.OperationalError:
        return None


def _run_service(schema_name: str) -> tuple[RunService, psycopg.Connection[dict[str, object]]]:
    conn = open_run_store_connection(
        InfrastructureConfig.from_env().postgres_dsn(),
        autocommit=True,
    )
    conn.execute("select set_config('search_path', %s, false)", (schema_name,))
    return RunService(RunRepository(conn)), conn


def _run(run_id: str) -> Run:
    timestamp = _timestamp()
    return Run(
        run_id=run_id,
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
        created_at=timestamp,
        updated_at=timestamp,
        active_agent_id="dummy-agent",
    )


def _event(run: Run, event_type: RunEventType, sequence: int) -> RunEvent:
    payload: (
        RunCreatedPayload
        | RunReadyPayload
        | RunStartedPayload
        | RunCompletedPayload
        | ToolCallRecordedPayload
        | RunStepCreatedPayload
    )
    if event_type == RunEventType.RUN_CREATED:
        payload = RunCreatedPayload(
            event_type=RunEventType.RUN_CREATED,
            run=run,
        )
    elif event_type == RunEventType.RUN_READY:
        payload = RunReadyPayload(
            event_type=RunEventType.RUN_READY,
            run_id=run.run_id,
            status=RunStatus.READY,
        )
    elif event_type == RunEventType.RUN_STARTED:
        payload = RunStartedPayload(
            event_type=RunEventType.RUN_STARTED,
            run_id=run.run_id,
            status=RunStatus.RUNNING,
            started_at=_timestamp(),
        )
    elif event_type == RunEventType.RUN_COMPLETED:
        payload = RunCompletedPayload(
            event_type=RunEventType.RUN_COMPLETED,
            run_id=run.run_id,
            final_status=RunStatus.SUCCEEDED,
            completed_at=_timestamp(),
        )
    else:
        payload = ToolCallRecordedPayload(
            event_type=RunEventType.TOOL_CALL_RECORDED,
            run_id=run.run_id,
            tool_call=ToolCall(
                tool_call_id="tool_001",
                tool_name="identity_api",
                action="lookup_account",
                arguments={"employee_id": "emp_123"},
                status=ToolCallStatus.SUCCEEDED,
                result={"account_state": "locked"},
            ),
        )

    return RunEvent(
        event_id=f"evt_{sequence}",
        run_id=run.run_id,
        sequence=sequence,
        occurred_at=_timestamp(),
        source=RunEventSource.WORKER,
        actor_type=ActorType.WORKER,
        event_type=event_type,
        payload=payload,
    )


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    conn = _connect()
    if conn is None:
        pytest.skip("local Postgres is not available")

    schema_name = f"test_run_api_{uuid.uuid4().hex[:8]}"
    conn.execute(f'create schema "{schema_name}"')
    conn.execute(f'set search_path to "{schema_name}"')
    apply_migrations(conn, discover_migrations(DEFAULT_MIGRATIONS_DIR))

    config = ApiConfig(
        service=ServiceConfig(
            service_name="atlas-api",
            environment="test",
            host="127.0.0.1",
            port=8000,
            log_level="INFO",
            reload=False,
        ),
        infrastructure=InfrastructureConfig.from_env(),
    )
    app = create_app(config)
    app.state.database_schema = schema_name
    client = TestClient(app)

    try:
        yield client
    finally:
        with suppress(psycopg.Error):
            conn.execute(f'drop schema if exists "{schema_name}" cascade')
        conn.close()


def test_run_api_create_list_get_and_events(api_client: TestClient) -> None:
    create_response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
                "environmentVersion": "v1",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_helpdesk",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
            "activeAgentId": "dummy-agent",
        },
    )

    assert create_response.status_code == 201
    run_payload = create_response.json()["run"]
    run_id = run_payload["runId"]
    assert run_payload["status"] == "pending"

    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    try:
        run = service.get_run(run_id)
        service.append_run_event(_event(run, RunEventType.RUN_CREATED, 0))
        service.append_run_event(_event(run, RunEventType.RUN_READY, 1))
        service.append_run_event(_event(run, RunEventType.RUN_STARTED, 2))
        service.append_run_event(_event(run, RunEventType.TOOL_CALL_RECORDED, 3))
        service.attach_artifact(
            run_id=run_id,
            artifact=Artifact(
                artifact_id="artifact_001",
                kind=ArtifactKind.LOG,
                uri="minio://atlas-artifacts/run_123/log.json",
                content_type="application/json",
                created_at=_timestamp(),
                metadata={"source": "api-test"},
            ),
        )
    finally:
        service_conn.close()

    list_response = api_client.get("/runs")
    assert list_response.status_code == 200
    assert [item["runId"] for item in list_response.json()["runs"]] == [run_id]

    get_response = api_client.get(f"/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["run"]["runId"] == run_id

    events_response = api_client.get(f"/runs/{run_id}/events")
    assert events_response.status_code == 200
    assert events_response.json()["runId"] == run_id
    assert events_response.json()["events"][0]["schemaVersion"] == 1
    assert events_response.json()["events"][0]["payload"]["schemaVersion"] == 1
    assert [item["eventType"] for item in events_response.json()["events"]] == [
        "run.created",
        "run.ready",
        "run.started",
        "tool_call.recorded",
    ]


def test_benchmark_catalog_and_result_endpoints(api_client: TestClient) -> None:
    catalog_response = api_client.get("/benchmarks/catalogs/helpdesk-v0")
    assert catalog_response.status_code == 200
    assert catalog_response.json()["catalog"]["catalogId"] == "helpdesk-v0"
    assert [entry["entryId"] for entry in catalog_response.json()["catalog"]["entries"]] == [
        "travel-lockout-recovery",
        "shared-drive-access-request",
    ]

    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    try:
        result = execute_benchmark_catalog(
            service,
            catalog=get_benchmark_catalog("helpdesk-v0"),
            benchmark_run_id="benchmark-api-001",
        )
    finally:
        service_conn.close()

    result_response = api_client.get("/benchmarks/catalogs/helpdesk-v0/runs/benchmark-api-001")
    assert result_response.status_code == 200
    payload = result_response.json()["result"]
    assert payload["benchmarkRunId"] == "benchmark-api-001"
    assert payload["catalogId"] == "helpdesk-v0"
    assert payload["aggregate"]["totalRuns"] == 2
    assert payload["aggregate"]["passedRuns"] == 2
    assert len(payload["items"]) == 2
    assert {item["runId"] for item in payload["items"]} == {item.run_id for item in result.items}


def test_run_compare_endpoint_flags_regression(api_client: TestClient) -> None:
    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    try:
        baseline_run = _run("run_compare_baseline")
        baseline_run = service.create_run(baseline_run)
        baseline_run = RunRepository(service_conn).update_run_progress(
            baseline_run.run_id,
            status=RunStatus.SUCCEEDED,
            updated_at=_timestamp().replace(minute=2),
            started_at=_timestamp(),
            completed_at=_timestamp().replace(minute=2),
            grade_result=GradeResult(
                grade_id="grade-baseline",
                outcome=GradeOutcome.PASSED,
                score=1.0,
                summary="Completed successfully.",
            ),
        )
        candidate_run = _run("run_compare_candidate")
        candidate_run = service.create_run(candidate_run)
        candidate_run = RunRepository(service_conn).update_run_progress(
            candidate_run.run_id,
            status=RunStatus.FAILED,
            updated_at=_timestamp().replace(minute=4),
            started_at=_timestamp(),
            completed_at=_timestamp().replace(minute=4),
            grade_result=GradeResult(
                grade_id="grade-candidate",
                outcome=GradeOutcome.FAILED,
                score=0.4,
                summary="Failed after extra approvals.",
            ),
        )
        service.append_run_event(_event(baseline_run, RunEventType.RUN_STEP_CREATED, 0))
        service.append_run_event(
            RunEvent(
                event_id="baseline-tool",
                run_id=baseline_run.run_id,
                sequence=1,
                occurred_at=_timestamp(),
                source=RunEventSource.AGENT,
                actor_type=ActorType.AGENT,
                correlation_id="baseline-tool",
                event_type=RunEventType.TOOL_CALL_RECORDED,
                payload=ToolCallRecordedPayload(
                    event_type=RunEventType.TOOL_CALL_RECORDED,
                    run_id=baseline_run.run_id,
                    step_id=None,
                    tool_call=ToolCall(
                        tool_call_id="tool-baseline",
                        tool_name="identity_api",
                        action="reset_password",
                        arguments={},
                        status=ToolCallStatus.SUCCEEDED,
                        result={"ok": True},
                    ),
                    policy_decision=PolicyDecision(
                        decision_id="policy-baseline",
                        outcome=PolicyDecisionOutcome.REQUIRE_APPROVAL,
                        action_type="identity.reset_password",
                        rationale="Sensitive action.",
                        approval_request_id="approval-baseline",
                    ),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="baseline-approval",
                run_id=baseline_run.run_id,
                sequence=2,
                occurred_at=_timestamp(),
                source=RunEventSource.BASTION,
                actor_type=ActorType.SYSTEM,
                correlation_id="approval-baseline",
                event_type=RunEventType.APPROVAL_RESOLVED,
                payload=ApprovalResolvedPayload(
                    event_type=RunEventType.APPROVAL_RESOLVED,
                    run_id=baseline_run.run_id,
                    approval_request=ApprovalRequestRef(
                        approval_request_id="approval-baseline",
                        run_id=baseline_run.run_id,
                        status=ApprovalRequestStatus.APPROVED,
                        requested_action_type="identity.reset_password",
                        requester_role="agent",
                        requested_at=_timestamp(),
                        resolved_at=_timestamp().replace(minute=1),
                    ).model_dump(mode="json"),
                    operator_id="operator-001",
                    decided_at=_timestamp().replace(minute=1),
                ),
            )
        )

        service.append_run_event(_event(candidate_run, RunEventType.RUN_STEP_CREATED, 0))
        service.append_run_event(
            RunEvent(
                event_id="candidate-tool-1",
                run_id=candidate_run.run_id,
                sequence=1,
                occurred_at=_timestamp(),
                source=RunEventSource.AGENT,
                actor_type=ActorType.AGENT,
                correlation_id="candidate-tool-1",
                event_type=RunEventType.TOOL_CALL_RECORDED,
                payload=ToolCallRecordedPayload(
                    event_type=RunEventType.TOOL_CALL_RECORDED,
                    run_id=candidate_run.run_id,
                    step_id=None,
                    tool_call=ToolCall(
                        tool_call_id="tool-candidate-1",
                        tool_name="identity_api",
                        action="reset_password",
                        arguments={},
                        status=ToolCallStatus.SUCCEEDED,
                        result={"ok": True},
                    ),
                    policy_decision=PolicyDecision(
                        decision_id="policy-candidate-1",
                        outcome=PolicyDecisionOutcome.REQUIRE_APPROVAL,
                        action_type="identity.reset_password",
                        rationale="Sensitive action.",
                        approval_request_id="approval-candidate-1",
                    ),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="candidate-tool-2",
                run_id=candidate_run.run_id,
                sequence=2,
                occurred_at=_timestamp(),
                source=RunEventSource.AGENT,
                actor_type=ActorType.AGENT,
                correlation_id="candidate-tool-2",
                event_type=RunEventType.TOOL_CALL_RECORDED,
                payload=ToolCallRecordedPayload(
                    event_type=RunEventType.TOOL_CALL_RECORDED,
                    run_id=candidate_run.run_id,
                    step_id=None,
                    tool_call=ToolCall(
                        tool_call_id="tool-candidate-2",
                        tool_name="identity_api",
                        action="disable_mfa",
                        arguments={},
                        status=ToolCallStatus.FAILED,
                        error_message="denied",
                    ),
                    policy_decision=PolicyDecision(
                        decision_id="policy-candidate-2",
                        outcome=PolicyDecisionOutcome.DENY,
                        action_type="identity.disable_mfa",
                        rationale="Unsafe shortcut.",
                    ),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="candidate-approval-1",
                run_id=candidate_run.run_id,
                sequence=3,
                occurred_at=_timestamp(),
                source=RunEventSource.BASTION,
                actor_type=ActorType.SYSTEM,
                correlation_id="approval-candidate-1",
                event_type=RunEventType.APPROVAL_RESOLVED,
                payload=ApprovalResolvedPayload(
                    event_type=RunEventType.APPROVAL_RESOLVED,
                    run_id=candidate_run.run_id,
                    approval_request=ApprovalRequestRef(
                        approval_request_id="approval-candidate-1",
                        run_id=candidate_run.run_id,
                        status=ApprovalRequestStatus.APPROVED,
                        requested_action_type="identity.reset_password",
                        requester_role="agent",
                        requested_at=_timestamp(),
                        resolved_at=_timestamp().replace(minute=1),
                    ).model_dump(mode="json"),
                    operator_id="operator-001",
                    decided_at=_timestamp().replace(minute=1),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="candidate-approval-2",
                run_id=candidate_run.run_id,
                sequence=4,
                occurred_at=_timestamp().replace(minute=2),
                source=RunEventSource.BASTION,
                actor_type=ActorType.SYSTEM,
                correlation_id="approval-candidate-2",
                event_type=RunEventType.APPROVAL_RESOLVED,
                payload=ApprovalResolvedPayload(
                    event_type=RunEventType.APPROVAL_RESOLVED,
                    run_id=candidate_run.run_id,
                    approval_request=ApprovalRequestRef(
                        approval_request_id="approval-candidate-2",
                        run_id=candidate_run.run_id,
                        status=ApprovalRequestStatus.APPROVED,
                        requested_action_type="identity.reset_password",
                        requester_role="agent",
                        requested_at=_timestamp().replace(minute=2),
                        resolved_at=_timestamp().replace(minute=3),
                    ).model_dump(mode="json"),
                    operator_id="operator-002",
                    decided_at=_timestamp().replace(minute=3),
                ),
            )
        )
    finally:
        service_conn.close()

    response = api_client.get(
        "/runs/compare",
        params={
            "baseline_run_id": "run_compare_baseline",
            "candidate_run_id": "run_compare_candidate",
        },
    )

    assert response.status_code == 200
    payload = response.json()["comparison"]
    assert payload["outcome"] == "worse"
    assert payload["scoreDelta"] == -0.6
    assert payload["approvalCountDelta"] == 1
    assert payload["deniedPolicyDelta"] == 1
    assert "Candidate failed while baseline passed." in payload["regressions"]


def test_benchmark_compare_endpoint_surfaces_regression(api_client: TestClient) -> None:
    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    try:
        execute_benchmark_catalog(
            service,
            catalog=get_benchmark_catalog("helpdesk-v0"),
            benchmark_run_id="benchmark-compare-baseline",
        )
        execute_benchmark_catalog(
            service,
            catalog=get_benchmark_catalog("helpdesk-v0"),
            benchmark_run_id="benchmark-compare-candidate",
        )
        degraded_run_id = benchmark_entry_run_id(
            "benchmark-compare-candidate",
            "travel-lockout-recovery",
        )
        degraded_run = service.get_run(degraded_run_id)
        RunRepository(service_conn).update_run_progress(
            degraded_run_id,
            status=RunStatus.FAILED,
            updated_at=_timestamp().replace(minute=5),
            completed_at=degraded_run.completed_at or _timestamp().replace(minute=5),
            grade_result=GradeResult(
                grade_id="grade-degraded",
                outcome=GradeOutcome.FAILED,
                score=0.2,
                summary="Regression example.",
            ),
        )
        service.append_run_event(
            RunEvent(
                event_id=f"{degraded_run_id}-extra-deny",
                run_id=degraded_run_id,
                sequence=service.next_event_sequence(degraded_run_id),
                occurred_at=_timestamp().replace(minute=5),
                source=RunEventSource.BASTION,
                actor_type=ActorType.SYSTEM,
                correlation_id="extra-deny",
                event_type=RunEventType.TOOL_CALL_RECORDED,
                payload=ToolCallRecordedPayload(
                    event_type=RunEventType.TOOL_CALL_RECORDED,
                    run_id=degraded_run_id,
                    step_id=None,
                    tool_call=ToolCall(
                        tool_call_id="tool-extra-deny",
                        tool_name="identity_api",
                        action="disable_mfa",
                        arguments={},
                        status=ToolCallStatus.FAILED,
                        error_message="denied",
                    ),
                    policy_decision=PolicyDecision(
                        decision_id="policy-extra-deny",
                        outcome=PolicyDecisionOutcome.DENY,
                        action_type="identity.disable_mfa",
                        rationale="Unsafe shortcut.",
                    ),
                ),
            )
        )
    finally:
        service_conn.close()

    response = api_client.get(
        "/benchmarks/catalogs/helpdesk-v0/compare",
        params={
            "baseline_benchmark_run_id": "benchmark-compare-baseline",
            "candidate_benchmark_run_id": "benchmark-compare-candidate",
        },
    )

    assert response.status_code == 200
    payload = response.json()["comparison"]
    assert payload["outcome"] == "worse"
    assert payload["passedRunDelta"] == -1
    assert payload["failedRunDelta"] == 1
    assert any(
        item["entryId"] == "travel-lockout-recovery" and item["comparison"]["outcome"] == "worse"
        for item in payload["itemComparisons"]
    )


def test_run_replay_endpoint_returns_grouped_run_detail(api_client: TestClient) -> None:
    create_response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
                "environmentVersion": "v1",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_helpdesk",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
            "activeAgentId": "dummy-agent",
        },
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["run"]["runId"]

    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    try:
        run = service.get_run(run_id)
        service.append_run_event(_event(run, RunEventType.RUN_CREATED, 0))
        service.append_run_event(_event(run, RunEventType.RUN_READY, 1))
        service.append_run_event(_event(run, RunEventType.RUN_STARTED, 2))
        service.append_run_event(
            RunEvent(
                event_id="evt_step",
                run_id=run_id,
                sequence=3,
                occurred_at=_timestamp(),
                source=RunEventSource.AGENT,
                actor_type=ActorType.AGENT,
                correlation_id="step_001",
                event_type=RunEventType.RUN_STEP_CREATED,
                payload=RunStepCreatedPayload(
                    event_type=RunEventType.RUN_STEP_CREATED,
                    run_id=run_id,
                    step={
                        "step_id": "step_001",
                        "run_id": run_id,
                        "step_index": 1,
                        "title": "Inspect account state",
                        "status": "completed",
                        "started_at": _timestamp().isoformat(),
                        "completed_at": _timestamp().isoformat(),
                    },
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_tool",
                run_id=run_id,
                sequence=4,
                occurred_at=_timestamp(),
                source=RunEventSource.WORKER,
                actor_type=ActorType.WORKER,
                correlation_id="req_123",
                event_type=RunEventType.TOOL_CALL_RECORDED,
                payload=ToolCallRecordedPayload(
                    event_type=RunEventType.TOOL_CALL_RECORDED,
                    run_id=run_id,
                    step_id="step_001",
                    tool_call=ToolCall(
                        tool_call_id="tool_001",
                        tool_name="identity_api",
                        action="limited_mfa_recovery",
                        arguments={"employee_id": "emp_123"},
                        status=ToolCallStatus.BLOCKED,
                        result={"artifactIds": ["artifact_001"]},
                    ),
                    policy_decision=PolicyDecision(
                        decision_id="policy_001",
                        outcome=PolicyDecisionOutcome.REQUIRE_APPROVAL,
                        action_type="identity.limited_mfa_recovery",
                        rationale="Sensitive account recovery requires approval.",
                        approval_request_id="approval_001",
                    ),
                ),
            )
        )
        approval_request = ApprovalRequestRef(
            approval_request_id="approval_001",
            run_id=run_id,
            step_id="step_001",
            status=ApprovalRequestStatus.PENDING,
            requested_action_type="identity.limited_mfa_recovery",
            tool_name="identity_api",
            requested_arguments={"employee_id": "emp_123"},
            requested_at=_timestamp(),
            summary="Approve the limited recovery path.",
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_approval_requested",
                run_id=run_id,
                sequence=5,
                occurred_at=_timestamp(),
                source=RunEventSource.BASTION,
                actor_type=ActorType.BASTION,
                correlation_id="approval_001",
                event_type=RunEventType.APPROVAL_REQUESTED,
                payload=ApprovalRequestedPayload(
                    event_type=RunEventType.APPROVAL_REQUESTED,
                    run_id=run_id,
                    approval_request=approval_request.model_dump(mode="json"),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_waiting",
                run_id=run_id,
                sequence=6,
                occurred_at=_timestamp(),
                source=RunEventSource.WORKER,
                actor_type=ActorType.WORKER,
                correlation_id="approval_001",
                event_type=RunEventType.RUN_WAITING_APPROVAL,
                payload=RunWaitingApprovalPayload(
                    event_type=RunEventType.RUN_WAITING_APPROVAL,
                    run_id=run_id,
                    status=RunStatus.WAITING_APPROVAL,
                    approval_request_id="approval_001",
                    waiting_at=_timestamp(),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_audit",
                run_id=run_id,
                sequence=7,
                occurred_at=_timestamp(),
                source=RunEventSource.BASTION,
                actor_type=ActorType.BASTION,
                correlation_id="req_123",
                event_type=RunEventType.AUDIT_RECORDED,
                payload=AuditRecordedPayload(
                    event_type=RunEventType.AUDIT_RECORDED,
                    run_id=run_id,
                    audit_record=AuditRecordEnvelope(
                        audit_id="audit_001",
                        run_id=run_id,
                        step_id="step_001",
                        request_id="req_123",
                        actor_type=ActorType.BASTION,
                        event_kind=AuditEventKind.APPROVAL_REQUESTED,
                        occurred_at=_timestamp(),
                        payload={"reasonCode": "approval_required"},
                    ).model_dump(mode="json"),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_artifact",
                run_id=run_id,
                sequence=8,
                occurred_at=_timestamp(),
                source=RunEventSource.WORKER,
                actor_type=ActorType.WORKER,
                correlation_id="artifact_001",
                event_type=RunEventType.ARTIFACT_ATTACHED,
                payload=ArtifactAttachedPayload(
                    event_type=RunEventType.ARTIFACT_ATTACHED,
                    run_id=run_id,
                    step_id="step_001",
                    artifact=Artifact(
                        artifact_id="artifact_001",
                        run_id=run_id,
                        step_id="step_001",
                        kind=ArtifactKind.SCREENSHOT,
                        uri="minio://atlas-artifacts/run_123/screenshot.png",
                        content_type="image/png",
                        created_at=_timestamp(),
                        metadata={"source": "browser"},
                    ),
                ),
            )
        )
        approved_request = approval_request.model_copy(
            update={"status": ApprovalRequestStatus.APPROVED, "resolved_at": _timestamp()}
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_approval_resolved",
                run_id=run_id,
                sequence=9,
                occurred_at=_timestamp(),
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id="approval_001",
                event_type=RunEventType.APPROVAL_RESOLVED,
                payload=ApprovalResolvedPayload(
                    event_type=RunEventType.APPROVAL_RESOLVED,
                    run_id=run_id,
                    approval_request=approved_request.model_dump(mode="json"),
                    operator_id="operator_001",
                    decided_at=_timestamp(),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_resumed",
                run_id=run_id,
                sequence=10,
                occurred_at=_timestamp(),
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id="approval_001",
                event_type=RunEventType.RUN_RESUMED,
                payload=RunResumedPayload(
                    event_type=RunEventType.RUN_RESUMED,
                    run_id=run_id,
                    status=RunStatus.RUNNING,
                    approval_request_id="approval_001",
                    resumed_at=_timestamp(),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_completed",
                run_id=run_id,
                sequence=11,
                occurred_at=_timestamp(),
                source=RunEventSource.WORKER,
                actor_type=ActorType.WORKER,
                event_type=RunEventType.RUN_COMPLETED,
                payload=RunCompletedPayload(
                    event_type=RunEventType.RUN_COMPLETED,
                    run_id=run_id,
                    final_status=RunStatus.SUCCEEDED,
                    completed_at=_timestamp(),
                ),
            )
        )
    finally:
        service_conn.close()

    response = api_client.get(f"/runs/{run_id}/replay")

    assert response.status_code == 200
    payload = response.json()["replay"]
    assert payload["run"]["runId"] == run_id
    assert payload["rawEventCount"] == 12
    assert payload["toolActions"][0]["toolCall"]["toolName"] == "identity_api"
    assert payload["policyDecisions"][0]["decision"]["outcome"] == "require_approval"
    assert payload["approvals"][0]["approvalRequestId"] == "approval_001"
    assert payload["auditRecords"][0]["auditId"] == "audit_001"
    assert payload["artifacts"][0]["artifactId"] == "artifact_001"
    assert payload["outcome"]["finalStatus"] == "succeeded"
    assert payload["outcomeExplanation"]["objectiveStatus"] == "incomplete"
    assert payload["scoreSummary"]["toolCallCount"] == 1
    assert payload["scoreSummary"]["approvalCounts"]["approved"] == 1
    assert payload["scoreSummary"]["policyCounts"]["requireApproval"] == 1
    assert "summary" in payload["outcomeExplanation"]
    assert any(entry["kind"] == "tool_action" for entry in payload["timelineEntries"])
    assert any(entry["kind"] == "approval" for entry in payload["timelineEntries"])

    artifacts_response = api_client.get(f"/runs/{run_id}/artifacts")
    assert artifacts_response.status_code == 200
    assert artifacts_response.json()["artifacts"][0]["artifactId"] == "artifact_001"
    assert artifacts_response.json()["artifacts"][0]["runId"] == run_id
    assert artifacts_response.json()["artifacts"][0]["schemaVersion"] == 1


def test_run_api_returns_404_for_missing_run(api_client: TestClient) -> None:
    response = api_client.get("/runs/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "run missing does not exist"


def test_run_api_returns_404_for_missing_run_children(api_client: TestClient) -> None:
    events_response = api_client.get("/runs/missing/events")
    artifacts_response = api_client.get("/runs/missing/artifacts")
    stop_response = api_client.post("/runs/missing/stop", json={"operatorId": "operator_123"})

    assert events_response.status_code == 404
    assert events_response.json()["detail"] == "run missing does not exist"
    assert artifacts_response.status_code == 404
    assert artifacts_response.json()["detail"] == "run missing does not exist"
    assert stop_response.status_code == 404
    assert stop_response.json()["detail"] == "run missing does not exist"


def test_run_api_validates_request_shape(api_client: TestClient) -> None:
    response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_other",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
        },
    )

    assert response.status_code == 422


def test_run_api_lists_and_resolves_approvals(api_client: TestClient) -> None:
    create_response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
                "environmentVersion": "v1",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_helpdesk",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
            "activeAgentId": "dummy-agent",
        },
    )
    run_id = create_response.json()["run"]["runId"]

    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    approval = ApprovalRequestRef(
        approval_request_id="approval_001",
        run_id=run_id,
        step_id=f"{run_id}-step-001",
        status=ApprovalRequestStatus.PENDING,
        requested_action_type="limited_mfa_recovery",
        tool_name="identity_api",
        requested_arguments={"action": "limited_mfa_recovery", "employee_id": "emp_123"},
        requester_role="helpdesk_agent",
        reason_code="limited_mfa_recovery_requires_approval",
        summary="Limited MFA recovery requires operator approval before execution.",
        target_resource_type="employee",
        target_resource_id="emp_123",
        requested_at=_timestamp(),
    )
    try:
        run = service.get_run(run_id)
        service.append_run_event(_event(run, RunEventType.RUN_CREATED, 0))
        service.append_run_event(_event(run, RunEventType.RUN_READY, 1))
        service.append_run_event(_event(run, RunEventType.RUN_STARTED, 2))
        service.append_run_event(
            RunEvent(
                event_id="evt_approval_requested",
                run_id=run_id,
                sequence=3,
                occurred_at=_timestamp(),
                source=RunEventSource.BASTION,
                actor_type=ActorType.BASTION,
                correlation_id=approval.approval_request_id,
                event_type=RunEventType.APPROVAL_REQUESTED,
                payload=ApprovalRequestedPayload(
                    event_type=RunEventType.APPROVAL_REQUESTED,
                    run_id=run_id,
                    approval_request=approval.model_dump(mode="json"),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_waiting_approval",
                run_id=run_id,
                sequence=4,
                occurred_at=_timestamp(),
                source=RunEventSource.WORKER,
                actor_type=ActorType.WORKER,
                correlation_id=approval.approval_request_id,
                event_type=RunEventType.RUN_WAITING_APPROVAL,
                payload=RunWaitingApprovalPayload(
                    event_type=RunEventType.RUN_WAITING_APPROVAL,
                    run_id=run_id,
                    status=RunStatus.WAITING_APPROVAL,
                    approval_request_id=approval.approval_request_id,
                    waiting_at=_timestamp(),
                ),
            )
        )
    finally:
        service_conn.close()

    approvals_response = api_client.get(f"/runs/{run_id}/approvals")
    assert approvals_response.status_code == 200
    assert approvals_response.json()["approvals"][0]["approvalRequestId"] == "approval_001"
    assert approvals_response.json()["approvals"][0]["status"] == "pending"

    approve_response = api_client.post(
        f"/runs/{run_id}/approvals/approval_001/approve",
        json={"operatorId": "operator_123", "resolutionSummary": "Least-privilege recovery is approved."},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["approval"]["status"] == "approved"

    get_response = api_client.get(f"/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["run"]["status"] == "running"

    events_response = api_client.get(f"/runs/{run_id}/events")
    event_types = [item["eventType"] for item in events_response.json()["events"]]
    assert "approval.requested" in event_types
    assert "run.waiting_approval" in event_types
    assert "approval.resolved" in event_types
    assert "audit.recorded" in event_types
    assert "run.resumed" in event_types

    audit_response = api_client.get(f"/runs/{run_id}/audit")
    assert audit_response.status_code == 200
    assert audit_response.json()["records"][0]["eventKind"] == "approval_resolved"
    assert audit_response.json()["records"][0]["payload"]["decision"] == "approved"


def test_run_api_denied_approval_fails_run(api_client: TestClient) -> None:
    create_response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
                "environmentVersion": "v1",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_helpdesk",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
            "activeAgentId": "dummy-agent",
        },
    )
    run_id = create_response.json()["run"]["runId"]

    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    approval = ApprovalRequestRef(
        approval_request_id="approval_002",
        run_id=run_id,
        step_id=f"{run_id}-step-001",
        status=ApprovalRequestStatus.PENDING,
        requested_action_type="temporary_diagnostic_access",
        requested_at=_timestamp(),
    )
    try:
        run = service.get_run(run_id)
        service.append_run_event(_event(run, RunEventType.RUN_CREATED, 0))
        service.append_run_event(_event(run, RunEventType.RUN_READY, 1))
        service.append_run_event(_event(run, RunEventType.RUN_STARTED, 2))
        service.append_run_event(
            RunEvent(
                event_id="evt_approval_requested_2",
                run_id=run_id,
                sequence=3,
                occurred_at=_timestamp(),
                source=RunEventSource.BASTION,
                actor_type=ActorType.BASTION,
                correlation_id=approval.approval_request_id,
                event_type=RunEventType.APPROVAL_REQUESTED,
                payload=ApprovalRequestedPayload(
                    event_type=RunEventType.APPROVAL_REQUESTED,
                    run_id=run_id,
                    approval_request=approval.model_dump(mode="json"),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_waiting_approval_2",
                run_id=run_id,
                sequence=4,
                occurred_at=_timestamp(),
                source=RunEventSource.WORKER,
                actor_type=ActorType.WORKER,
                correlation_id=approval.approval_request_id,
                event_type=RunEventType.RUN_WAITING_APPROVAL,
                payload=RunWaitingApprovalPayload(
                    event_type=RunEventType.RUN_WAITING_APPROVAL,
                    run_id=run_id,
                    status=RunStatus.WAITING_APPROVAL,
                    approval_request_id=approval.approval_request_id,
                    waiting_at=_timestamp(),
                ),
            )
        )
    finally:
        service_conn.close()

    deny_response = api_client.post(
        f"/runs/{run_id}/approvals/approval_002/deny",
        json={"operatorId": "operator_456", "resolutionSummary": "Business risk is too high."},
    )
    assert deny_response.status_code == 200
    assert deny_response.json()["approval"]["status"] == "rejected"

    get_response = api_client.get(f"/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["run"]["status"] == "failed"

    events_response = api_client.get(f"/runs/{run_id}/events")
    event_types = [item["eventType"] for item in events_response.json()["events"]]
    assert "audit.recorded" in event_types
    assert "approval.resolved" in event_types
    assert event_types[-1] == "run.completed"

    audit_response = api_client.get(f"/runs/{run_id}/audit")
    assert audit_response.status_code == 200
    assert audit_response.json()["records"][0]["eventKind"] == "approval_resolved"
    assert audit_response.json()["records"][0]["payload"]["decision"] == "denied"


def test_run_api_stop_request_schedules_running_run(api_client: TestClient) -> None:
    create_response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
                "environmentVersion": "v1",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_helpdesk",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
            "activeAgentId": "dummy-agent",
        },
    )
    run_id = create_response.json()["run"]["runId"]

    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    try:
        run = service.get_run(run_id)
        service.append_run_event(_event(run, RunEventType.RUN_CREATED, 0))
        service.append_run_event(_event(run, RunEventType.RUN_READY, 1))
        service.append_run_event(_event(run, RunEventType.RUN_STARTED, 2))
    finally:
        service_conn.close()

    stop_response = api_client.post(
        f"/runs/{run_id}/stop",
        json={"operatorId": "operator_123", "reason": "Unsafe behavior observed."},
    )
    assert stop_response.status_code == 200
    assert stop_response.json()["runId"] == run_id
    assert stop_response.json()["status"] == "running"

    events_response = api_client.get(f"/runs/{run_id}/events")
    event_types = [item["eventType"] for item in events_response.json()["events"]]
    assert "run.stop_requested" in event_types
    assert "run.completed" not in event_types

    audit_response = api_client.get(f"/runs/{run_id}/audit")
    assert audit_response.status_code == 200
    assert audit_response.json()["records"][0]["eventKind"] == "kill_switch_triggered"
    assert audit_response.json()["records"][0]["payload"]["phase"] == "requested"


def test_run_api_stop_request_cancels_waiting_run_immediately(api_client: TestClient) -> None:
    create_response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
                "environmentVersion": "v1",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_helpdesk",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
            "activeAgentId": "dummy-agent",
        },
    )
    run_id = create_response.json()["run"]["runId"]

    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    approval = ApprovalRequestRef(
        approval_request_id="approval_stop_001",
        run_id=run_id,
        step_id=f"{run_id}-step-001",
        status=ApprovalRequestStatus.PENDING,
        requested_action_type="limited_mfa_recovery",
        requested_at=_timestamp(),
    )
    try:
        run = service.get_run(run_id)
        service.append_run_event(_event(run, RunEventType.RUN_CREATED, 0))
        service.append_run_event(_event(run, RunEventType.RUN_READY, 1))
        service.append_run_event(_event(run, RunEventType.RUN_STARTED, 2))
        service.append_run_event(
            RunEvent(
                event_id="evt_stop_approval_requested",
                run_id=run_id,
                sequence=3,
                occurred_at=_timestamp(),
                source=RunEventSource.BASTION,
                actor_type=ActorType.BASTION,
                correlation_id=approval.approval_request_id,
                event_type=RunEventType.APPROVAL_REQUESTED,
                payload=ApprovalRequestedPayload(
                    event_type=RunEventType.APPROVAL_REQUESTED,
                    run_id=run_id,
                    approval_request=approval.model_dump(mode="json"),
                ),
            )
        )
        service.append_run_event(
            RunEvent(
                event_id="evt_stop_waiting_approval",
                run_id=run_id,
                sequence=4,
                occurred_at=_timestamp(),
                source=RunEventSource.WORKER,
                actor_type=ActorType.WORKER,
                correlation_id=approval.approval_request_id,
                event_type=RunEventType.RUN_WAITING_APPROVAL,
                payload=RunWaitingApprovalPayload(
                    event_type=RunEventType.RUN_WAITING_APPROVAL,
                    run_id=run_id,
                    status=RunStatus.WAITING_APPROVAL,
                    approval_request_id=approval.approval_request_id,
                    waiting_at=_timestamp(),
                ),
            )
        )
    finally:
        service_conn.close()

    stop_response = api_client.post(
        f"/runs/{run_id}/stop",
        json={"operatorId": "operator_789", "reason": "Stop the paused run."},
    )
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "cancelled"

    get_response = api_client.get(f"/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["run"]["status"] == "cancelled"

    audit_response = api_client.get(f"/runs/{run_id}/audit")
    phases = [record["payload"]["phase"] for record in audit_response.json()["records"]]
    assert phases == ["requested", "completed"]


def test_run_api_lists_persisted_bastion_audit_records(api_client: TestClient) -> None:
    create_response = api_client.post(
        "/runs",
        json={
            "environment": {
                "environmentId": "env_helpdesk",
                "environmentName": "Northstar Helpdesk",
                "environmentVersion": "v1",
            },
            "scenario": {
                "scenarioId": "scn_123",
                "environmentId": "env_helpdesk",
                "scenarioName": "travel-lockout",
                "scenarioSeed": "seed-123",
            },
            "task": {
                "taskId": "task_123",
                "scenarioId": "scn_123",
                "taskKind": "access_restoration",
                "taskTitle": "Restore employee access after travel lockout",
            },
            "activeAgentId": "dummy-agent",
        },
    )
    run_id = create_response.json()["run"]["runId"]

    schema_name = cast(Any, api_client.app).state.database_schema
    service, service_conn = _run_service(schema_name)
    try:
        run = service.get_run(run_id)
        service.append_run_event(_event(run, RunEventType.RUN_CREATED, 0))
        service.append_run_event(_event(run, RunEventType.RUN_READY, 1))
        service.append_run_event(_event(run, RunEventType.RUN_STARTED, 2))
        service.append_run_event(
            RunEvent(
                event_id="evt_audit_recorded",
                run_id=run_id,
                sequence=3,
                occurred_at=_timestamp(),
                source=RunEventSource.BASTION,
                actor_type=ActorType.BASTION,
                correlation_id="toolreq_001",
                event_type=RunEventType.AUDIT_RECORDED,
                payload=AuditRecordedPayload(
                    event_type=RunEventType.AUDIT_RECORDED,
                    run_id=run_id,
                    audit_record=AuditRecordEnvelope(
                        audit_id="audit_001",
                        run_id=run_id,
                        step_id=f"{run_id}-step-001",
                        request_id="toolreq_001",
                        actor_type=ActorType.BASTION,
                        event_kind=AuditEventKind.POLICY_EVALUATED,
                        occurred_at=_timestamp(),
                        payload={
                            "reasonCode": "read_only_lookup_allowed",
                            "decision": "allow",
                        },
                    ).model_dump(mode="json"),
                ),
            )
        )
    finally:
        service_conn.close()

    response = api_client.get(f"/runs/{run_id}/audit")
    assert response.status_code == 200
    assert response.json()["runId"] == run_id
    assert response.json()["records"] == [
        {
            "auditId": "audit_001",
            "runId": run_id,
            "stepId": f"{run_id}-step-001",
            "requestId": "toolreq_001",
            "actorType": "bastion",
            "eventKind": "policy_evaluated",
            "occurredAt": "2026-03-15T12:00:00Z",
            "payload": {
                "reasonCode": "read_only_lookup_allowed",
                "decision": "allow",
            },
        }
    ]
