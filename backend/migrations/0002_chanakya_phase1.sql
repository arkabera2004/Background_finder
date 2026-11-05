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

create table if not exists chanakya_scouted_companies (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    run_id uuid not null references chanakya_runs(id) on delete cascade,
    name text not null,
    domain text not null,
    fit_score double precision not null default 0,
    selected boolean not null default false,
    source_url text not null,
    data jsonb not null default '{}',
    created_at timestamptz not null default now(),
    unique (run_id, domain)
);

create table if not exists chanakya_people (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    run_id uuid not null references chanakya_runs(id) on delete cascade,
    company_id uuid not null references chanakya_scouted_companies(id) on delete cascade,
    full_name text not null,
    role text not null,
    linkedin_url text,
    confidence double precision not null default 0,
    identity_confirmed boolean not null default false,
    resolution_status text not null default 'pending',
    candidate_profiles jsonb not null default '[]',
    created_at timestamptz not null default now(),
    unique (run_id, company_id, full_name)
);

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

create table if not exists chanakya_email_candidates (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    run_id uuid not null references chanakya_runs(id) on delete cascade,
    person_id uuid not null references chanakya_people(id) on delete cascade,
    email text not null,
    pattern text not null,
    verification_status text not null default 'needs_review',
    confidence double precision not null default 0,
    created_at timestamptz not null default now(),
    unique (run_id, person_id, email)
);

create table if not exists chanakya_research_briefs (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    run_id uuid not null references chanakya_runs(id) on delete cascade,
    person_id uuid not null references chanakya_people(id) on delete cascade,
    status text not null,
    data jsonb not null default '{}',
    created_at timestamptz not null default now(),
    unique (run_id, person_id)
);

create table if not exists chanakya_qa_records (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    run_id uuid not null references chanakya_runs(id) on delete cascade,
    person_id uuid not null references chanakya_people(id) on delete cascade,
    confidence_score double precision not null default 0,
    confidence_level text not null,
    needs_review boolean not null default true,
    draft_subject text not null,
    draft_body text not null,
    approval_status text not null default 'pending_review',
    created_at timestamptz not null default now(),
    unique (run_id, person_id)
);

alter table chanakya_scouted_companies enable row level security;
alter table chanakya_people enable row level security;

create policy owner_select on chanakya_scouted_companies for select using (owner_id = auth.uid());
create policy owner_all on chanakya_scouted_companies for all using (owner_id = auth.uid());

create policy owner_select on chanakya_people for select using (owner_id = auth.uid());
create policy owner_all on chanakya_people for all using (owner_id = auth.uid());

alter table chanakya_email_candidates enable row level security;
create policy owner_select on chanakya_email_candidates for select using (owner_id = auth.uid());
create policy owner_all on chanakya_email_candidates for all using (owner_id = auth.uid());

alter table chanakya_research_briefs enable row level security;
create policy owner_select on chanakya_research_briefs for select using (owner_id = auth.uid());
create policy owner_all on chanakya_research_briefs for all using (owner_id = auth.uid());

alter table chanakya_qa_records enable row level security;
create policy owner_select on chanakya_qa_records for select using (owner_id = auth.uid());
create policy owner_all on chanakya_qa_records for all using (owner_id = auth.uid());
