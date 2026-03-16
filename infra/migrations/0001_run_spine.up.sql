create table if not exists runs (
    run_id text primary key,
    environment_id text not null,
    environment_name text not null,
    environment_version text,
    scenario_id text not null,
    scenario_name text not null,
    scenario_seed text not null,
    task_id text not null,
    task_kind text not null,
    task_title text not null,
    status text not null check (
        status in (
            'pending',
            'ready',
            'running',
            'waiting_approval',
            'succeeded',
            'failed',
            'cancelled'
        )
    ),
    created_at timestamptz not null,
    updated_at timestamptz not null,
    started_at timestamptz,
    completed_at timestamptz,
    current_step_index integer not null default 0 check (current_step_index >= 0),
    active_agent_id text,
    grade_result jsonb
);

create table if not exists run_events (
    event_id text primary key,
    run_id text not null references runs(run_id) on delete cascade,
    sequence integer not null check (sequence >= 0),
    occurred_at timestamptz not null,
    source text not null check (
        source in (
            'api',
            'worker',
            'agent',
            'bastion',
            'operator',
            'grader',
            'system'
        )
    ),
    actor_type text not null check (
        actor_type in (
            'system',
            'worker',
            'agent',
            'bastion',
            'operator',
            'grader'
        )
    ),
    correlation_id text,
    event_type text not null,
    payload jsonb not null,
    unique (run_id, sequence)
);

create index if not exists idx_run_events_run_sequence
    on run_events (run_id, sequence asc);

create table if not exists run_artifacts (
    artifact_id text primary key,
    run_id text not null references runs(run_id) on delete cascade,
    step_id text,
    kind text not null check (
        kind in (
            'log',
            'screenshot',
            'trace',
            'diff',
            'report',
            'note'
        )
    ),
    uri text not null,
    content_type text not null,
    created_at timestamptz not null,
    sha256 text,
    size_bytes bigint check (size_bytes is null or size_bytes >= 0),
    metadata jsonb not null default '{}'::jsonb
);

create index if not exists idx_run_artifacts_run_created
    on run_artifacts (run_id, created_at asc);
