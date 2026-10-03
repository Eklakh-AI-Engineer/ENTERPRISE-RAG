-- Add defense-in-depth tenant integrity without weakening the existing RLS policies.

create policy "ingestion jobs must match document tenant"
on public.ingestion_jobs
as restrictive
for insert
to authenticated
with check (
  exists (
    select 1
    from public.documents d
    where d.id = ingestion_jobs.document_id
      and d.organization_id = ingestion_jobs.organization_id
  )
);

create policy "storage objects must match document row"
on storage.objects
as restrictive
for all
to authenticated
using (
  bucket_id = 'documents'
  and split_part(name, '/', 1) = 'organizations'
  and split_part(name, '/', 3) = 'documents'
  and exists (
    select 1
    from public.documents d
    where d.organization_id = split_part(objects.name, '/', 2)::uuid
      and d.id = split_part(objects.name, '/', 4)::uuid
      and d.storage_path = objects.name
  )
)
with check (
  bucket_id = 'documents'
  and split_part(name, '/', 1) = 'organizations'
  and split_part(name, '/', 3) = 'documents'
  and exists (
    select 1
    from public.documents d
    where d.organization_id = split_part(name, '/', 2)::uuid
      and d.id = split_part(name, '/', 4)::uuid
      and d.storage_path = name
  )
);
