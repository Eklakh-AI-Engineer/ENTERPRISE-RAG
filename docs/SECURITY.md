# Enterprise RAG — Security Baseline

## Phase 1 security decisions

### Secrets

- Provider keys live only in environment variables.
- .env is ignored.
- .env.example contains placeholders only.
- Frontend VITE_* variables must never contain provider secrets.

### Tenant isolation

The production lexical strategy is per-tenant BM25.

A global BM25 index followed by metadata filtering is not an accepted production design.

### Supabase request path

Normal user operations should carry the user's authorization context so RLS can enforce ownership.

Service-role credentials are restricted to explicitly trusted operations and do not prove that RLS is working.

### Uploaded documents

Retrieved document content is untrusted input.

Later production generation must:
- keep system/developer instructions separate from retrieved text;
- delimit evidence clearly;
- prevent document text from becoming executable instructions;
- test adversarial prompt-injection documents.

### Request boundaries

The current API validates query length and rejects empty queries.

Later production hardening must add:
- file-type validation
- file-size limits
- request-size limits
- rate limits
- quota enforcement
- safe error responses
- secret-safe logging

## Security testing gate

Before accepting real multi-user data:
1. authenticate as User A;
2. attempt to access User B's document/query/source;
3. verify denial;
4. repeat through the real API path;
5. verify RLS independently.
