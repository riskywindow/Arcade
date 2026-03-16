from __future__ import annotations

import argparse

from atlas_worker.dummy_execution import DummyRunSpec, execute_dummy_run_from_config
from atlas_worker.config import load_config
from atlas_core.logging import configure_logging, log_event


def boot() -> dict[str, str | int]:
    config = load_config()
    service = config.service
    logger = configure_logging(service.service_name, service.log_level)
    log_event(
        logger,
        "worker_starting",
        host=service.host,
        port=service.port,
        environment=service.environment,
        postgres_dsn=config.infrastructure.postgres_dsn(),
        redis_url=config.infrastructure.redis_url(),
        minio_endpoint=config.infrastructure.minio_endpoint,
    )
    state: dict[str, str | int] = {
        "status": "ok",
        "service": service.service_name,
        "environment": service.environment,
        "port": service.port,
    }
    log_event(logger, "worker_ready", **state)
    log_event(logger, "worker_stopping", service=service.service_name)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description="Atlas worker entrypoint")
    parser.add_argument(
        "command",
        nargs="?",
        default="boot",
        choices=("boot", "dummy-run"),
        help="worker action to run",
    )
    parser.add_argument("--run-id", default="dummy-run-001", help="run id for the dummy execution")
    parser.add_argument(
        "--schema-name",
        default=None,
        help="optional Postgres schema name used for local or test execution",
    )
    args = parser.parse_args()

    if args.command == "boot":
        boot()
        return

    config = load_config()
    result = execute_dummy_run_from_config(
        config,
        DummyRunSpec(run_id=args.run_id),
        schema_name=args.schema_name,
    )
    print(
        {
            "run_id": result.run_id,
            "final_status": result.final_status.value,
            "event_count": result.event_count,
            "artifact_count": result.artifact_count,
        }
    )
