# Noctem v0.9.X Implementation Plan (v2)

*Updated: 2026-02-17*
*Supersedes: 0.9.X Plan.md*

---

## Overview

v0.9.0 wiki core is complete. This plan covers the architectural evolution toward the ID-Alfred-Ego system, resolving known issues (rules-based capture, context exhaustion, access/sandboxing), and preparing for 1.0.

Note the updated version implementation order at the end of the document; 

**Versioning Philosophy:**
- **0.9.x**: Personal MVP — reliable daily driver for the creator
- **1.0**: Friends release — stable enough to share with trusted users
- **2.0**: Public release — documented, hardened, community-ready

---

## Unsolved Issues (Tracked)

| Issue | Status | Target Version |
|-------|--------|----------------|
| Rules-based capture limitations | Solution identified (embeddings) | 0.9.2 |
| Context exhaustion for small models | Solution identified (observation masking) | 0.9.3 |
| Access/sandboxing for agents | Solution identified (container isolation) | 0.9.5 |
| Zero-downtime updates | Solution identified (Gunicorn HUP) | 0.9.4 |
| Butler contact guidance | Guideline: ~5 sessions/week (no hard limit) | 0.9.3 |

---

## Version Plan

### v0.9.1 — Wiki CLI & Quick Wins (Current Priority)
**Goal:** Make the wiki usable, not just implemented.
**Estimate:** 4-6 hours

**Deliverables:**
1. Wiki CLI commands
   - `noctem wiki ingest [file]` — Process files from `data/sources/`
   - `noctem wiki search "query"` — Semantic search with top-K results
   - `noctem wiki ask "question"` — Full Q&A with citations
   - `noctem wiki sources [--trust N]` — List indexed sources
   - `noctem wiki status` — Indexing stats
   - `noctem wiki verify` — Check for changed source files

2. Skill-Wiki bridge (partial)
   - Add `wiki_context` field to skill execution input
   - Skills can request wiki retrieval in instructions

3. Web dashboard — Butler status widget
   - Feedback sessions: X/5 remaining this week
   - Next scheduled session
   - [Summon] button

**Implementation notes:**
- Use existing `noctem/wiki/` module functions
- Follow existing CLI patterns (click groups)
- Status widget: `/api/butler/status` endpoint + JS polling (30s)

---

### v0.9.2 — Embedding-Based Classification
**Goal:** Move beyond regex rules for intent detection.
**Estimate:** 6-8 hours

**Deliverables:**
1. Embedding classifier module (`noctem/fast/embedding_classifier.py`)
   - Pre-compute embeddings for intent patterns
   - Pattern categories: task_creation, note, question, ambiguous, other
   - Configurable similarity threshold (default 0.7)

2. Hybrid classification pipeline
   ```
   Input → Embedding similarity (30-40%)
        → Even if match: Rule fast-path record data for investigation later
        → If still ambiguous: Queue for Butler/Know agent (10-20%)
   ```

3. Benchmarking infrastructure
   - Compare rule-only vs hybrid accuracy on historical thoughts
   - Log classification path (rule/embedding/llm) to execution logs
   - Weekly report on classifier performance

**New files:**
- `noctem/fast/embedding_classifier.py`
- `noctem/fast/pattern_embeddings.json` (cached embeddings)

**Dependencies:**
- Ollama `nomic-embed-text` (already used for wiki)

**Upgrade path for tokenizer-level patterns:** Document for future research. Idea: if task commands have similar tokenizations, create rules at token level rather than word level.

---

### v0.9.3 — Context Management & Adaptive Feedback
**Goal:** Handle context exhaustion; replace fixed contact limit.
**Estimate:** 8-10 hours

**Deliverables:**
1. Context Manager (`noctem/slow/context_manager.py`)
   - Observation masking: hide intermediate reasoning, keep decisions
   - Recent turn preservation (configurable, default 10)
   - External state injection from DB/wiki
   - Token counting and budget tracking

