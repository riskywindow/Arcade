from __future__ import annotations

from dataclasses import dataclass
import os


def _env_name(prefix: str, field_name: str) -> str:
    return f"{prefix}_{field_name}".upper()


def _read_str(prefix: str, field_name: str, default: str) -> str:
    return os.getenv(_env_name(prefix, field_name), default)


def _read_int(prefix: str, field_name: str, default: int) -> int:
    value = os.getenv(_env_name(prefix, field_name))
    if value is None:
        return default
    return int(value)


def _read_bool(prefix: str, field_name: str, default: bool) -> bool:
    value = os.getenv(_env_name(prefix, field_name))
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ServiceConfig:
    service_name: str
    environment: str
    host: str
    port: int
    log_level: str
    reload: bool

    @classmethod
    def from_env(
        cls,
        *,
        prefix: str,
        service_name: str,
        default_port: int,
    ) -> "ServiceConfig":
        return cls(
            service_name=service_name,
            environment=_read_str(prefix, "environment", "local"),
            host=_read_str(prefix, "host", "127.0.0.1"),
            port=_read_int(prefix, "port", default_port),
            log_level=_read_str(prefix, "log_level", "INFO"),
            reload=_read_bool(prefix, "reload", False),
        )

    def health_payload(self) -> dict[str, str]:
        return {
            "status": "ok",
            "service": self.service_name,
            "environment": self.environment,
        }


@dataclass(frozen=True)
class InfrastructureConfig:
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    redis_host: str
    redis_port: int
    minio_endpoint: str
    minio_console_url: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str

    @classmethod
    def from_env(cls) -> "InfrastructureConfig":
        return cls(
            postgres_host=_read_str("atlas", "postgres_host", "127.0.0.1"),
            postgres_port=_read_int("atlas", "postgres_port", 5432),
            postgres_db=_read_str("atlas", "postgres_db", "atlas_bastion"),
            postgres_user=_read_str("atlas", "postgres_user", "atlas"),
            postgres_password=_read_str("atlas", "postgres_password", "atlas"),
            redis_host=_read_str("atlas", "redis_host", "127.0.0.1"),
            redis_port=_read_int("atlas", "redis_port", 6379),
            minio_endpoint=_read_str("atlas", "minio_endpoint", "http://127.0.0.1:9000"),
            minio_console_url=_read_str("atlas", "minio_console_url", "http://127.0.0.1:9001"),
            minio_access_key=_read_str("atlas", "minio_access_key", "atlas"),
            minio_secret_key=_read_str("atlas", "minio_secret_key", "atlasminio"),
            minio_bucket=_read_str("atlas", "minio_bucket", "atlas-artifacts"),
        )

    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"
