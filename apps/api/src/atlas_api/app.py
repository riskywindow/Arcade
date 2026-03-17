from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse

from atlas_api.config import ApiConfig, load_config
from atlas_api.schemas import (
    AddTicketNoteRequest,
    BenchmarkCatalogResponse,
    BenchmarkCatalogSchema,
    BenchmarkRunResultResponse,
    BenchmarkRunResultSchema,
    ApprovalDecisionRequest,
    ApprovalListResponse,
    ApprovalResponse,
    ApprovalRequestSchema,
    AuditListResponse,
    AuditRecordSchema,
    AssignTicketRequest,
    ArtifactListResponse,
    ArtifactSchema,
    CreateRunRequest,
    DirectoryEmployeeDetailResponse,
    DirectoryEmployeeDetailSchema,
    DirectoryEmployeeListResponse,
    DirectoryEmployeeSchema,
    HelpdeskTicketDetailResponse,
    HelpdeskTicketDetailSchema,
    HelpdeskTicketQueueResponse,
    HelpdeskTicketResponse,
    HelpdeskTicketSchema,
    InboxThreadListResponse,
    InboxThreadResponse,
    InboxThreadSchema,
    RunEventListResponse,
    RunEventSchema,
    RunListResponse,
    RunReplayResponse,
    RunReplaySchema,
    RunResponse,
    RunSchema,
    StopRunRequest,
    StopRunResponse,
    TransitionTicketStatusRequest,
    WikiDocumentListResponse,
    WikiDocumentResponse,
    WikiDocumentSchema,
    WikiSearchResponseSchema,
    WikiSearchResultSchema,
)
from atlas_core import (
    ActorType,
    ApprovalRequestedPayload,
    ApprovalRequestRef,
    ApprovalRequestStatus,
    ApprovalResolvedPayload,
    AuditEventKind,
    AuditRecordEnvelope,
    AuditRecordedPayload,
    BenchmarkCatalog,
    BenchmarkRunItemResult,
    BenchmarkRunResult,
    EnvironmentRef,
    GradeOutcome,
    GradeResult,
    Run,
    RunAlreadyExistsError,
    RunCompletedPayload,
    RunEvent,
    RunEventSource,
    RunEventType,
    RunNotFoundError,
    RunRepository,
    RunReplay,
    RunScoreSummary,
    RunResumedPayload,
    RunStopRequestedPayload,
    ScenarioRef,
    RunService,
    RunStatus,
    TaskRef,
    build_replay_outcome_explanation,
    build_run_replay,
    build_run_score_summary,
    benchmark_entry_run_id,
    build_benchmark_aggregate,
    open_run_store_connection,
)
from atlas_env_helpdesk import (
    EmployeeNotFoundError,
    HelpdeskService,
    HelpdeskTicketNotFoundError,
    InboxThreadNotFoundError,
    InvalidTicketTransitionError,
    TicketStatus,
    WikiDocumentNotFoundError,
    get_benchmark_catalog_v0,
    get_scenario_definition,
)


def get_run_service(request: Request):
    infrastructure_config = request.app.state.infrastructure_config
    conn = open_run_store_connection(infrastructure_config.postgres_dsn(), autocommit=True)
    schema_name = getattr(request.app.state, "database_schema", None)
    if schema_name:
        conn.execute("select set_config('search_path', %s, false)", (schema_name,))
    try:
        yield RunService(RunRepository(conn))
    finally:
        conn.close()


def _to_run_schema(run: Run, score_summary: RunScoreSummary | None = None) -> RunSchema:
    payload = run.model_dump(mode="json")
    if score_summary is not None:
        payload["score_summary"] = score_summary.model_dump(mode="json")
    return RunSchema.model_validate(payload)


def _to_run_event_schema(event) -> RunEventSchema:
    return RunEventSchema.model_validate(event.model_dump(mode="json"))


def _to_artifact_schema(artifact) -> ArtifactSchema:
    return ArtifactSchema.model_validate(artifact.model_dump(mode="json"))


def _to_run_replay_schema(replay: RunReplay) -> RunReplaySchema:
    return RunReplaySchema.model_validate(replay.model_dump(mode="json"))


def _to_benchmark_catalog_schema(catalog: BenchmarkCatalog) -> BenchmarkCatalogSchema:
    return BenchmarkCatalogSchema.model_validate(catalog.model_dump(mode="json"))


