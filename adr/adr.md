# Architecture Decision Records (ADR)

This document tracks key architectural decisions for CodeAssist.

## Recent Decisions

### ADR-001: Local-first memory architecture (2026-05-03)

**Status:** Accepted ✅

**Context:**
Need to decide how to store project memory - cloud database vs local files.

**Decision:**
Use local Markdown files (`.agennext/memory.md`) with optional cloud RAG backend.

**Rationale:**
- Reviewable: Users can read/edit memory files manually
- No external DB dependency for basic operation  
- Works in air-gapped mode
- Audit trail stays in repo

**Consequences:**
- Memory bounded to ~100KB before compaction
- Cross-repo queries require workspace layout
- Cloud RAG optional for larger scale

---

### ADR-002: OAuth provider authentication (2026-05-03)

**Status:** Accepted ✅

**Context:**
User authenticates with LLM providers - OAuth vs manual API key entry.

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

**Status:** Accepted ✅

**Context:**
How to handle security finding severity levels.

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

**Status:** Accepted ✅

**Context:**
Provider API rate limits exhausted - how to continue.

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

**Status:** Accepted ✅

**Context:**
Run quality gates as separate microservices vs in-process.

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

**Status:** Accepted ✅

**Context:**How to update target repositories.

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