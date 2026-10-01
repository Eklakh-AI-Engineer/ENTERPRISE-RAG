# Supabase Phase 3

This directory contains **reference database artifacts only**.

## Current status

The connected Supabase account currently exposes a project named **Tackboard**. That project is unrelated to Enterprise RAG and has **not** been modified.

Therefore this repository does **not** contain an applied Enterprise RAG migration yet.

## Files

- `schema.sql` — reviewed Phase 3 reference DDL for the intended production schema.
- `../docs/DATABASE.md` — architectural data-model and parity decisions.

## Migration rule

When the dedicated Enterprise RAG Supabase project is identified:

1. Verify the project ID.
2. Check its Postgres and pgvector versions.
3. Generate the migration filename with the installed Supabase CLI:
   `supabase migration new phase3_initial_schema`
4. Move the reviewed SQL into that generated migration.
5. Apply it only to the intended project.
6. Run Supabase security/performance advisors.
7. Verify the schema and RLS with test queries before wiring the application.

Do **not** apply `schema.sql` directly to an unrelated Supabase project.

## Current vector parity assumptions

The reference schema uses the current repository baseline:

- `sentence-transformers/all-MiniLM-L6-v2`
- 384 dimensions
- normalized embeddings
- cosine distance (`<=>`)
- HNSW index with `vector_cosine_ops`

These are **provisional production choices** until the FAISS-vs-pgvector parity benchmark is executed.
