from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status

from atlas_api.config import ApiConfig, load_config
from atlas_api.schemas import (
    ArtifactListResponse,
    ArtifactSchema,
    CreateRunRequest,
    RunEventListResponse,
    RunEventSchema,
    RunListResponse,
    RunResponse,
    RunSchema,
)
from atlas_core import (
    EnvironmentRef,
    Run,
    RunAlreadyExistsError,
    RunNotFoundError,
    RunRepository,
    ScenarioRef,
    RunService,
    RunStatus,
    TaskRef,
    open_run_store_connection,
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


def _to_run_schema(run: Run) -> RunSchema:
    return RunSchema.model_validate(run.model_dump(mode="json"))


def _to_run_event_schema(event) -> RunEventSchema:
    return RunEventSchema.model_validate(event.model_dump(mode="json"))


def _to_artifact_schema(artifact) -> ArtifactSchema:
    return ArtifactSchema.model_validate(artifact.model_dump(mode="json"))


def create_app(config: ApiConfig | None = None) -> FastAPI:
    app_config = config or load_config()
    service_config = app_config.service
    app = FastAPI(title="Atlas API", version="0.1.0")
    app.state.service_config = service_config
    app.state.infrastructure_config = app_config.infrastructure
    app.state.database_schema = None

    @app.get("/health")
    def health() -> dict[str, str]:
        return service_config.health_payload()

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
        return RunResponse(run=_to_run_schema(created))

    @app.get("/runs", response_model=RunListResponse)
    def list_runs(
        run_service: RunService = Depends(get_run_service),
    ) -> RunListResponse:
        runs = run_service.list_runs()
        return RunListResponse(runs=[_to_run_schema(run) for run in runs])

    @app.get("/runs/{run_id}", response_model=RunResponse)
    def get_run(
        run_id: str,
        run_service: RunService = Depends(get_run_service),
    ) -> RunResponse:
        try:
            run = run_service.get_run(run_id)
        except RunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return RunResponse(run=_to_run_schema(run))

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

    return app
