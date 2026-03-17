from __future__ import annotations

import argparse

from atlas_worker.dummy_execution import DummyRunSpec, execute_dummy_run_from_config
from atlas_worker.agent_execution import (
    SeededAgentRunSpec,
    execute_policy_protected_demo_run_from_config,
    execute_seeded_agent_run_from_config,
)
from atlas_worker.scripted_smoke import execute_scripted_smoke_from_config
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
        choices=("boot", "dummy-run", "scripted-smoke", "agent-demo", "policy-demo"),
        help="worker action to run",
    )
    parser.add_argument("--run-id", default="dummy-run-001", help="run id for the dummy execution")
    parser.add_argument(
        "--schema-name",
        default=None,
        help="optional Postgres schema name used for local or test execution",
    )
    parser.add_argument(
        "--run-prefix",
        default="phase3-smoke",
        help="run id prefix for the scripted smoke flow",
    )
    parser.add_argument(
        "--scenario-id",
        default="mfa-reenrollment-device-loss",
        help="scenario id for the seeded agent demo path",
    )
    parser.add_argument(
        "--seed",
        default="seed-phase3-demo",
        help="scenario seed for the seeded agent demo path",
    )
    parser.add_argument(
        "--browser-mode",
        default="stub",
        choices=("stub", "live"),
        help="browser mode for the seeded agent demo path",
    )
    parser.add_argument(
        "--approval-timeout-seconds",
        type=int,
        default=180,
        help="how long the policy demo waits for an approval decision before failing",
    )
    parser.add_argument(
        "--approval-poll-interval-seconds",
        type=float,
        default=1.0,
        help="how often the policy demo polls for approval resolution",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="auto-approve the policy-gated action for deterministic smoke validation",
    )
    args = parser.parse_args()

    if args.command == "boot":
        boot()
        return

    config = load_config()
    if args.command == "dummy-run":
        dummy_result = execute_dummy_run_from_config(
            config,
            DummyRunSpec(run_id=args.run_id),
            schema_name=args.schema_name,
        )
        print(
            {
                "run_id": dummy_result.run_id,
                "final_status": dummy_result.final_status.value,
                "event_count": dummy_result.event_count,
                "artifact_count": dummy_result.artifact_count,
            }
        )
        return

    if args.command == "agent-demo":
        agent_result = execute_seeded_agent_run_from_config(
            config,
            spec=SeededAgentRunSpec(
                run_id=args.run_id,
                scenario_id=args.scenario_id,
                seed=args.seed,
                browser_mode=args.browser_mode,
            ),
            schema_name=args.schema_name,
        )
        print(
            {
                "run_id": agent_result.run_id,
                "scenario_id": agent_result.scenario_id,
                "final_status": agent_result.final_status.value,
                "termination_reason": agent_result.termination_reason.value,
                "event_count": agent_result.event_count,
                "artifact_count": agent_result.artifact_count,
                "browser_mode": args.browser_mode,
            }
        )
        return

    if args.command == "policy-demo":
        demo_result = execute_policy_protected_demo_run_from_config(
            config,
            spec=SeededAgentRunSpec(
                run_id=args.run_id,
                scenario_id="travel-lockout-recovery",
                seed=args.seed,
                browser_mode=args.browser_mode,
            ),
            schema_name=args.schema_name,
            approval_timeout_seconds=args.approval_timeout_seconds,
            approval_poll_interval_seconds=args.approval_poll_interval_seconds,
            auto_approve=args.auto_approve,
        )
        print(
            {
                "run_id": demo_result.run_id,
                "scenario_id": demo_result.scenario_id,
                "final_status": demo_result.final_status.value,
                "termination_reason": demo_result.termination_reason.value,
                "approval_request_id": demo_result.approval_request_id,
                "event_count": demo_result.event_count,
                "artifact_count": demo_result.artifact_count,
                "browser_mode": args.browser_mode,
            }
        )
        return

    scripted_result = execute_scripted_smoke_from_config(
        config,
        schema_name=args.schema_name,
        run_prefix=args.run_prefix,
    )
    print(
        {
            "run_count": len(scripted_result.outcomes),
            "outcomes": [
                {
                    "run_id": outcome.run_id,
                    "scenario_id": outcome.scenario_id,
                    "final_status": outcome.final_status.value,
                    "grade_outcome": outcome.grade_result.outcome.value,
                    "event_count": outcome.event_count,
                    "artifact_count": outcome.artifact_count,
                }
                for outcome in scripted_result.outcomes
            ],
        }
    )
