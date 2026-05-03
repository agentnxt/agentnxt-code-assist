# Architecture Decision Records (ADR)

This document tracks key architectural decisions for CodeAssist.
Each decision includes: context, options considered, evaluation method, decision, and rationale.

## Recent Decisions

### ADR-001: Local-first memory architecture (2026-05-03)

**Context:**
Need to decide how to store project memory - cloud database vs local files.

**Options Considered:**
1. Cloud database (PostgreSQL with pgvector) - external service, searchable
2. Local Markdown files (.agennext/memory.md) - simple, reviewable
3. Hybrid - local + optional cloud RAG backend

**Evaluation Method:**
- Reviewed simplicity, reviewability, air-gapped support
- Tested local file read/write performance
- Assessed external DB dependency

**Decision:**
Use local Markdown files (`.agennext/memory.md`) with optional cloud RAG backend.

**Rationale:**
- Users can read/edit memory files manually
- No external DB dependency for basic operation  
- Works in air-gapped mode
- Audit trail stays in repo

**Consequences:**
- Memory bounded to ~100KB before compaction
- Cross-repo queries require workspace layout
- Cloud RAG optional for larger scale

---

### ADR-002: OAuth provider authentication (2026-05-03)

**Context:**
User authenticates with LLM providers - should we use OAuth or manual API key entry?

**Options Considered:**
1. Manual API key entry via form - simple, no OAuth complexity
2. OAuth popup flow - better UX, no key handling
3. OAuth with manual fallback (Gateway mode)

**Evaluation Method:**
- Tested OAuth popup flow in browser
- Assessed token refresh handling
- Reviewed enterprise/custom provider needs

**Decision:**
OAuth popup flow with manual fallback (Gateway mode).

**Rationale:**
- Better UX: one-click sign-in
- No credential handling by CodeAssist
- Gateway mode for enterprise/custom

**Consequences:**
- Requires OAuth callback handling
- Provider-specific login URLs

---

### ADR-003: Security gates fail-closed (2026-05-03)

**Context:**
How to handle security finding severity levels - fail open or fail closed?

**Options Considered:**
1. Fail open - warn but continue (risky for production)
2. Fail closed - always stop on errors (safe but blocking)
3. Configurable per-severity level

**Evaluation Method:**
- Analyzed security incident patterns
- Reviewed production deployment requirements
- Tested --fail-on-anomaly-severity flag

**Decision:**
Errors always fail, warnings fail if `--fail-on-anomaly-severity warning` is passed.

**Rationale:**
- Secret leaks can't be ignored
- Production mode strict by default
- Explicit opt-in to allow warnings

**Consequences:**
- Runs fail on error-severity security findings
- Audit trace records all findings

---

### ADR-004: Local LLM fallback for rate limits (2026-05-03)

**Context:**
Provider API rate limits exhausted - how to continue operations?

**Options Considered:**
1. Fail immediately - clear error message
2. Queue requests - wait for rate limit reset
3. Local llama.cpp fallback - use local models

**Evaluation Method:**
- Tested llama.cpp inference locally
- Measured model download size vs capability
- Assessed air-gapped compatibility

**Decision:**
Local llama.cpp fallback with pre-downloaded GGUF models.

**Rationale:**
- Works offline when API exhausted
- No additional API costs
- Air-gapped compatible

**Consequences:**
- Models must be downloaded first
- Slower than cloud APIs
- Limited model size (~8B params)

---

### ADR-005: Quality gates in-process (2026-05-03)

**Context:**
Run quality gates as separate microservices or in-process?

**Options Considered:**
1. External microservices - scalable, complex deployment
2. In-process gates - simple, shared context
3. Plugin interface with external tool runners

**Evaluation Method:**
- Benchmarked in-process vs external execution
- Reviewed deployment complexity
- Assessed shared context benefits

**Decision:**
Run in-process by default, with plugin interface for external tools.

**Rationale:**
- Simpler deployment
- Shared context with agent
- External tools via `--check` argument

**Consequences:**
- All gates run in single process
- Scalable version can add worker queue

---

### ADR-006: Update mode: Git CLI (2026-05-03)

**Context:**How to update target repositories - GitHub API vs Git CLI vs filesystem?

**Options Considered:**
1. GitHub API - direct, quota-managed
2. Git CLI - full features, local checkout
3. Raw filesystem - insecure, no audit

**Evaluation Method:**
- Tested each update path
- Measured API quota usage
- Reviewed audit trail completeness

**Decision:**
Git CLI with token auth for all updates.

**Rationale:**
- Full git feature support
- Audit trail via commits
- Works without GitHub API quota

**Consequences:**
- Requires git installed
- Local checkout needed

---

## Future Decisions To Make

- [ ] Rate limiting strategy
- [ ] Multi-tenant isolation model
- [ ] Audit log retention policy