-- Chanakya Phase 5: durable monthly scheduler + two gaps found while
-- adding it: chanakya_runs never had RLS enabled (every other Chanakya
-- table does), and (owner_id, period) was indexed but not unique,
-- allowing duplicate monthly runs at the database layer even though the
-- app now rejects a duplicate with 409. Belt and suspenders.

create table if not exists chanakya_schedules (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references auth.users(id) on delete cascade,
    enabled boolean not null default true,
    day_of_month int not null default 1,
    offerings jsonb not null,
    filters jsonb not null default '{}',
    config jsonb not null default '{}',
    last_run_period text,
    last_run_id uuid,
    last_run_status text,
    last_run_error text,
    created_at timestamptz not null default now()
);
create index if not exists ix_chanakya_schedules_owner on chanakya_schedules (owner_id);

alter table chanakya_schedules enable row level security;
create policy owner_select on chanakya_schedules for select using (owner_id = auth.uid());
create policy owner_all on chanakya_schedules for all using (owner_id = auth.uid());

alter table chanakya_runs enable row level security;
create policy owner_select on chanakya_runs for select using (owner_id = auth.uid());
create policy owner_all on chanakya_runs for all using (owner_id = auth.uid());

alter table chanakya_runs add constraint uq_chanakya_runs_owner_period unique (owner_id, period);
