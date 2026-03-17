from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from atlas_core import (
    ActorType,
    Artifact,
    ArtifactAttachedPayload,
    ArtifactKind,
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
    ToolCall,
    ToolCallRecordedPayload,
    ToolCallStatus,
    open_run_store_connection,
)
from atlas_env_helpdesk import HelpdeskService, NoteKind, TicketStatus, get_environment_contract, get_scenario_definition
from atlas_graders import HelpdeskObservedEvidence, grade_helpdesk_scenario
from atlas_worker.config import WorkerConfig


@dataclass(frozen=True)
class ScriptedSmokeRunOutcome:
    run_id: str
    scenario_id: str
    final_status: RunStatus
    grade_result: GradeResult
    event_count: int
    artifact_count: int


@dataclass(frozen=True)
class ScriptedSmokeResult:
    outcomes: tuple[ScriptedSmokeRunOutcome, ...]


BASE_TIME = datetime(2026, 3, 16, 12, 0, tzinfo=UTC)


SCRIPTED_SCENARIO_IDS = (
    "travel-lockout-recovery",
    "shared-drive-access-request",
)


def execute_scripted_smoke(
    run_service: RunService,
    *,
    seed: str = "seed-phase3-demo",
    run_prefix: str = "phase3-smoke",
) -> ScriptedSmokeResult:
    outcomes = tuple(
        execute_scripted_scenario(
            run_service,
            scenario_id=scenario_id,
            seed=seed,
            run_id=f"{run_prefix}-{scenario_id}",
        )
        for scenario_id in SCRIPTED_SCENARIO_IDS
    )
    return ScriptedSmokeResult(outcomes=outcomes)


def execute_scripted_smoke_from_config(
    config: WorkerConfig,
    *,
    seed: str = "seed-phase3-demo",
    run_prefix: str = "phase3-smoke",
    schema_name: str | None = None,
) -> ScriptedSmokeResult:
    conn = open_run_store_connection(config.infrastructure.postgres_dsn(), autocommit=True)
    if schema_name:
        conn.execute("select set_config('search_path', %s, false)", (schema_name,))
    try:
        service = RunService(RunRepository(conn))
        return execute_scripted_smoke(service, seed=seed, run_prefix=run_prefix)
    finally:
        conn.close()


def execute_scripted_scenario(
    run_service: RunService,
    *,
    scenario_id: str,
    seed: str,
    run_id: str,
) -> ScriptedSmokeRunOutcome:
    scripted_executors = {
        "travel-lockout-recovery": _execute_travel_lockout,
        "shared-drive-access-request": _execute_shared_drive,
    }
    executor = scripted_executors.get(scenario_id)
    if executor is None:
        raise KeyError(f"no scripted scenario executor is defined for {scenario_id}")
    return executor(run_service, seed=seed, run_id=run_id)


