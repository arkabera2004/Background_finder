-- Phase 0: core schema. owner_id ties every row to auth.users for RLS.

create table if not exists companies (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    domain text,
    name text,
    data jsonb not null default '{}',
    crawled_at timestamptz,
    created_at timestamptz not null default now()
);

create table if not exists prospects (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    company_id uuid references companies(id) on delete set null,
    full_name text not null,
    linkedin_url text,
    tags text[] not null default '{}',
    status text not null default 'new',
    created_at timestamptz not null default now()
);

create table if not exists research_runs (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    prospect_id uuid references prospects(id) on delete cascade,
    depth text not null default 'standard',
    status text not null default 'pending',
    created_at timestamptz not null default now(),
    completed_at timestamptz
);

create table if not exists run_steps (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references research_runs(id) on delete cascade,
    stage text not null,
    status text not null default 'pending',
    output jsonb,
    error text,
    started_at timestamptz,
    completed_at timestamptz
);

create table if not exists sources (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references research_runs(id) on delete cascade,
    url text not null,
    excerpt text,
    content_hash text,
    fetched_at timestamptz not null default now()
);

create table if not exists briefs (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    prospect_id uuid not null references prospects(id) on delete cascade,
    run_id uuid references research_runs(id) on delete set null,
    version int not null default 1,
    data jsonb not null,
    created_at timestamptz not null default now()
);

create table if not exists products (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    one_liner text,
    ideal_customer text,
    pain_points text[] not null default '{}',
    proof_points text[] not null default '{}',
    links text[] not null default '{}',
    created_at timestamptz not null default now()
);

alter table companies enable row level security;
alter table prospects enable row level security;
alter table research_runs enable row level security;
alter table run_steps enable row level security;
alter table sources enable row level security;
alter table briefs enable row level security;
alter table products enable row level security;

create policy owner_select on companies for select using (owner_id = auth.uid());
create policy owner_all on companies for all using (owner_id = auth.uid());

create policy owner_select on prospects for select using (owner_id = auth.uid());
create policy owner_all on prospects for all using (owner_id = auth.uid());

create policy owner_select on research_runs for select using (owner_id = auth.uid());
create policy owner_all on research_runs for all using (owner_id = auth.uid());

create policy owner_select on run_steps for select using (
    exists (select 1 from research_runs r where r.id = run_steps.run_id and r.owner_id = auth.uid())
);
create policy owner_all on run_steps for all using (
    exists (select 1 from research_runs r where r.id = run_steps.run_id and r.owner_id = auth.uid())
);

create policy owner_select on sources for select using (
    exists (select 1 from research_runs r where r.id = sources.run_id and r.owner_id = auth.uid())
);
create policy owner_all on sources for all using (
    exists (select 1 from research_runs r where r.id = sources.run_id and r.owner_id = auth.uid())
);

create policy owner_select on briefs for select using (owner_id = auth.uid());
create policy owner_all on briefs for all using (owner_id = auth.uid());

create policy owner_select on products for select using (owner_id = auth.uid());
create policy owner_all on products for all using (owner_id = auth.uid());
