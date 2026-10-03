-- Enforce that an ingestion job and its document always belong to the same organization.

alter table public.documents
  add constraint documents_organization_id_id_key unique (organization_id, id);

alter table public.ingestion_jobs
  add constraint ingestion_jobs_document_org_fkey
  foreign key (organization_id, document_id)
  references public.documents (organization_id, id)
  on delete cascade;