2. Feedback session guidance (no hard limit)
   - Remove `max_contacts_per_week` entirely
   - Guideline: ~5 sessions/week (in Alfred's identity document)
   - Alfred uses discretion based on urgency and context
   - Session types: scheduled, urgent, user-initiated (all allowed)
   - Config in `config.py`:
     ```python
     feedback_session_guideline = 5  # Soft target, not enforced
     # No hard limit — Alfred decides based on context
     ```

3. Session content batching
   - Batch pending questions (max 3 per session)
   - Include quick-reply options (numbered)
   - Track session effectiveness (response rate, time to respond)

**Database changes:**
```sql
-- Track feedback sessions
CREATE TABLE feedback_sessions (
    id INTEGER PRIMARY KEY,
    session_type TEXT,  -- 'scheduled', 'urgent', 'user_initiated'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    questions_asked INTEGER,
    questions_answered INTEGER,
    user_response_time_seconds INTEGER
);
```

---

### v0.9.4 — Zero-Downtime Deployment
**Goal:** Update system without service interruption.
**Estimate:** 4-6 hours

**Deliverables:**
1. Gunicorn configuration for graceful restarts
   ```python
   # gunicorn.conf.py
   bind = "0.0.0.0:8080"
   workers = 2
   worker_class = "sync"
   graceful_timeout = 30
   pidfile = "/app/gunicorn.pid"
   ```

2. Deployment script (`scripts/deploy.sh`)
   ```bash
   # Pull new code
   # Run migrations (backwards-compatible)
   # Send HUP signal for graceful restart
   kill -HUP $(cat /app/gunicorn.pid)
   ```

3. Alembic migration setup
   - Initialize Alembic for schema migrations
   - Migration backwards-compatibility policy
   - Pre-deployment validation script

4. Health check endpoint (`/api/health`)
   - Version info
   - Database connectivity
   - Model availability

---

### v0.9.5 — ID Layer & Alfred Foundation
**Goal:** Implement the instant response layer and evolved Butler.
**Estimate:** 12-16 hours

**Deliverables:**
1. ID Layer (`noctem/fast/id_layer.py`)
   - Instant acknowledgment (<50ms)
   - Uses embedding classifier from v0.9.2
   - Records to thoughts table
   - Returns immediately; Butler processes async
   
   ```python
   def process_instant(text: str, source: str) -> str:
       classification = classify(text)  # <300ms
       thought = create_thought(text, source, classification)
       queue_for_butler(thought.id)
       return acknowledgment(classification)
   ```

2. Alfred evolution from Butler
   - Rename Butler → Alfred in code
   - Add system task creation foundation; this guy creates the tasks  that the system must complete based on what I send and what tasks exist in the database
   - Add agent dispatch stub (for future egos); at the moment Alfred handles all the tasks
   - Implement follow-up response (sends second message after processing)

3. Telegram integration update
   - ID layer responds first: "Added 'Buy milk' for tomorrow"
   - Alfred follows up: "Added buy milk to shopping list, that trip would fit best at 2pm tomorrow"
	   - keeping track of a shopping list here would be a complex skill, to know that all of these things could be bought form similar places

**Configuration:**
```python
# ID layer settings
instant_response_enabled = True
instant_response_timeout_ms = 300
follow_up_response_enabled = True
```

---

### v0.9.6 — First Ego Agent: Improve
**Goal:** Prove the ego model with lowest-risk agent.
**Estimate:** 10-14 hours

**Deliverables:**
1. Ego agent framework (`noctem/agents/`)
   - Base agent class with identity document
   - Skill scope definition
   - Sandbox permissions model
   - Context isolation

2. Improve agent (`noctem/agents/improve.py`)
   - Access: logs, patterns, insights (read-only to most)
   - Skills: pattern detection, suggestion generation
   - Identity: analytical, conservative, surfaces patterns
   - Runs via Alfred scheduling (not user-triggered)

3. Agent web page (`/agents/improve`)
   - Pattern insights visualization
   - Pending suggestions
   - System health metrics
   - Approve/dismiss actions

**Database changes:**
```sql
CREATE TABLE agent_runs (
    id INTEGER PRIMARY KEY,
    agent_type TEXT,  -- 'improve', 'do', 'plan', 'know'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT,
    input_context TEXT,  -- JSON
    output TEXT,         -- JSON
    tokens_used INTEGER,
    error_message TEXT
);
```

---

# vvv SKIP FOR NOW vvv
### v0.9.7 — Remaining Egos (Plan, Do, Know) 
**Goal:** Complete the ego agent model.
**Estimate:** 20-30 hours

**Deliverables:**
1. Plan agent
   - Access: Full DB (read), projects/goals
   - Skills: scheduling, prioritization, goal decomposition
   - Web page: `/agents/plan` with goals/projects block

2. Do agent
   - Access: Task DB, calendar, limited external
   - Skills: task completion, time management
   - Web page: `/agents/do` with active tasks queue

3. Know agent
   - Access: Wiki, sources, skills registry
   - Skills: RAG, citation, fact verification
   - Web page: `/agents/know` with wiki search

4. Interface agent (lightweight)
   - Handles web/API/Telegram formatting
   - No separate page initially

**Routing logic in Alfred:**
```python
def route_to_agent(thought):
    if thought.kind == "question":
        return "know"
    elif thought.kind == "actionable" and is_task_like(thought):
        return "do"
    elif thought.mentions_planning():
        return "plan"
    else:
        return "do"  # Default
```

---
# ^^^ SKIP FOR NOW ^^^
### v0.9.8+ — Digital Aristotle (Learning)
**Goal:** Transform wiki into active learning system.
**Estimate:** 20-30 hours

**Deliverables:**
1. Query mode enhancement
   - Confidence indicators
   - "I don't know" when sources insufficient
   - Inline citations

2. Socratic mode
   - Generate questions from wiki chunks
   - Challenge assumptions
   - Evaluate answers against sources

3. Review mode (SM-2)
   - `learning_items` table
   - Spaced repetition scheduling
   - Alfred prompts at optimal intervals

---

## 1.0 — Friends Release

**Prerequisite:** All v0.9.x items stable and tested.

### 1.0 Deliverables

1. **Documentation**
   - Installation guide
   - Configuration reference
   - User guide updates

2. **Durable workflows (Temporal)**
   - Email drafting with approval checkpoint
   - Calendar write-back with confirmation
   - Multi-step automations

3. **Security hardening**
   - Container isolation for ego agents
   - Secret injection (not sharing)
   - Audit logging

4. **External integrations**
   - Google Calendar API
   - Email (SMTP/Gmail API)
   - Human checkpoint on all writes

5. **Maintenance protocol v2**
   - Weekly improvement reports (doesn't count against sessions)
   - Model auto-switching recommendations

---

## 2.0 and Beyond

### 2.0 — Public Release
- Mobile companion app
- Docker containerization
- gVisor/Firecracker sandboxing (multi-user security)
- Community setup (docs, Discord, issues)
- Security audit

### Post-2.0 — Personal Skills
- Habit Builder
- Fitness Tracking
- Meal Planning
- Finance Awareness
- Reading List

---

## Priority Summary

| Version   | Focus                             | Estimate   | Depends On |
| --------- | --------------------------------- | ---------- | ---------- |
| 0.9.1     | Wiki CLI, quick wins              | 4-6h       | —          |
| 0.9.**3** | Embedding classification          | 6-8h       | —          |
| 0.9.**4** | Context mgmt, adaptive sessions   | 8-10h      | —          |
| 0.9.**2** | Zero-downtime deployment          | 4-6h       | —          |
| 0.9.5     | ID layer, Agent Alfred foundation | 12-16h     | 0.9.2      |
| 0.9.**7** | Improve ego agent                 | 10-14h     | 0.9.5      |
| ~~0.9.7~~ | ~~Remaining egos~~                | ~~20-30h~~ | ~~0.9.6~~  |
| 0.9.**6** | Digital Aristotle                 | 20-30h     | 0.9.1      |

**Total 0.9.x estimate:** 85-120 hours
**Target for 1.0:** After 0.9.x stable and daily-driven

---

## Guiding Principles

> "I never want to touch a computer again."

1. **Zero-touch operation** — Every feature moves toward automation
2. **Human-in-the-loop for risky actions** — Never send/commit without approval
3. **Local-first, privacy-first** — Cloud only with explicit consent
4. **Put down / pick up** — All work pausable, persisted, resumable
5. **Adaptive attention** — Feedback sessions, not spam

---

## Architecture Notes (from Ideals v0.9.1)

### ID-Alfred-Ego Flow
```
User Input
    │
    ▼
ID Layer (<50ms) → "Got it" → Alfred (1-5s) → Ego Agent → Result
                                    │
                              (routes to)
                                    │
                    ┌───────┬───────┼───────┬───────┐
                    ▼       ▼       ▼       ▼       ▼
                   Do     Plan  Improve   Know  Interface
```

### Ego Agent Properties
- Identity document (behavior context)
- Skill scope (allowed skills)
- Sandbox permissions (data access)
- Local context (conversation history)

### Sandboxing Approach (Personal MVP)
- Docker containers with restricted capabilities
- Secrets injected by Alfred, not shared
- Ephemeral containers (destroyed after task)
- Full isolation (gVisor/Firecracker) deferred to 2.0

---

*Co-Authored-By: Warp <agent@warp.dev>*