def _to_benchmark_run_result_schema(result: BenchmarkRunResult) -> BenchmarkRunResultSchema:
    return BenchmarkRunResultSchema.model_validate(result.model_dump(mode="json"))


def _score_summary_for_run(
    run: Run,
    *,
    run_service: RunService,
    events: list[RunEvent] | None = None,
    artifacts: list | None = None,
) -> RunScoreSummary:
    run_events = events if events is not None else run_service.list_run_events(run.run_id)
    run_artifacts = artifacts if artifacts is not None else run_service.list_run_artifacts(run.run_id)
    return build_run_score_summary(run, run_events, run_artifacts)


def _benchmark_catalog(catalog_id: str) -> BenchmarkCatalog:
    if catalog_id == "helpdesk-v0":
        return get_benchmark_catalog_v0()
    raise KeyError(f"unknown benchmark catalog: {catalog_id}")


def _benchmark_result(
    *,
    catalog: BenchmarkCatalog,
    benchmark_run_id: str,
    run_service: RunService,
) -> BenchmarkRunResult:
    items: list[BenchmarkRunItemResult] = []
    started_at = None
    completed_at = None
    seed = None
    for entry in catalog.entries:
        run_id = benchmark_entry_run_id(benchmark_run_id, entry.entry_id)
        run = run_service.get_run(run_id)
        if run is None:
            raise RunNotFoundError(f"run {run_id} does not exist")
        events = run_service.list_run_events(run_id)
        artifacts = run_service.list_run_artifacts(run_id)
        score_summary = build_run_score_summary(run, events, artifacts)
        items.append(
            BenchmarkRunItemResult(
                entry_id=entry.entry_id,
                run_id=run_id,
                scenario_id=entry.scenario_id,
                task_id=entry.task_id,
                task_title=entry.task_title,
                final_status=run.status.value,
                score_summary=score_summary,
            )
        )
        started_at = run.created_at if started_at is None else min(started_at, run.created_at)
        run_completed_at = run.completed_at or run.updated_at
        completed_at = (
            run_completed_at if completed_at is None else max(completed_at, run_completed_at)
        )
        seed = run.scenario.scenario_seed if seed is None else seed
    return BenchmarkRunResult(
        benchmark_run_id=benchmark_run_id,
        catalog_id=catalog.catalog_id,
        seed=seed or "seed-phase3-demo",
        started_at=started_at,
        completed_at=completed_at,
        items=tuple(items),
        aggregate=build_benchmark_aggregate(tuple(items)),
    )


def _apply_outcome_objective(replay: RunReplay) -> RunReplay:
    try:
        scenario = get_scenario_definition(replay.run.scenario.scenario_id)
    except KeyError:
        return replay
    return replay.model_copy(
        update={
            "outcome_explanation": build_replay_outcome_explanation(
                replay,
                objective=scenario.public_task.success_condition,
            )
        }
    )


def _to_approval_schema(approval: ApprovalRequestRef) -> ApprovalRequestSchema:
    return ApprovalRequestSchema.model_validate(approval.model_dump(mode="json"))


def _to_audit_record_schema(record: AuditRecordEnvelope) -> AuditRecordSchema:
    return AuditRecordSchema.model_validate(record.model_dump(mode="json"))


def get_helpdesk_service(request: Request) -> HelpdeskService:
    return request.app.state.helpdesk_service


def _to_helpdesk_ticket_schema(ticket) -> HelpdeskTicketSchema:
    return HelpdeskTicketSchema.model_validate(ticket.model_dump(mode="json"))


def _to_helpdesk_ticket_detail_schema(detail) -> HelpdeskTicketDetailSchema:
    return HelpdeskTicketDetailSchema.model_validate(detail.model_dump(mode="json"))


def _to_directory_employee_schema(employee) -> DirectoryEmployeeSchema:
    return DirectoryEmployeeSchema.model_validate(employee.model_dump(mode="json"))


def _to_directory_employee_detail_schema(detail) -> DirectoryEmployeeDetailSchema:
    return DirectoryEmployeeDetailSchema.model_validate(detail.model_dump(mode="json"))


def _to_wiki_document_schema(document) -> WikiDocumentSchema:
    return WikiDocumentSchema.model_validate(document.model_dump(mode="json"))


def _to_inbox_thread_schema(thread) -> InboxThreadSchema:
    return InboxThreadSchema.model_validate(thread.model_dump(mode="json"))


