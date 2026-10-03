-- Allow the authenticated API to create and clean up tenant-scoped ingestion jobs.
-- Worker lifecycle updates remain trusted service-role operations.

create policy "members can create ingestion jobs"
on public.ingestion_jobs
for insert
to authenticated
with check (
  exists (
    select 1
    from public.organization_members om
    where om.organization_id = ingestion_jobs.organization_id
      and om.user_id = (select auth.uid())
  )
);

create policy "members can delete ingestion jobs"
on public.ingestion_jobs
for delete
to authenticated
using (
  exists (
    select 1
    from public.organization_members om
    where om.organization_id = ingestion_jobs.organization_id
      and om.user_id = (select auth.uid())
  )
);
