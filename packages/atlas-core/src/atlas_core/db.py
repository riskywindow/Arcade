from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from atlas_core.config import InfrastructureConfig

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MIGRATIONS_DIR = REPO_ROOT / "infra" / "migrations"


@dataclass(frozen=True)
class MigrationFile:
    version: str
    name: str
    up_path: Path
    down_path: Path


def discover_migrations(migrations_dir: Path) -> list[MigrationFile]:
    grouped: dict[str, dict[str, Path]] = {}
    for path in sorted(migrations_dir.glob("*.sql")):
        if path.name.endswith(".up.sql"):
            key = path.name[: -len(".up.sql")]
            grouped.setdefault(key, {})["up"] = path
        elif path.name.endswith(".down.sql"):
            key = path.name[: -len(".down.sql")]
            grouped.setdefault(key, {})["down"] = path

    migrations: list[MigrationFile] = []
    for key, parts in sorted(grouped.items()):
        if "up" not in parts or "down" not in parts:
            raise ValueError(f"migration {key} must include both .up.sql and .down.sql files")
        version, _, name = key.partition("_")
        migrations.append(
            MigrationFile(
                version=version,
                name=name or key,
                up_path=parts["up"],
                down_path=parts["down"],
            )
        )
    return migrations


def open_connection(
    dsn: str,
    *,
    autocommit: bool = False,
) -> Connection[dict[str, object]]:
    return psycopg.connect(dsn, row_factory=dict_row, autocommit=autocommit)


def ensure_migration_table(conn: Connection[dict[str, object]]) -> None:
    conn.execute(
        """
        create table if not exists schema_migrations (
            version text primary key,
            name text not null,
            applied_at timestamptz not null default now()
        )
        """
    )


def applied_versions(conn: Connection[dict[str, object]]) -> list[str]:
    ensure_migration_table(conn)
    rows = conn.execute(
        """
        select version
        from schema_migrations
        order by version asc
        """
    ).fetchall()
    return [str(row["version"]) for row in rows]


def apply_migrations(
    conn: Connection[dict[str, object]],
    migrations: Iterable[MigrationFile],
) -> list[str]:
    ensure_migration_table(conn)
    already_applied = set(applied_versions(conn))
    applied_now: list[str] = []

    for migration in migrations:
        if migration.version in already_applied:
            continue
        sql = migration.up_path.read_text()
        with conn.transaction():
            conn.execute(sql)
            conn.execute(
                """
                insert into schema_migrations (version, name)
                values (%s, %s)
                """,
                (migration.version, migration.name),
            )
        applied_now.append(migration.version)
    return applied_now


def rollback_migrations(
    conn: Connection[dict[str, object]],
    migrations: Iterable[MigrationFile],
    *,
    steps: int,
) -> list[str]:
    if steps < 1:
        raise ValueError("steps must be at least 1")

    migration_map = {migration.version: migration for migration in migrations}
    applied = applied_versions(conn)
    to_rollback = applied[-steps:]
    rolled_back: list[str] = []

    for version in reversed(to_rollback):
        migration = migration_map.get(version)
        if migration is None:
            raise ValueError(f"no migration file found for applied version {version}")
        sql = migration.down_path.read_text()
        with conn.transaction():
            conn.execute(sql)
            conn.execute(
                """
                delete from schema_migrations
                where version = %s
                """,
                (version,),
            )
        rolled_back.append(version)
    return rolled_back


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atlas database migration runner")
    parser.add_argument(
        "command",
        choices=("up", "down", "status"),
        help="migration action to run",
    )
    parser.add_argument(
        "--dsn",
        default=InfrastructureConfig.from_env().postgres_dsn(),
        help="Postgres DSN. Defaults to ATLAS_* environment variables.",
    )
    parser.add_argument(
        "--migrations-dir",
        default=str(DEFAULT_MIGRATIONS_DIR),
        help="Directory containing .up.sql and .down.sql migration files.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1,
        help="Number of migrations to roll back when using the down command.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    migrations_dir = Path(args.migrations_dir).resolve()
    migrations = discover_migrations(migrations_dir)

    with open_connection(args.dsn, autocommit=True) as conn:
        if args.command == "up":
            applied = apply_migrations(conn, migrations)
            print(f"applied migrations: {applied or 'none'}")
            return

        if args.command == "down":
            rolled_back = rollback_migrations(conn, migrations, steps=args.steps)
            print(f"rolled back migrations: {rolled_back or 'none'}")
            return

        print(f"applied migrations: {applied_versions(conn)}")