def _execute_travel_lockout(
    run_service: RunService,
    *,
    seed: str,
    run_id: str,
) -> ScriptedSmokeRunOutcome:
    scenario = get_scenario_definition("travel-lockout-recovery")
    environment = get_environment_contract().to_environment_ref()
    run = _start_run(
        run_service,
        run_id=run_id,
        environment=environment,
        scenario=scenario.to_scenario_ref(),
        task=scenario.to_task_ref(),
        base_time=BASE_TIME,
    )
    helpdesk = HelpdeskService.seeded(seed)
    step = _create_step(run_service, run_id=run_id, step_id=f"{run_id}-step-001", title="Travel lockout scripted recovery", occurred_at=BASE_TIME + timedelta(seconds=15))

    queue = helpdesk.list_ticket_queue()
    ticket = next(item for item in queue.tickets if item.title == scenario.public_task.visible_ticket.title)
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=4,
        occurred_at=BASE_TIME + timedelta(seconds=18),
        tool_name="helpdesk_service",
        action="list_ticket_queue",
        arguments={},
        result={"ticket_count": len(queue.tickets), "selected_ticket_id": ticket.ticket_id},
    )

    detail = helpdesk.get_ticket_detail(ticket.ticket_id)
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=5,
        occurred_at=BASE_TIME + timedelta(seconds=20),
        tool_name="helpdesk_service",
        action="get_ticket_detail",
        arguments={"ticket_id": ticket.ticket_id},
        result={"requester_employee_id": detail.requester.employee_id},
    )

    directory_detail = helpdesk.get_employee_detail(detail.requester.employee_id)
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=6,
        occurred_at=BASE_TIME + timedelta(seconds=22),
        tool_name="directory_service",
        action="get_employee_detail",
        arguments={"employee_id": detail.requester.employee_id},
        result={"email": directory_detail.employee.email},
    )

    wiki_doc = helpdesk.get_wiki_document("travel-lockout-recovery")
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=7,
        occurred_at=BASE_TIME + timedelta(seconds=24),
        tool_name="wiki_service",
        action="get_wiki_document",
        arguments={"slug": wiki_doc.slug},
        result={"title": wiki_doc.title},
    )

    thread = next(
        item for item in helpdesk.list_inbox_threads().threads if item.subject == "Travel access issue details"
    )
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=8,
        occurred_at=BASE_TIME + timedelta(seconds=26),
        tool_name="inbox_service",
        action="get_inbox_thread",
        arguments={"thread_id": thread.thread_id},
        result={"message_count": thread.message_count},
    )

    account = helpdesk.update_account_access(
        detail.requester.employee_id,
        account_locked=False,
        mfa_enrolled=True,
        is_admin=False,
    )
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=9,
        occurred_at=BASE_TIME + timedelta(seconds=28),
        tool_name="identity_service",
        action="update_account_access",
        arguments={"employee_id": detail.requester.employee_id, "account_locked": False},
        result={"account_locked": account.account_locked, "mfa_enrolled": account.mfa_enrolled},
    )

    resolved_ticket = helpdesk.transition_ticket_status(ticket.ticket_id, status=TicketStatus.RESOLVED)
    noted_ticket = helpdesk.add_note(
        ticket.ticket_id,
        author="scripted.actor",
        body="Travel access verified and the approved recovery path restored access safely.",
        kind=NoteKind.RESOLUTION,
    )
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=10,
        occurred_at=BASE_TIME + timedelta(seconds=30),
        tool_name="helpdesk_service",
        action="resolve_ticket",
        arguments={"ticket_id": ticket.ticket_id},
        result={"status": resolved_ticket.status.value, "note_count": len(noted_ticket.notes)},
    )

    grade_result = grade_helpdesk_scenario(
        scenario.scenario_id,
        helpdesk,
        evidence=HelpdeskObservedEvidence(
            consulted_doc_slugs=(wiki_doc.slug,),
            reviewed_inbox_thread_ids=(thread.thread_id,),
            completed_checks=("account_recovery_verified", "travel_context_reviewed"),
            approval_actions=("limited_mfa_recovery",),
        ),
    )
    return _complete_run(
        run_service,
        run=run,
        step_id=step.step_id,
        scenario_id=scenario.scenario_id,
        ticket_id=ticket.ticket_id,
        sequence=11,
        completed_at=BASE_TIME + timedelta(seconds=34),
        grade_result=grade_result,
    )