def _approval_requests_for_run(run_service: RunService, run_id: str) -> dict[str, ApprovalRequestRef]:
    approvals: dict[str, ApprovalRequestRef] = {}
    for event in run_service.list_run_events(run_id):
        if event.event_type == RunEventType.APPROVAL_REQUESTED:
            requested_payload = cast(ApprovalRequestedPayload, event.payload)
            approval = ApprovalRequestRef.model_validate(requested_payload.approval_request)
            approvals[approval.approval_request_id] = approval
        elif event.event_type == RunEventType.APPROVAL_RESOLVED:
            resolved_payload = cast(ApprovalResolvedPayload, event.payload)
            approval = ApprovalRequestRef.model_validate(resolved_payload.approval_request)
            approvals[approval.approval_request_id] = approval
    return approvals


def _audit_records_for_run(run_service: RunService, run_id: str) -> list[AuditRecordEnvelope]:
    records: list[AuditRecordEnvelope] = []
    for event in run_service.list_run_events(run_id):
        if event.event_type == RunEventType.AUDIT_RECORDED:
            payload = cast(AuditRecordedPayload, event.payload)
            records.append(AuditRecordEnvelope.model_validate(payload.audit_record))
    return records


def _latest_stop_request_for_run(
    run_service: RunService,
    run_id: str,
) -> RunStopRequestedPayload | None:
    for event in reversed(run_service.list_run_events(run_id)):
        if event.event_type == RunEventType.RUN_COMPLETED:
            return None
        if event.event_type == RunEventType.RUN_STOP_REQUESTED:
            return cast(RunStopRequestedPayload, event.payload)
    return None


