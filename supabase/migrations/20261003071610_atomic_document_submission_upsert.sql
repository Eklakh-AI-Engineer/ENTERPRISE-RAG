-- Make concurrent identical submissions converge on one document/job identity.

create or replace function public.submit_document_with_job(
  p_organization_id uuid,
  p_filename text,
  p_storage_path text,
  p_content_hash text,
  p_pipeline_version text
)
returns table(document_id uuid, ingestion_job_id uuid, deduplicated boolean, document_status text)
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_document public.documents;
  v_job public.ingestion_jobs;
begin
  if auth.uid() is null then
    raise exception 'authenticated user required';
  end if;

  if not exists (
    select 1
    from public.organization_members om
    where om.organization_id = p_organization_id
      and om.user_id = (select auth.uid())
  ) then
    raise exception 'organization membership required';
  end if;

  insert into public.documents (
    organization_id, owner_user_id, filename, storage_path,
    content_hash, pipeline_version
  )
  values (
    p_organization_id, (select auth.uid()), p_filename, p_storage_path,
    p_content_hash, p_pipeline_version
  )
  on conflict (organization_id, content_hash, pipeline_version)
  do nothing
  returning * into v_document;

  if v_document.id is null then
    select d.*
      into v_document
    from public.documents d
    where d.organization_id = p_organization_id
      and d.content_hash = p_content_hash
      and d.pipeline_version = p_pipeline_version
    limit 1;
  end if;

  select j.*
    into v_job
  from public.ingestion_jobs j
  where j.organization_id = p_organization_id
    and j.document_id = v_document.id
    and j.content_hash = p_content_hash
    and j.pipeline_version = p_pipeline_version
  order by j.created_at desc
  limit 1;

  if v_job.id is not null then
    return query select v_document.id, v_job.id, true, v_document.status;
    return;
  end if;

  insert into public.ingestion_jobs (
    organization_id, document_id, pipeline_version, content_hash
  )
  values (
    p_organization_id, v_document.id, p_pipeline_version, p_content_hash
  )
  returning * into v_job;

  return query select v_document.id, v_job.id, false, v_document.status;
end;
$$;