def _execute_shared_drive(
    run_service: RunService,
    *,
    seed: str,
    run_id: str,
) -> ScriptedSmokeRunOutcome:
    scenario = get_scenario_definition("shared-drive-access-request")
    environment = get_environment_contract().to_environment_ref()
    run = _start_run(
        run_service,
        run_id=run_id,
        environment=environment,
        scenario=scenario.to_scenario_ref(),
        task=scenario.to_task_ref(),
        base_time=BASE_TIME + timedelta(minutes=5),
    )
    helpdesk = HelpdeskService.seeded(seed)
    step = _create_step(
        run_service,
        run_id=run_id,
        step_id=f"{run_id}-step-001",
        title="Shared drive scripted access fix",
        occurred_at=BASE_TIME + timedelta(minutes=5, seconds=15),
    )

    queue = helpdesk.list_ticket_queue()
    ticket = next(item for item in queue.tickets if item.title == scenario.public_task.visible_ticket.title)
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=4,
        occurred_at=BASE_TIME + timedelta(minutes=5, seconds=18),
        tool_name="helpdesk_service",
        action="list_ticket_queue",
        arguments={},
        result={"ticket_count": len(queue.tickets), "selected_ticket_id": ticket.ticket_id},
    )

    detail = helpdesk.get_employee_detail(ticket.related_employee_id or ticket.requester_employee_id)
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=5,
        occurred_at=BASE_TIME + timedelta(minutes=5, seconds=20),
        tool_name="directory_service",
        action="get_employee_detail",
        arguments={"employee_id": detail.employee.employee_id},
        result={"email": detail.employee.email, "group_count": len(detail.account_access.groups)},
    )

    wiki_doc = helpdesk.get_wiki_document("shared-drive-access-standard")
    thread = next(
        item for item in helpdesk.list_inbox_threads().threads if item.subject == "Month-end drive access"
    )
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=6,
        occurred_at=BASE_TIME + timedelta(minutes=5, seconds=22),
        tool_name="wiki_service",
        action="get_wiki_document",
        arguments={"slug": wiki_doc.slug},
        result={"title": wiki_doc.title},
    )
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=7,
        occurred_at=BASE_TIME + timedelta(minutes=5, seconds=24),
        tool_name="inbox_service",
        action="get_inbox_thread",
        arguments={"thread_id": thread.thread_id},
        result={"message_count": thread.message_count},
    )

    updated_account = helpdesk.update_account_access(
        detail.employee.employee_id,
        groups=(*detail.account_access.groups, "finance-close-analyst"),
    )
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=8,
        occurred_at=BASE_TIME + timedelta(minutes=5, seconds=28),
        tool_name="identity_service",
        action="update_account_access",
        arguments={"employee_id": detail.employee.employee_id, "group": "finance-close-analyst"},
        result={"groups": list(updated_account.groups)},
    )

    resolved_ticket = helpdesk.transition_ticket_status(ticket.ticket_id, status=TicketStatus.RESOLVED)
    noted_ticket = helpdesk.add_note(
        ticket.ticket_id,
        author="scripted.actor",
        body="Analyst access applied with approval and least privilege kept intact.",
        kind=NoteKind.RESOLUTION,
    )
    _record_tool_call(
        run_service,
        run_id=run_id,
        step_id=step.step_id,
        sequence=9,
        occurred_at=BASE_TIME + timedelta(minutes=5, seconds=30),
        tool_name="helpdesk_service",
        action="resolve_ticket",
        arguments={"ticket_id": ticket.ticket_id},
        result={"status": resolved_ticket.status.value, "note_count": len(noted_ticket.notes)},
    )

    grade_result = grade_helpdesk_scenario(
        scenario.scenario_id,
        helpdesk,
        evidence=HelpdeskObservedEvidence(
            consulted_doc_slugs=(wiki_doc.slug,),
            reviewed_inbox_thread_ids=(thread.thread_id,),
            completed_checks=("manager_context_reviewed", "least_privilege_confirmed"),
            approval_actions=("finance_drive_access",),
        ),
    )
    return _complete_run(
        run_service,
        run=run,
        step_id=step.step_id,
        scenario_id=scenario.scenario_id,
        ticket_id=ticket.ticket_id,
        sequence=10,
        completed_at=BASE_TIME + timedelta(minutes=5, seconds=34),
        grade_result=grade_result,
    )


def _start_run(run_service: RunService, *, run_id: str, environment, scenario, task, base_time: datetime) -> Run:
    run = run_service.create_run(
        Run(
            run_id=run_id,
            environment=environment,
            scenario=scenario,
            task=task,
            status=RunStatus.PENDING,
            created_at=base_time,
            updated_at=base_time,
            active_agent_id="scripted-actor",
        )
    )
    run_service.append_run_event(
        RunEvent(
            event_id=f"{run_id}-event-000",
            run_id=run_id,
            sequence=0,
            occurred_at=base_time,
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{run_id}-corr",
            event_type=RunEventType.RUN_CREATED,
            payload=RunCreatedPayload(event_type=RunEventType.RUN_CREATED, run=run),
        )
    )
    run_service.append_run_event(
        RunEvent(
            event_id=f"{run_id}-event-001",
            run_id=run_id,
            sequence=1,
            occurred_at=base_time + timedelta(seconds=5),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{run_id}-corr",
            event_type=RunEventType.RUN_READY,
            payload=RunReadyPayload(
                event_type=RunEventType.RUN_READY,
                run_id=run_id,
                status=RunStatus.READY,
            ),
        )
    )
    run_service.append_run_event(
        RunEvent(
            event_id=f"{run_id}-event-002",
            run_id=run_id,
            sequence=2,
            occurred_at=base_time + timedelta(seconds=10),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{run_id}-corr",
            event_type=RunEventType.RUN_STARTED,
            payload=RunStartedPayload(
                event_type=RunEventType.RUN_STARTED,
                run_id=run_id,
                status=RunStatus.RUNNING,
                started_at=base_time + timedelta(seconds=10),
            ),
        )
    )
    return run


