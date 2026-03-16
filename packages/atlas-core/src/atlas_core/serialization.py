from __future__ import annotations

from typing import Any

from atlas_core.domain import Artifact, RunEvent


def serialize_run_event(event: RunEvent) -> dict[str, Any]:
    return event.model_dump(mode="json")


def deserialize_run_event(document: dict[str, Any]) -> RunEvent:
    return RunEvent.model_validate(document)


def serialize_run_event_payload(event: RunEvent) -> dict[str, Any]:
    return event.payload.model_dump(mode="json")


def serialize_artifact(artifact: Artifact) -> dict[str, Any]:
    return artifact.model_dump(mode="json")


def deserialize_artifact(document: dict[str, Any]) -> Artifact:
    return Artifact.model_validate(document)
