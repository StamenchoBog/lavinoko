-- OPTION, NOT IN USE: candidate design if Supabase is chosen for hosting reports. See docs/architecture/README.md.
-- LavinOko field reports — run once in the Supabase SQL editor (Project → SQL editor → New query).
-- Model: invited observers only. Public sign-up must be OFF (Authentication → Sign In / Providers →
-- "Allow new users to sign up" = off); invite people from Authentication → Users → Invite user,
-- then add a row for them in public.observers.

-- Who may report, and how they are shown publicly (role and organisation, never the e-mail).
create table if not exists public.observers (
  user_id      uuid primary key references auth.users (id) on delete cascade,
  display_role text not null check (display_role in ('guide', 'patrol', 'rescue', 'forecaster', 'observer')),
  organisation text,
  active       boolean not null default true,
  created_at   timestamptz not null default now()
);

create table if not exists public.reports (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  observed_at   timestamptz not null,
  observer_id   uuid not null default auth.uid() references public.observers (user_id),
  place_id      text,
  lat           double precision not null check (lat between 40.5 and 42.7),
  lon           double precision not null check (lon between 20.0 and 23.4),
  elevation_m   integer check (elevation_m between 0 and 3000),
  aspect        text check (aspect in ('N','NE','E','SE','S','SW','W','NW')),
  kinds         text[] not null check (
                  cardinality(kinds) between 1 and 7 and
                  kinds <@ array['avalanche','cracking','whumpf','drifting','new_snow','wet_snow','other']),
  avalanche_size smallint check (avalanche_size between 1 and 5),
  new_snow_cm   smallint check (new_snow_cm between 0 and 300),
  note          text check (char_length(note) <= 1000),
  photo_path    text,
  hidden        boolean not null default false   -- set true to take a report down
);
create index if not exists reports_observed_at on public.reports (observed_at desc);

-- What the website reads: no user ids, only the public role/organisation.
create or replace view public.reports_public with (security_invoker = false) as
  select r.id, r.created_at, r.observed_at, r.place_id, r.lat, r.lon, r.elevation_m, r.aspect,
         r.kinds, r.avalanche_size, r.new_snow_cm, r.note, r.photo_path,
         o.display_role, o.organisation
  from public.reports r join public.observers o on o.user_id = r.observer_id
  where not r.hidden and r.observed_at > now() - interval '30 days';

alter table public.observers enable row level security;
alter table public.reports   enable row level security;

-- Observers can see their own observer row (the site uses it to show the report button).
drop policy if exists "observer reads own row" on public.observers;
create policy "observer reads own row" on public.observers
  for select to authenticated using (user_id = auth.uid());

-- Only active observers can add reports, and only as themselves.
drop policy if exists "active observers insert" on public.reports;
create policy "active observers insert" on public.reports
  for insert to authenticated
  with check (observer_id = auth.uid()
              and exists (select 1 from public.observers o where o.user_id = auth.uid() and o.active));

-- Observers can correct or remove their own reports.
drop policy if exists "observers update own" on public.reports;
create policy "observers update own" on public.reports
  for update to authenticated using (observer_id = auth.uid()) with check (observer_id = auth.uid());

-- Public read goes only through the view.
revoke all on public.reports from anon;
grant select on public.reports_public to anon, authenticated;

-- Photos: public to read, only active observers can upload, into a folder named after themselves.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
  values ('report-photos', 'report-photos', true, 3145728, array['image/jpeg'])
  on conflict (id) do nothing;

drop policy if exists "observers upload photos" on storage.objects;
create policy "observers upload photos" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'report-photos'
              and (storage.foldername(name))[1] = auth.uid()::text
              and exists (select 1 from public.observers o where o.user_id = auth.uid() and o.active));