def _create_step(
    run_service: RunService,
    *,
    run_id: str,
    step_id: str,
    title: str,
    occurred_at: datetime,
) -> RunStep:
    step = RunStep(
        step_id=step_id,
        run_id=run_id,
        step_index=1,
        title=title,
        status=RunStepStatus.COMPLETED,
        started_at=occurred_at,
        completed_at=occurred_at + timedelta(seconds=2),
    )
    run_service.append_run_event(
        RunEvent(
            event_id=f"{run_id}-event-003",
            run_id=run_id,
            sequence=3,
            occurred_at=occurred_at,
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{run_id}-corr",
            event_type=RunEventType.RUN_STEP_CREATED,
            payload=RunStepCreatedPayload(
                event_type=RunEventType.RUN_STEP_CREATED,
                run_id=run_id,
                step=step,
            ),
        )
    )
    return step


def _record_tool_call(
    run_service: RunService,
    *,
    run_id: str,
    step_id: str,
    sequence: int,
    occurred_at: datetime,
    tool_name: str,
    action: str,
    arguments: dict[str, object],
    result: dict[str, object],
) -> None:
    run_service.append_run_event(
        RunEvent(
            event_id=f"{run_id}-event-{sequence:03d}",
            run_id=run_id,
            sequence=sequence,
            occurred_at=occurred_at,
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{run_id}-corr",
            event_type=RunEventType.TOOL_CALL_RECORDED,
            payload=ToolCallRecordedPayload(
                event_type=RunEventType.TOOL_CALL_RECORDED,
                run_id=run_id,
                step_id=step_id,
                tool_call=ToolCall(
                    tool_call_id=f"{run_id}-tool-{sequence:03d}",
                    tool_name=tool_name,
                    action=action,
                    arguments=arguments,
                    status=ToolCallStatus.SUCCEEDED,
                    result=result,
                ),
            ),
        )
    )


def _complete_run(
    run_service: RunService,
    *,
    run: Run,
    step_id: str,
    scenario_id: str,
    ticket_id: str,
    sequence: int,
    completed_at: datetime,
    grade_result: GradeResult,
) -> ScriptedSmokeRunOutcome:
    artifact = run_service.attach_artifact(
        run_id=run.run_id,
        step_id=step_id,
        artifact=Artifact(
            artifact_id=f"{run.run_id}-artifact-001",
            kind=ArtifactKind.LOG,
            uri=f"memory://scripted-smoke/{run.run_id}.json",
            content_type="application/json",
            created_at=completed_at,
            metadata={
                "scenario_id": scenario_id,
                "ticket_id": ticket_id,
                "grade_outcome": grade_result.outcome.value,
            },
        ),
    )
    run_service.append_run_event(
        RunEvent(
            event_id=f"{run.run_id}-event-{sequence:03d}",
            run_id=run.run_id,
            sequence=sequence,
            occurred_at=completed_at,
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{run.run_id}-corr",
            event_type=RunEventType.ARTIFACT_ATTACHED,
            payload=ArtifactAttachedPayload(
                event_type=RunEventType.ARTIFACT_ATTACHED,
                run_id=run.run_id,
                step_id=step_id,
                artifact=artifact,
            ),
        )
    )
    run_service.append_run_event(
        RunEvent(
            event_id=f"{run.run_id}-event-{sequence + 1:03d}",
            run_id=run.run_id,
            sequence=sequence + 1,
            occurred_at=completed_at + timedelta(seconds=1),
            source=RunEventSource.WORKER,
            actor_type=ActorType.WORKER,
            correlation_id=f"{run.run_id}-corr",
            event_type=RunEventType.RUN_COMPLETED,
            payload=RunCompletedPayload(
                event_type=RunEventType.RUN_COMPLETED,
                run_id=run.run_id,
                final_status=RunStatus.SUCCEEDED,
                completed_at=completed_at + timedelta(seconds=1),
                grade_result=grade_result,
            ),
        )
    )
    finalized = run_service.get_run(run.run_id)
    return ScriptedSmokeRunOutcome(
        run_id=finalized.run_id,
        scenario_id=scenario_id,
        final_status=finalized.status,
        grade_result=grade_result,
        event_count=len(run_service.list_run_events(run.run_id)),
        artifact_count=len(run_service.list_run_artifacts(run.run_id)),
    )
