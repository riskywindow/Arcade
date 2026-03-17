from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from atlas_core.domain import (
    Artifact,
    GradeResult,
    Run,
    RunCompletedPayload,
    RunEvent,
    RunEventType,
    RunStatus,
    RunStepCreatedPayload,
)
from atlas_core.serialization import (
    deserialize_artifact,
    deserialize_run_event,
    serialize_artifact,
    serialize_run_event_payload,
)
from atlas_core.run_state_machine import (
    InvalidRunEventTransitionError,
    InvalidRunTransitionError,
    TERMINAL_RUN_STATUSES,
    validate_event_transition,
    validate_run_transition,
)


class RunStoreError(Exception):
    """Base error for run persistence operations."""


class RunNotFoundError(RunStoreError):
    """Raised when a referenced Run does not exist."""


class RunAlreadyExistsError(RunStoreError):
    """Raised when attempting to create a duplicate Run."""


class EventSequenceConflictError(RunStoreError):
    """Raised when a RunEvent sequence is already in use for a Run."""


class ArtifactAlreadyExistsError(RunStoreError):
    """Raised when attempting to attach a duplicate Artifact."""


class InvalidRunFinalizationError(RunStoreError):
    """Raised when finalization data is structurally invalid."""


@dataclass(frozen=True)
class RunFinalization:
    final_status: RunStatus
    completed_at: datetime
    grade_result: GradeResult | None = None


def open_run_store_connection(
    dsn: str,
    *,
    autocommit: bool = False,
) -> Connection[dict[str, object]]:
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=autocommit)


