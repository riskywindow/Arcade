from __future__ import annotations

import uvicorn

from atlas_api.app import create_app
from atlas_api.config import load_config
from atlas_core.logging import configure_logging, log_event


def app():
    return create_app()


def main() -> None:
    config = load_config()
    service = config.service
    logger = configure_logging(service.service_name, service.log_level)
    log_event(
        logger,
        "service_starting",
        host=service.host,
        port=service.port,
        environment=service.environment,
        postgres_dsn=config.infrastructure.postgres_dsn(),
        redis_url=config.infrastructure.redis_url(),
        minio_endpoint=config.infrastructure.minio_endpoint,
    )
    uvicorn.run(
        "atlas_api.main:app",
        factory=True,
        host=service.host,
        port=service.port,
        reload=service.reload,
    )


if __name__ == "__main__":
    main()