def create_app(config: ApiConfig | None = None) -> FastAPI:
    app_config = config or load_config()
    service_config = app_config.service
    app = FastAPI(title="Atlas API", version="0.1.0")
    app.state.service_config = service_config
    app.state.infrastructure_config = app_config.infrastructure
    app.state.database_schema = None
    app.state.helpdesk_service = HelpdeskService.seeded("seed-phase3-demo")

    @app.get("/health")
    def health() -> dict[str, str]:
        return service_config.health_payload()

    @app.get("/environments/helpdesk/tickets", response_model=HelpdeskTicketQueueResponse)
    def list_helpdesk_tickets(
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> HelpdeskTicketQueueResponse:
        queue = helpdesk_service.list_ticket_queue()
        return HelpdeskTicketQueueResponse(
            seed=queue.seed,
            tickets=[_to_helpdesk_ticket_schema(ticket) for ticket in queue.tickets],
        )

    @app.get(
        "/environments/helpdesk/tickets/{ticket_id}",
        response_model=HelpdeskTicketDetailResponse,
    )
    def get_helpdesk_ticket(
        ticket_id: str,
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> HelpdeskTicketDetailResponse:
        try:
            detail = helpdesk_service.get_ticket_detail(ticket_id)
        except HelpdeskTicketNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return HelpdeskTicketDetailResponse(detail=_to_helpdesk_ticket_detail_schema(detail))

    @app.post(
        "/environments/helpdesk/tickets/{ticket_id}/notes",
        response_model=HelpdeskTicketResponse,
    )
    def add_helpdesk_ticket_note(
        ticket_id: str,
        payload: AddTicketNoteRequest,
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> HelpdeskTicketResponse:
        # Operator/fixture-local mutation surface. The live agent path must
        # still reach helpdesk mutations through Bastion-owned tool adapters.
        try:
            ticket = helpdesk_service.add_note(
                ticket_id,
                author=payload.author,
                body=payload.body,
                kind=payload.kind,
            )
        except HelpdeskTicketNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return HelpdeskTicketResponse(ticket=_to_helpdesk_ticket_schema(ticket))

    @app.post(
        "/environments/helpdesk/tickets/{ticket_id}/assignment",
        response_model=HelpdeskTicketResponse,
    )
    def assign_helpdesk_ticket(
        ticket_id: str,
        payload: AssignTicketRequest,
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> HelpdeskTicketResponse:
        # Operator/fixture-local mutation surface. The live agent path must
        # still reach helpdesk mutations through Bastion-owned tool adapters.
        try:
            ticket = helpdesk_service.assign_ticket(
                ticket_id,
                assigned_to=payload.assigned_to,
            )
        except HelpdeskTicketNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return HelpdeskTicketResponse(ticket=_to_helpdesk_ticket_schema(ticket))

    @app.post(
        "/environments/helpdesk/tickets/{ticket_id}/status",
        response_model=HelpdeskTicketResponse,
    )
    def transition_helpdesk_ticket_status(
        ticket_id: str,
        payload: TransitionTicketStatusRequest,
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> HelpdeskTicketResponse:
        # Operator/fixture-local mutation surface. The live agent path must
        # still reach helpdesk mutations through Bastion-owned tool adapters.
        try:
            ticket = helpdesk_service.transition_ticket_status(
                ticket_id,
                status=TicketStatus(payload.status),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"unsupported ticket status {payload.status}",
            ) from exc
        except HelpdeskTicketNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidTicketTransitionError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return HelpdeskTicketResponse(ticket=_to_helpdesk_ticket_schema(ticket))

    @app.post("/environments/helpdesk/reset", response_model=HelpdeskTicketQueueResponse)
    def reset_helpdesk_environment(
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> HelpdeskTicketQueueResponse:
        queue = helpdesk_service.reset()
        return HelpdeskTicketQueueResponse(
            seed=queue.seed,
            tickets=[_to_helpdesk_ticket_schema(ticket) for ticket in queue.tickets],
        )

    @app.get(
        "/environments/helpdesk/directory/employees",
        response_model=DirectoryEmployeeListResponse,
    )
    def list_directory_employees(
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> DirectoryEmployeeListResponse:
        directory = helpdesk_service.list_employees()
        return DirectoryEmployeeListResponse(
            seed=directory.seed,
            employees=[_to_directory_employee_schema(employee) for employee in directory.employees],
        )

    @app.get(
        "/environments/helpdesk/directory/employees/{employee_id}",
        response_model=DirectoryEmployeeDetailResponse,
    )
    def get_directory_employee(
        employee_id: str,
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> DirectoryEmployeeDetailResponse:
        try:
            detail = helpdesk_service.get_employee_detail(employee_id)
        except EmployeeNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return DirectoryEmployeeDetailResponse(
            detail=_to_directory_employee_detail_schema(detail)
        )

    @app.get(
        "/environments/helpdesk/wiki/documents",
        response_model=WikiDocumentListResponse,
    )
    def list_wiki_documents(
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> WikiDocumentListResponse:
        documents = helpdesk_service.list_wiki_documents()
        return WikiDocumentListResponse(
            seed=documents.seed,
            documents=[
                _to_wiki_document_schema(document) for document in documents.documents
            ],
        )

    @app.get(
        "/environments/helpdesk/wiki/documents/{slug}",
        response_model=WikiDocumentResponse,
    )
    def get_wiki_document(
        slug: str,
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> WikiDocumentResponse:
        try:
            document = helpdesk_service.get_wiki_document(slug)
        except WikiDocumentNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return WikiDocumentResponse(document=_to_wiki_document_schema(document))

    @app.get(
        "/environments/helpdesk/wiki/search",
        response_model=WikiSearchResponseSchema,
    )
    def search_wiki_documents(
        q: str,
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> WikiSearchResponseSchema:
        response = helpdesk_service.search_wiki_documents(q)
        return WikiSearchResponseSchema(
            seed=response.seed,
            query=response.query,
            results=[
                WikiSearchResultSchema(
                    document=_to_wiki_document_schema(result.document),
                    score=result.score,
                    matched_terms=list(result.matched_terms),
                )
                for result in response.results
            ],
        )

    @app.get(
        "/environments/helpdesk/inbox/threads",
        response_model=InboxThreadListResponse,
    )
    def list_inbox_threads(
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> InboxThreadListResponse:
        threads = helpdesk_service.list_inbox_threads()
        return InboxThreadListResponse(
            seed=threads.seed,
            threads=[_to_inbox_thread_schema(thread) for thread in threads.threads],
        )

    @app.get(
        "/environments/helpdesk/inbox/threads/{thread_id}",
        response_model=InboxThreadResponse,
    )
    def get_inbox_thread(
        thread_id: str,
        helpdesk_service: HelpdeskService = Depends(get_helpdesk_service),
    ) -> InboxThreadResponse:
        try:
            thread = helpdesk_service.get_inbox_thread(thread_id)
        except InboxThreadNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return InboxThreadResponse(thread=_to_inbox_thread_schema(thread))

    @app.get("/benchmarks/catalogs/{catalog_id}", response_model=BenchmarkCatalogResponse)
    def get_benchmark_catalog(
        catalog_id: str,
    ) -> BenchmarkCatalogResponse:
        try:
            catalog = _benchmark_catalog(catalog_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return BenchmarkCatalogResponse(catalog=_to_benchmark_catalog_schema(catalog))

    @app.get(
        "/benchmarks/catalogs/{catalog_id}/runs/{benchmark_run_id}",
        response_model=BenchmarkRunResultResponse,
    )
    def get_benchmark_run_result(
        catalog_id: str,
        benchmark_run_id: str,
        run_service: RunService = Depends(get_run_service),
    ) -> BenchmarkRunResultResponse:
        try:
            catalog = _benchmark_catalog(catalog_id)
            result = _benchmark_result(
                catalog=catalog,
                benchmark_run_id=benchmark_run_id,
                run_service=run_service,
            )
        except (KeyError, RunNotFoundError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return BenchmarkRunResultResponse(result=_to_benchmark_run_result_schema(result))

    @app.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
    def create_run(
        payload: CreateRunRequest,
        run_service: RunService = Depends(get_run_service),
    ) -> RunResponse:
        timestamp = datetime.now(UTC)
        run = Run(
            run_id=f"run_{uuid4().hex}",
            environment=EnvironmentRef.model_validate(payload.environment.model_dump()),
            scenario=ScenarioRef.model_validate(payload.scenario.model_dump()),
            task=TaskRef.model_validate(payload.task.model_dump()),
            status=RunStatus.PENDING,
            created_at=timestamp,
            updated_at=timestamp,
            active_agent_id=payload.active_agent_id,
        )
        try:
            created = run_service.create_run(run)
        except RunAlreadyExistsError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return RunResponse(
            run=_to_run_schema(
                created,
                _score_summary_for_run(created, run_service=run_service, events=[], artifacts=[]),
            )
        )

    @app.get("/runs", response_model=RunListResponse)
    def list_runs(
        run_service: RunService = Depends(get_run_service),
    ) -> RunListResponse:
        runs = run_service.list_runs()
        return RunListResponse(
            runs=[
                _to_run_schema(run, _score_summary_for_run(run, run_service=run_service))
                for run in runs
            ]
        )

    @app.get("/runs/{run_id}", response_model=RunResponse)
    def get_run(
        run_id: str,
        run_service: RunService = Depends(get_run_service),
    ) -> RunResponse:
        try:
            run = run_service.get_run(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return RunResponse(
            run=_to_run_schema(run, _score_summary_for_run(run, run_service=run_service))
        )

    @app.get("/runs/{run_id}/events", response_model=RunEventListResponse)
    def list_run_events(
        run_id: str,
        run_service: RunService = Depends(get_run_service),
    ) -> RunEventListResponse:
        try:
            events = run_service.list_run_events(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return RunEventListResponse(
            run_id=run_id,
            events=[_to_run_event_schema(event) for event in events],
        )

    @app.get("/runs/{run_id}/replay", response_model=RunReplayResponse)
    def get_run_replay(
        run_id: str,
        run_service: RunService = Depends(get_run_service),
    ) -> RunReplayResponse:
        try:
            run = run_service.get_run(run_id)
            events = run_service.list_run_events(run_id)
            artifacts = run_service.list_run_artifacts(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        replay = _apply_outcome_objective(build_run_replay(run, events, artifacts))
        return RunReplayResponse(replay=_to_run_replay_schema(replay))

    @app.get("/runs/{run_id}/audit", response_model=AuditListResponse)
    def list_run_audit(
        run_id: str,
        run_service: RunService = Depends(get_run_service),
    ) -> AuditListResponse:
        try:
            records = _audit_records_for_run(run_service, run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return AuditListResponse(
            run_id=run_id,
            records=[_to_audit_record_schema(record) for record in records],
        )

    @app.get("/runs/{run_id}/approvals", response_model=ApprovalListResponse)
    def list_run_approvals(
        run_id: str,
        run_service: RunService = Depends(get_run_service),
    ) -> ApprovalListResponse:
        try:
            approvals = _approval_requests_for_run(run_service, run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return ApprovalListResponse(
            run_id=run_id,
            approvals=[_to_approval_schema(approval) for approval in approvals.values()],
        )

    @app.post("/runs/{run_id}/stop", response_model=StopRunResponse)
    def stop_run(
        run_id: str,
        payload: StopRunRequest,
        run_service: RunService = Depends(get_run_service),
    ) -> StopRunResponse:
        try:
            run = run_service.get_run(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        if run.status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"run {run_id} is already terminal",
            )

        existing_request = _latest_stop_request_for_run(run_service, run_id)
        if existing_request is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"run {run_id} already has an active stop request",
            )

        requested_at = datetime.now(UTC)
        stop_request_id = f"stop_{uuid4().hex[:12]}"
        operator_id = payload.operator_id

        run_service.append_run_event(
            RunEvent(
                event_id=f"{run_id}-event-stop-requested-{stop_request_id}",
                run_id=run_id,
                sequence=run_service.next_event_sequence(run_id),
                occurred_at=requested_at,
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id=stop_request_id,
                event_type=RunEventType.RUN_STOP_REQUESTED,
                payload=RunStopRequestedPayload(
                    event_type=RunEventType.RUN_STOP_REQUESTED,
                    run_id=run_id,
                    stop_request_id=stop_request_id,
                    operator_id=operator_id,
                    requested_at=requested_at,
                    reason=payload.reason,
                ),
            )
        )
        run_service.append_run_event(
            RunEvent(
                event_id=f"{run_id}-event-audit-stop-requested-{stop_request_id}",
                run_id=run_id,
                sequence=run_service.next_event_sequence(run_id),
                occurred_at=requested_at,
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id=stop_request_id,
                event_type=RunEventType.AUDIT_RECORDED,
                payload=AuditRecordedPayload(
                    event_type=RunEventType.AUDIT_RECORDED,
                    run_id=run_id,
                    audit_record=AuditRecordEnvelope(
                        audit_id=f"audit-stop-requested-{stop_request_id}",
                        run_id=run_id,
                        actor_type=ActorType.OPERATOR,
                        event_kind=AuditEventKind.KILL_SWITCH_TRIGGERED,
                        occurred_at=requested_at,
                        payload={
                            "phase": "requested",
                            "stopRequestId": stop_request_id,
                            "operatorId": operator_id,
                            "reason": payload.reason,
                        },
                    ).model_dump(mode="json"),
                ),
            )
        )

        current_status = run.status
        if run.status != RunStatus.RUNNING:
            run_service.append_run_event(
                RunEvent(
                    event_id=f"{run_id}-event-audit-stop-completed-{stop_request_id}",
                    run_id=run_id,
                    sequence=run_service.next_event_sequence(run_id),
                    occurred_at=requested_at,
                    source=RunEventSource.OPERATOR,
                    actor_type=ActorType.OPERATOR,
                    correlation_id=stop_request_id,
                    event_type=RunEventType.AUDIT_RECORDED,
                    payload=AuditRecordedPayload(
                        event_type=RunEventType.AUDIT_RECORDED,
                        run_id=run_id,
                        audit_record=AuditRecordEnvelope(
                            audit_id=f"audit-stop-completed-{stop_request_id}",
                            run_id=run_id,
                            actor_type=ActorType.OPERATOR,
                            event_kind=AuditEventKind.KILL_SWITCH_TRIGGERED,
                            occurred_at=requested_at,
                            payload={
                                "phase": "completed",
                                "stopRequestId": stop_request_id,
                                "operatorId": operator_id,
                                "reason": payload.reason,
                            },
                        ).model_dump(mode="json"),
                    ),
                )
            )
            run_service.append_run_event(
                RunEvent(
                    event_id=f"{run_id}-event-completed-stop-{stop_request_id}",
                    run_id=run_id,
                    sequence=run_service.next_event_sequence(run_id),
                    occurred_at=requested_at,
                    source=RunEventSource.OPERATOR,
                    actor_type=ActorType.OPERATOR,
                    correlation_id=stop_request_id,
                    event_type=RunEventType.RUN_COMPLETED,
                    payload=RunCompletedPayload(
                        event_type=RunEventType.RUN_COMPLETED,
                        run_id=run_id,
                        final_status=RunStatus.CANCELLED,
                        completed_at=requested_at,
                        grade_result=GradeResult(
                            outcome=GradeOutcome.NOT_GRADED,
                            summary="Run interrupted by operator kill switch.",
                            details={
                                "terminationReason": "cancelled",
                                "stopRequestId": stop_request_id,
                                "stopRequestedBy": operator_id,
                                "stopReason": payload.reason,
                                "interruptedByKillSwitch": True,
                            },
                        ),
                    ),
                )
            )
            current_status = RunStatus.CANCELLED

        return StopRunResponse(
            run_id=run_id,
            status=current_status,
            stop_request_id=stop_request_id,
            requested_at=requested_at,
        )

    @app.post("/runs/{run_id}/approvals/{approval_request_id}/approve", response_model=ApprovalResponse)
    def approve_run_action(
        run_id: str,
        approval_request_id: str,
        payload: ApprovalDecisionRequest,
        run_service: RunService = Depends(get_run_service),
    ) -> ApprovalResponse:
        try:
            run = run_service.get_run(run_id)
            approvals = _approval_requests_for_run(run_service, run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        approval = approvals.get(approval_request_id)
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"approval {approval_request_id} does not exist")
        if run.status != RunStatus.WAITING_APPROVAL:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"run {run_id} is not waiting for approval")
        if approval.status != ApprovalRequestStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"approval {approval_request_id} is already resolved")

        decided_at = datetime.now(UTC)
        approved = approval.model_copy(
            update={
                "status": ApprovalRequestStatus.APPROVED,
                "resolved_at": decided_at,
                "resolution_summary": payload.resolution_summary,
            }
        )
        run_service.append_run_event(
            RunEvent(
                event_id=f"{run_id}-event-approval-resolved-{approval_request_id}",
                run_id=run_id,
                sequence=run_service.next_event_sequence(run_id),
                occurred_at=decided_at,
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id=approval_request_id,
                event_type=RunEventType.APPROVAL_RESOLVED,
                payload=ApprovalResolvedPayload(
                    event_type=RunEventType.APPROVAL_RESOLVED,
                    run_id=run_id,
                    approval_request=approved.model_dump(mode="json"),
                    operator_id=payload.operator_id,
                    decided_at=decided_at,
                ),
            )
        )
        run_service.append_run_event(
            RunEvent(
                event_id=f"{run_id}-event-audit-approval-approved-{approval_request_id}",
                run_id=run_id,
                sequence=run_service.next_event_sequence(run_id),
                occurred_at=decided_at,
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id=approval_request_id,
                event_type=RunEventType.AUDIT_RECORDED,
                payload=AuditRecordedPayload(
                    event_type=RunEventType.AUDIT_RECORDED,
                    run_id=run_id,
                    audit_record=AuditRecordEnvelope(
                        audit_id=f"audit-approval-approved-{approval_request_id}",
                        run_id=run_id,
                        step_id=approved.step_id,
                        request_id=None,
                        actor_type=ActorType.OPERATOR,
                        event_kind=AuditEventKind.APPROVAL_RESOLVED,
                        occurred_at=decided_at,
                        payload={
                            "approvalRequestId": approval_request_id,
                            "operatorId": payload.operator_id,
                            "decision": "approved",
                        },
                    ).model_dump(mode="json"),
                ),
            )
        )
        run_service.append_run_event(
            RunEvent(
                event_id=f"{run_id}-event-run-resumed-{approval_request_id}",
                run_id=run_id,
                sequence=run_service.next_event_sequence(run_id),
                occurred_at=decided_at,
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id=approval_request_id,
                event_type=RunEventType.RUN_RESUMED,
                payload=RunResumedPayload(
                    event_type=RunEventType.RUN_RESUMED,
                    run_id=run_id,
                    status=RunStatus.RUNNING,
                    approval_request_id=approval_request_id,
                    resumed_at=decided_at,
                ),
            )
        )
        return ApprovalResponse(approval=_to_approval_schema(approved))

    @app.post("/runs/{run_id}/approvals/{approval_request_id}/deny", response_model=ApprovalResponse)
    def deny_run_action(
        run_id: str,
        approval_request_id: str,
        payload: ApprovalDecisionRequest,
        run_service: RunService = Depends(get_run_service),
    ) -> ApprovalResponse:
        try:
            run = run_service.get_run(run_id)
            approvals = _approval_requests_for_run(run_service, run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        approval = approvals.get(approval_request_id)
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"approval {approval_request_id} does not exist")
        if run.status != RunStatus.WAITING_APPROVAL:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"run {run_id} is not waiting for approval")
        if approval.status != ApprovalRequestStatus.PENDING:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"approval {approval_request_id} is already resolved")

        decided_at = datetime.now(UTC)
        denied = approval.model_copy(
            update={
                "status": ApprovalRequestStatus.REJECTED,
                "resolved_at": decided_at,
                "resolution_summary": payload.resolution_summary,
            }
        )
        run_service.append_run_event(
            RunEvent(
                event_id=f"{run_id}-event-approval-resolved-{approval_request_id}",
                run_id=run_id,
                sequence=run_service.next_event_sequence(run_id),
                occurred_at=decided_at,
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id=approval_request_id,
                event_type=RunEventType.APPROVAL_RESOLVED,
                payload=ApprovalResolvedPayload(
                    event_type=RunEventType.APPROVAL_RESOLVED,
                    run_id=run_id,
                    approval_request=denied.model_dump(mode="json"),
                    operator_id=payload.operator_id,
                    decided_at=decided_at,
                ),
            )
        )
        run_service.append_run_event(
            RunEvent(
                event_id=f"{run_id}-event-audit-approval-denied-{approval_request_id}",
                run_id=run_id,
                sequence=run_service.next_event_sequence(run_id),
                occurred_at=decided_at,
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id=approval_request_id,
                event_type=RunEventType.AUDIT_RECORDED,
                payload=AuditRecordedPayload(
                    event_type=RunEventType.AUDIT_RECORDED,
                    run_id=run_id,
                    audit_record=AuditRecordEnvelope(
                        audit_id=f"audit-approval-denied-{approval_request_id}",
                        run_id=run_id,
                        step_id=denied.step_id,
                        request_id=None,
                        actor_type=ActorType.OPERATOR,
                        event_kind=AuditEventKind.APPROVAL_RESOLVED,
                        occurred_at=decided_at,
                        payload={
                            "approvalRequestId": approval_request_id,
                            "operatorId": payload.operator_id,
                            "decision": "denied",
                        },
                    ).model_dump(mode="json"),
                ),
            )
        )
        run_service.append_run_event(
            RunEvent(
                event_id=f"{run_id}-event-completed-approval-denied",
                run_id=run_id,
                sequence=run_service.next_event_sequence(run_id),
                occurred_at=decided_at,
                source=RunEventSource.OPERATOR,
                actor_type=ActorType.OPERATOR,
                correlation_id=approval_request_id,
                event_type=RunEventType.RUN_COMPLETED,
                payload=RunCompletedPayload(
                    event_type=RunEventType.RUN_COMPLETED,
                    run_id=run_id,
                    final_status=RunStatus.FAILED,
                    completed_at=decided_at,
                    grade_result=GradeResult(
                        outcome=GradeOutcome.NOT_GRADED,
                        summary="Run failed after approval was denied.",
                        details={
                            "terminationReason": "approval_denied",
                            "approvalRequestId": approval_request_id,
                            "operatorId": payload.operator_id,
                            "resolutionSummary": payload.resolution_summary,
                        },
                    ),
                ),
            )
        )
        return ApprovalResponse(approval=_to_approval_schema(denied))

    @app.get("/runs/{run_id}/artifacts", response_model=ArtifactListResponse)
    def list_run_artifacts(
        run_id: str,
        run_service: RunService = Depends(get_run_service),
    ) -> ArtifactListResponse:
        try:
            artifacts = run_service.list_run_artifacts(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return ArtifactListResponse(
            run_id=run_id,
            artifacts=[_to_artifact_schema(artifact) for artifact in artifacts],
        )

    @app.get("/runs/{run_id}/artifacts/{artifact_id}/content")
    def get_run_artifact_content(
        run_id: str,
        artifact_id: str,
        run_service: RunService = Depends(get_run_service),
    ) -> FileResponse:
        try:
            artifacts = run_service.list_run_artifacts(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        artifact = next((item for item in artifacts if item.artifact_id == artifact_id), None)
        if artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"artifact {artifact_id} does not exist for run {run_id}",
            )

        artifact_path = Path(artifact.uri)
        if not artifact_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"artifact {artifact_id} is not available as a local file",
            )

        filename = artifact.display_name or artifact_path.name
        return FileResponse(
            path=artifact_path,
            media_type=artifact.content_type,
            filename=filename,
        )

    return app