class RunRepository:
    def __init__(self, conn: Connection[dict[str, object]]) -> None:
        self._conn = conn

    @contextmanager
    def transaction(self) -> Any:
        with self._conn.transaction():
            yield

    def create_run(self, run: Run) -> Run:
        try:
            self._conn.execute(
                """
                insert into runs (
                    run_id,
                    environment_id,
                    environment_name,
                    environment_version,
                    scenario_id,
                    scenario_name,
                    scenario_seed,
                    task_id,
                    task_kind,
                    task_title,
                    status,
                    created_at,
                    updated_at,
                    started_at,
                    completed_at,
                    current_step_index,
                    active_agent_id,
                    grade_result
                )
                values (
                    %(run_id)s,
                    %(environment_id)s,
                    %(environment_name)s,
                    %(environment_version)s,
                    %(scenario_id)s,
                    %(scenario_name)s,
                    %(scenario_seed)s,
                    %(task_id)s,
                    %(task_kind)s,
                    %(task_title)s,
                    %(status)s,
                    %(created_at)s,
                    %(updated_at)s,
                    %(started_at)s,
                    %(completed_at)s,
                    %(current_step_index)s,
                    %(active_agent_id)s,
                    %(grade_result)s::jsonb
                )
                """,
                self._run_insert_params(run),
            )
        except psycopg.errors.UniqueViolation as exc:
            raise RunAlreadyExistsError(f"run {run.run_id} already exists") from exc
        return run

    def get_run(self, run_id: str) -> Run | None:
        row = self._conn.execute(
            """
            select *
            from runs
            where run_id = %s
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_run(row)

    def list_runs(self, *, limit: int = 100) -> list[Run]:
        rows = self._conn.execute(
            """
            select *
            from runs
            order by created_at desc, run_id asc
            limit %s
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_run(row) for row in rows]

    def list_run_events(self, run_id: str) -> list[RunEvent]:
        rows = self._conn.execute(
            """
            select event_id, run_id, sequence, occurred_at, source, actor_type, correlation_id, event_type, payload
            from run_events
            where run_id = %s
            order by sequence asc
            """,
            (run_id,),
        ).fetchall()
        return [self._row_to_run_event(row) for row in rows]

    def list_run_artifacts(self, run_id: str) -> list[Artifact]:
        rows = self._conn.execute(
            """
            select artifact_id, run_id, step_id, kind, uri, content_type, created_at, sha256, size_bytes, metadata
            from run_artifacts
            where run_id = %s
            order by created_at asc, artifact_id asc
            """,
            (run_id,),
        ).fetchall()
        return [self._row_to_artifact(row) for row in rows]

    def next_event_sequence(self, run_id: str) -> int:
        row = self._conn.execute(
            """
            select coalesce(max(sequence) + 1, 0) as next_sequence
            from run_events
            where run_id = %s
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return 0
        return cast(int, row["next_sequence"])

    def append_run_event(self, event: RunEvent) -> RunEvent:
        try:
            self._conn.execute(
                """
                insert into run_events (
                    event_id,
                    run_id,
                    sequence,
                    occurred_at,
                    source,
                    actor_type,
                    correlation_id,
                    event_type,
                    payload
                )
                values (
                    %(event_id)s,
                    %(run_id)s,
                    %(sequence)s,
                    %(occurred_at)s,
                    %(source)s,
                    %(actor_type)s,
                    %(correlation_id)s,
                    %(event_type)s,
                    %(payload)s::jsonb
                )
                """,
                self._run_event_insert_params(event),
            )
        except psycopg.errors.ForeignKeyViolation as exc:
            raise RunNotFoundError(f"run {event.run_id} does not exist") from exc
        except psycopg.errors.UniqueViolation as exc:
            if "run_events_run_id_sequence_key" in str(exc):
                raise EventSequenceConflictError(
                    f"sequence {event.sequence} is already used for run {event.run_id}"
                ) from exc
            raise
        return event

    def attach_artifact(
        self,
        *,
        run_id: str,
        artifact: Artifact,
        step_id: str | None = None,
    ) -> Artifact:
        artifact_to_store = artifact.model_copy(update={"run_id": run_id, "step_id": step_id})
        try:
            self._conn.execute(
                """
                insert into run_artifacts (
                    artifact_id,
                    run_id,
                    step_id,
                    kind,
                    uri,
                    content_type,
                    created_at,
                    sha256,
                    size_bytes,
                    metadata
                )
                values (
                    %(artifact_id)s,
                    %(run_id)s,
                    %(step_id)s,
                    %(kind)s,
                    %(uri)s,
                    %(content_type)s,
                    %(created_at)s,
                    %(sha256)s,
                    %(size_bytes)s,
                    %(metadata)s::jsonb
                )
                """,
                self._artifact_insert_params(artifact=artifact_to_store),
            )
        except psycopg.errors.ForeignKeyViolation as exc:
            raise RunNotFoundError(f"run {run_id} does not exist") from exc
        except psycopg.errors.UniqueViolation as exc:
            raise ArtifactAlreadyExistsError(
                f"artifact {artifact.artifact_id} already exists"
            ) from exc
        return artifact_to_store

    def finalize_run(self, run_id: str, finalization: RunFinalization) -> Run:
        if finalization.final_status not in TERMINAL_RUN_STATUSES:
            raise InvalidRunFinalizationError(
                "final_status must be one of succeeded, failed, or cancelled"
            )
        row = self._conn.execute(
            """
            update runs
            set status = %(status)s,
                updated_at = %(completed_at)s,
                completed_at = %(completed_at)s,
                grade_result = %(grade_result)s::jsonb
            where run_id = %(run_id)s
            returning *
            """,
            {
                "run_id": run_id,
                "status": finalization.final_status,
                "completed_at": finalization.completed_at,
                "grade_result": self._json_document(
                    finalization.grade_result.model_dump(mode="json")
                    if finalization.grade_result is not None
                    else None
                ),
            },
        ).fetchone()
        if row is None:
            raise RunNotFoundError(f"run {run_id} does not exist")
        return self._row_to_run(row)

    def update_run_progress(
        self,
        run_id: str,
        *,
        status: RunStatus | None = None,
        updated_at: datetime,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        current_step_index: int | None = None,
        grade_result: GradeResult | None = None,
    ) -> Run:
        row = self._conn.execute(
            """
            update runs
            set status = coalesce(%(status)s, status),
                updated_at = %(updated_at)s,
                started_at = coalesce(%(started_at)s, started_at),
                completed_at = coalesce(%(completed_at)s, completed_at),
                current_step_index = coalesce(%(current_step_index)s, current_step_index),
                grade_result = case
                    when %(grade_result)s::jsonb is null then grade_result
                    else %(grade_result)s::jsonb
                end
            where run_id = %(run_id)s
            returning *
            """,
            {
                "run_id": run_id,
                "status": status,
                "updated_at": updated_at,
                "started_at": started_at,
                "completed_at": completed_at,
                "current_step_index": current_step_index,
                "grade_result": self._json_document(
                    grade_result.model_dump(mode="json") if grade_result is not None else None
                ),
            },
        ).fetchone()
        if row is None:
            raise RunNotFoundError(f"run {run_id} does not exist")
        return self._row_to_run(row)

    def _run_insert_params(self, run: Run) -> dict[str, object]:
        return {
            "run_id": run.run_id,
            "environment_id": run.environment.environment_id,
            "environment_name": run.environment.environment_name,
            "environment_version": run.environment.environment_version,
            "scenario_id": run.scenario.scenario_id,
            "scenario_name": run.scenario.scenario_name,
            "scenario_seed": run.scenario.scenario_seed,
            "task_id": run.task.task_id,
            "task_kind": run.task.task_kind,
            "task_title": run.task.task_title,
            "status": run.status,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "current_step_index": run.current_step_index,
            "active_agent_id": run.active_agent_id,
            "grade_result": self._json_document(
                run.grade_result.model_dump(mode="json") if run.grade_result is not None else None
            ),
        }

    def _run_event_insert_params(self, event: RunEvent) -> dict[str, object]:
        return {
            "event_id": event.event_id,
            "run_id": event.run_id,
            "sequence": event.sequence,
            "occurred_at": event.occurred_at,
            "source": event.source,
            "actor_type": event.actor_type,
            "correlation_id": event.correlation_id,
            "event_type": event.event_type,
            "payload": self._json_document(serialize_run_event_payload(event)),
        }

    def _artifact_insert_params(
        self,
        *,
        artifact: Artifact,
    ) -> dict[str, object]:
        artifact_document = serialize_artifact(artifact)
        return {
            "artifact_id": artifact.artifact_id,
            "run_id": artifact.run_id,
            "step_id": artifact.step_id,
            "kind": artifact.kind,
            "uri": artifact.uri,
            "content_type": artifact.content_type,
            "created_at": artifact.created_at,
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
            "metadata": self._json_document(artifact_document["metadata"]),
        }

    def _row_to_run(self, row: dict[str, object]) -> Run:
        payload: dict[str, Any] = {
            "run_id": row["run_id"],
            "environment": {
                "environment_id": row["environment_id"],
                "environment_name": row["environment_name"],
                "environment_version": row["environment_version"],
            },
            "scenario": {
                "scenario_id": row["scenario_id"],
                "environment_id": row["environment_id"],
                "scenario_name": row["scenario_name"],
                "scenario_seed": row["scenario_seed"],
            },
            "task": {
                "task_id": row["task_id"],
                "scenario_id": row["scenario_id"],
                "task_kind": row["task_kind"],
                "task_title": row["task_title"],
            },
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "current_step_index": row["current_step_index"],
            "active_agent_id": row["active_agent_id"],
            "grade_result": row["grade_result"],
        }
        return Run.model_validate(payload)

    def _row_to_run_event(self, row: dict[str, object]) -> RunEvent:
        return deserialize_run_event(
            {
                "schema_version": 1,
                "event_id": row["event_id"],
                "run_id": row["run_id"],
                "sequence": row["sequence"],
                "occurred_at": row["occurred_at"],
                "source": row["source"],
                "actor_type": row["actor_type"],
                "correlation_id": row["correlation_id"],
                "event_type": row["event_type"],
                "payload": row["payload"],
            }
        )

    def _row_to_artifact(self, row: dict[str, object]) -> Artifact:
        return deserialize_artifact(
            {
                "schema_version": 1,
                "artifact_id": row["artifact_id"],
                "run_id": row["run_id"],
                "step_id": row["step_id"],
                "kind": row["kind"],
                "uri": row["uri"],
                "content_type": row["content_type"],
                "created_at": row["created_at"],
                "sha256": row["sha256"],
                "size_bytes": row["size_bytes"],
                "metadata": row["metadata"],
            }
        )

    def _json_document(self, value: Any) -> str:
        if value is None:
            return "null"
        from json import dumps

        return dumps(value)


class RunService:
    def __init__(self, repository: RunRepository) -> None:
        self._repository = repository

    def create_run(self, run: Run) -> Run:
        return self._repository.create_run(run)

    def get_run(self, run_id: str) -> Run:
        run = self._repository.get_run(run_id)
        if run is None:
            raise RunNotFoundError(f"run {run_id} does not exist")
        return run

    def list_runs(self, *, limit: int = 100) -> list[Run]:
        return self._repository.list_runs(limit=limit)

    def list_run_events(self, run_id: str) -> list[RunEvent]:
        self.get_run(run_id)
        return self._repository.list_run_events(run_id)

    def list_run_artifacts(self, run_id: str) -> list[Artifact]:
        self.get_run(run_id)
        return self._repository.list_run_artifacts(run_id)

    def next_event_sequence(self, run_id: str) -> int:
        self.get_run(run_id)
        return self._repository.next_event_sequence(run_id)

    def append_run_event(self, event: RunEvent) -> RunEvent:
        run = self.get_run(event.run_id)
        expected_sequence = self._repository.next_event_sequence(event.run_id)
        if event.sequence != expected_sequence:
            raise EventSequenceConflictError(
                f"run {event.run_id} expected next event sequence {expected_sequence}, got {event.sequence}"
            )

        try:
            transition = validate_event_transition(run.status, event)
        except InvalidRunEventTransitionError:
            raise

        current_step_index = None
        started_at = None
        completed_at = None
        grade_result = None

        if event.event_type == RunEventType.RUN_STARTED:
            started_at = event.occurred_at
        elif event.event_type == RunEventType.RUN_STEP_CREATED:
            step_payload = cast(RunStepCreatedPayload, event.payload)
            current_step_index = step_payload.step.step_index
        elif event.event_type == RunEventType.RUN_COMPLETED:
            completed_payload = cast(RunCompletedPayload, event.payload)
            completed_at = completed_payload.completed_at
            grade_result = completed_payload.grade_result

        with self._repository.transaction():
            if transition is not None or current_step_index is not None:
                self._repository.update_run_progress(
                    event.run_id,
                    status=transition.to_status if transition is not None else None,
                    updated_at=event.occurred_at,
                    started_at=started_at,
                    completed_at=completed_at,
                    current_step_index=current_step_index,
                    grade_result=grade_result,
                )
            appended = self._repository.append_run_event(event)
        return appended

    def attach_artifact(
        self,
        *,
        run_id: str,
        artifact: Artifact,
        step_id: str | None = None,
    ) -> Artifact:
        self.get_run(run_id)
        return self._repository.attach_artifact(run_id=run_id, artifact=artifact, step_id=step_id)

    def finalize_run(self, run_id: str, finalization: RunFinalization) -> Run:
        run = self.get_run(run_id)
        try:
            validate_run_transition(run.status, finalization.final_status)
        except InvalidRunTransitionError as exc:
            raise InvalidRunFinalizationError(str(exc)) from exc
        with self._repository.transaction():
            return self._repository.finalize_run(run_id, finalization)
