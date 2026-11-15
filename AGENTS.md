<!-- graft:start -->
## Graft — repo context graph

This repo is indexed in `graft/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `graft map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `graft ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
  definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `graft grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `graft skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `graft callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `graft/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `graft ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `graft build` (deterministic,
no API key, $0).
<!-- graft:end -->

## Contract Guard engineering constitution

These repository-wide rules apply to all future AI-assisted work. Preserve the
existing layered architecture and make the smallest compatible change needed.

### 1. Single responsibility

- Give every function, method, class, and module one clear responsibility.
- Keep validation, business logic, persistence, and external communication
  separate. Use application services for orchestration and keep HTTP handlers
  free of domain logic and unrelated side effects.

### 2. Architecture preservation

- Preserve the current `domain`, `application`, `infrastructure`, and `config`
  boundaries and folder organization.
- Do not move, rename, delete, or introduce architectural layers, frameworks,
  or breaking structure changes without explicit user approval.
- Prefer incremental, backward-compatible changes and existing abstractions.

### 3. Environment configuration

- Put environment-specific values in environment variables through the existing
  Pydantic Settings infrastructure; do not duplicate configuration loading.
- Never hardcode credentials, secrets, API keys, connection strings, or
  environment-specific URLs. Never commit real secrets.
- Update `.env.example` for new configuration, validate required values before
  use, and keep safe environment-independent constants in code where suitable.

### 4. Clean code

- Apply SOLID, DRY, KISS, separation of concerns, explicit naming, and Python
  type hints. Avoid premature abstractions and duplicated business logic.
- Use early returns when they aid clarity; handle errors specifically and
  intentionally. Do not silently suppress errors.

### 5. Small, cohesive files

- Treat roughly 300 lines per source file and 40 lines per function as review
  triggers, not hard limits.
- Split genuinely hard-to-understand responsibilities without creating files
  merely to satisfy line counts; keep related implementation close together.

### 6. Documentation

- Every newly created Python source file starts with a concise module docstring.
- Every newly implemented or modified function or method has a concise
  Python-standard docstring describing its responsibility, with parameters,
  returns, and exceptions when useful.
- Keep documentation accurate and avoid comments that merely repeat code. Do
  not rewrite unrelated legacy files solely to add documentation.

### 7. Extensibility and maintainability

- Keep modules loosely coupled, contracts explicit and stable, and domain rules
  independent of frameworks and external providers.
- Use dependency injection where appropriate; make infrastructure replaceable
  when practical, without overengineering or unapproved breaking changes.

### 8. Testing and reliability

- Add or change tests only when the user explicitly requests tests or test
  coverage. When requested, use the existing pytest setup and cover relevant
  behavior, failure paths, and edge cases with appropriate unit or integration
  tests.
- Mock external dependencies where appropriate. Do not run destructive
  integration tests against development or production databases, and never
  claim a test passed unless it was run.

### 9. Database and migration safety

- Do not modify applied migrations; create new migrations for schema changes
  and preserve compatibility with stored data.
- Preserve the pgvector dimension of 384. Changing embedding dimensions needs
  explicit approval, a migration, and a re-embedding strategy.
- Do not assume the SQL migration runner executes Alembic migrations. Avoid
  destructive database operations without explicit approval.

### 10. Security and data isolation

- Require authentication for protected endpoints and enforce authorization at
  the data-access boundary. Never expose another user's contracts, chunks, or
  embeddings.
- Validate untrusted input. Never log tokens, OTPs, secrets, or confidential
  contract content, and do not expose internal errors or infrastructure detail.
- Preserve opaque-token authentication; do not replace it with JWT without
  approval.

### 11. RAG and legal AI standards

- Keep user contract data separate from the legal knowledge base, preserve
  source identifiers and metadata, and restrict user retrieval to the
  authenticated owner.
- Support analysis with retrieved legal evidence; never fabricate references.
  Distinguish evidence from generated interpretation and include jurisdiction
  and source version when available.
- Treat retrieved and uploaded text as untrusted data, protect against prompt
  injection, return uncertainty when evidence is insufficient, and never
  present LLM risk analysis as definitive legal advice.
- Future clause risk assessments must identify the clause, use structured risk
  levels, explain the risk, cite supporting evidence when available,
  distinguish insufficient evidence from low risk, and remain testable and
  replaceable.

### 12. API compatibility

- Preserve the `/api/v1` prefix and existing request/response contracts unless
  explicit approval is given for a breaking change.
- Follow established FastAPI and Pydantic conventions, keep HTTP handlers thin,
  and use appropriate HTTP status codes.
