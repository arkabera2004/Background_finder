-- Chanakya Phase 1: monthly-run lifecycle and agent provenance foundation.
-- Additive to 0001_init.sql's single-prospect schema — see docs/CHANAKYA_GAP_ANALYSIS.md.

create table if not exists chanakya_runs (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    period text not null,
    status text not null default 'pending',
    config jsonb not null default '{}',
    created_at timestamptz not null default now(),
    completed_at timestamptz
);
create index if not exists ix_chanakya_runs_owner_period on chanakya_runs (owner_id, period);

create table if not exists chanakya_offering_snapshots (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    run_id uuid not null references chanakya_runs(id) on delete cascade,
    version int not null default 1,
    data jsonb not null,
    created_at timestamptz not null default now()
);
create index if not exists ix_offering_snapshots_run_version on chanakya_offering_snapshots (run_id, version);

create table if not exists chanakya_agent_executions (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references chanakya_runs(id) on delete cascade,
    agent_name text not null,
    status text not null default 'pending',
    retry_count int not null default 0,
    error text,
    output_summary jsonb not null default '{}',
    started_at timestamptz,
    completed_at timestamptz,
    unique (run_id, agent_name)
);

create table if not exists chanakya_evidence (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references chanakya_runs(id) on delete cascade,
    agent_name text not null,
    entity_type text not null,
    entity_id text not null,
    source_url text not null,
    excerpt text,
    confidence double precision not null default 0,
    fetched_at timestamptz not null default now()
);
create index if not exists ix_evidence_entity on chanakya_evidence (entity_type, entity_id);

alter table chanakya_runs enable row level security;
alter table chanakya_offering_snapshots enable row level security;
alter table chanakya_agent_executions enable row level security;
alter table chanakya_evidence enable row level security;

create policy owner_select on chanakya_runs for select using (owner_id = auth.uid());
create policy owner_all on chanakya_runs for all using (owner_id = auth.uid());

create policy owner_select on chanakya_offering_snapshots for select using (owner_id = auth.uid());
create policy owner_all on chanakya_offering_snapshots for all using (owner_id = auth.uid());

create policy owner_select on chanakya_agent_executions for select using (
    exists (select 1 from chanakya_runs r where r.id = chanakya_agent_executions.run_id and r.owner_id = auth.uid())
);
create policy owner_all on chanakya_agent_executions for all using (
    exists (select 1 from chanakya_runs r where r.id = chanakya_agent_executions.run_id and r.owner_id = auth.uid())
);

create policy owner_select on chanakya_evidence for select using (
    exists (select 1 from chanakya_runs r where r.id = chanakya_evidence.run_id and r.owner_id = auth.uid())
);
create policy owner_all on chanakya_evidence for all using (
    exists (select 1 from chanakya_runs r where r.id = chanakya_evidence.run_id and r.owner_id = auth.uid())
);
