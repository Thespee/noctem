# Noctem: Ideals v0.9.1+ — The Evolved Vision

*Last Updated: 2026-02-17*

---

## The North Star (Unchanged)

> **"I never want to touch a computer again. This system should do it all for me while I am off engaging with life."**

This vision drives everything. Every architectural decision, every feature, every line of code should move toward complete automation of digital life management while maintaining absolute data sovereignty and respect for human attention.

---

## 1. The Evolved Architecture: ID-Alfred-Ego

The system evolves from a monolithic assistant into a layered cognitive architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    USER INPUT                           │
└─────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  ID LAYER (Instant, <5s)                                │
│  • Acknowledgment: "Got it"                             │
│  • Quick classification via embedding similarity        │
│  • Enters input into system state                       │
│  • NO LLM call — rule/embedding based only              │
└─────────────────────────────────────────────────────────┘
                    │
	                ▼
┌─────────────────────────────────────────────────────────┐
│  ALFRED (Butler Evolution, 10-15s)                      │
│  • Super-ego: orchestrates ego agents                   │
│  • Manages task queue (create, prioritize, execute)     │
│  • Decides which ego agent handles the task             │
│  • Contacts user as needed (adaptive, not fixed limit)  │
│  • Merges data after agent runs                         │
│  • Maintains the unified system view                    │
└─────────────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│   DO     │ │   PLAN   │ │ IMPROVE  │ │   KNOW   │
│  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │
├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤
│ Execute  │ │ Strategy │ │ Patterns │ │ Ground   │
│ tasks    │ │ & goals  │ │ & maint  │ │ & verify │
│          │ │          │ │          │ │          │
│ Sandbox: │ │ Sandbox: │ │ Sandbox: │ │ Sandbox: │
│ Task DB  │ │ Full DB  │ │ Logs     │ │ Wiki     │
│ Calendar │ │ Projects │ │ Insights │ │ Sources  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 1.1 ID Layer: The Instant Acknowledger

The ID layer provides immediate feedback. Research shows human conversation expects ~200ms between turns. The ID layer provides:

- **Instant acknowledgment** (<5s): User knows input was received
- **Quick classification**: Embedding similarity to known patterns
- **System entry**: Input recorded to thoughts table
- **No waiting**: Butler/agents work in background

**Upgrade path:** Start with rule-based + cached embeddings. Future versions could use a tiny distilled model (sub-1B parameters) for richer instant responses.

### 1.2 Alfred: The Cognitive Orchestrator

Alfred (the evolved Butler) is the system's super-ego — not executing tasks, but managing the minds that do. Responsibilities:

1. **Task Queue Management**: Creates, prioritizes, and assigns tasks to appropriate ego agents
2. **Agent Lifecycle**: Spins up agents with appropriate context, receives results, handles failures
3. **Data Merging**: After an agent completes, Alfred reconciles any state changes
4. **User Contact**: Discretionary outreach (~5 sessions/week guideline, no hard limit)
5. **Batching**: When switching agents (expensive), batches similar tasks together

**Key insight:** Alfred doesn't need to be smart about *doing* things. It needs to be smart about *deciding who does things*.

First implementation will skip the ego agents and just use Alfred to execute tasks

### 1.3 Ego Agents: Specialized Minds

Each ego agent has:
- **Identity document**: Context for how it should behave
- **Skill scope**: Which skills it can invoke
- **Local context**: Its own conversation/reasoning history
- **Permissions**: What data/systems it can access
- **Sandbox**: Isolated execution environment

**The Five Egos:**

| Agent | Purpose | Sandbox Access | Key Skills |
|-------|---------|----------------|------------|
| **Do** | Execute discrete tasks | Task DB, calendar, limited external | Task completion, time management |
| **Plan** | Strategic planning | Full DB (read), projects/goals | Scheduling, prioritization, goal decomposition |
| **Improve** | System maintenance | Logs, patterns, insights | Pattern detection, suggestion generation |
| **Know** | Knowledge grounding | Wiki, sources, skills registry | RAG, citation, fact verification |
| **Interface** | Web/API/Telegram | Session state, user preferences | Response formatting, UI adaptation |

**Future consideration:** Each ego could have its own page on the web dashboard for direct interaction.

---

## 2. The Ideal Classification: From Rules to Semantics

### Current State (Rules-Based)
```python
ACTION_VERBS = {"buy", "get", "call", "email", ...}
if any(verb in text.lower() for verb in ACTION_VERBS):
    return ACTIONABLE
```

### Ideal State (Embedding-Based)
```python
# Pre-computed embeddings for task patterns
PATTERNS = {
    "task_creation": embed("I need to buy something"),
    "task_creation": embed("Remind me to do something"),
    "note": embed("Just a thought about something"),
    "question": embed("What is something?"),
    ...
}

def classify(text):
    text_emb = embed(text)
    similarities = {k: cosine_sim(text_emb, v) for k, v in PATTERNS.items()}
    best_match = max(similarities, key=similarities.get)
    confidence = similarities[best_match]
    
    if confidence > 0.8:
        return best_match, "high"
    elif confidence > 0.5:
        return best_match, "medium"  # ID responds, Alfred confirms
    else:
        return "ambiguous", "low"    # Route to Know agent
```

### Transition Strategy
1. **Phase 1:** Add embedding path alongside rules, measure accuracy
2. **Phase 2:** Route ambiguous cases through embedding path
3. **Phase 3:** Replace rules with embeddings where proven superior
4. **Phase 4:** Tokenizer-level patterns (research needed)

**The ideal:** Rules catch obvious cases instantly. Embeddings catch semantic variations. LLM only for genuinely ambiguous input.

---

## 3. The Ideal Sandboxing: Secure Yet Capable

### Research Consensus (2026)
- Standard containers share host kernel — insufficient for untrusted code
- gVisor provides user-space kernel mediation — good balance
- Firecracker microVMs provide full isolation — ~125ms boot, production-grade

### Ideal for Noctem (Personal MVP)

For a single-user system, full microVM isolation is likely overkill. The ideal approach:

```
┌─────────────────────────────────────────┐
│  ALFRED (Host Process)                   │
│  • Has access to secrets                 │
│  • Manages agent lifecycle               │
│  • Injects secrets as needed             │
└─────────────────────────────────────────┘
              │
              │ (spawn with restricted capabilities)
              ▼
┌─────────────────────────────────────────┐
│  EGO AGENT CONTAINER                     │
│  • No direct secret access               │
│  • Read-only filesystem (mostly)         │
│  • Network egress controlled             │
│  • CPU/memory limits                     │
│  • Ephemeral — destroyed after task      │
└─────────────────────────────────────────┘
```

**Key principles (from NVIDIA guidance):**
1. Secrets injected, not shared
2. Lifecycle management prevents accumulation
3. Explicit approval for isolation violations
4. Zero-trust within sandbox

**Upgrade path:** If moving to multi-user (1.0+), implement proper gVisor or Firecracker isolation.

---

## 4. The Ideal Context Management

### The Problem
7B models have 4-8K context. Long-running agents exhaust this quickly, leading to "context degradation syndrome" where the model loses coherence.

### Research Finding (JetBrains, 2025)
"Observation masking outperforms LLM summarization in terms of overall efficiency and reliability."

### Ideal Implementation

```python
class ContextManager:
    def __init__(self, max_tokens=4000, recent_turns=10):
        self.max_tokens = max_tokens
        self.recent_turns = recent_turns
    
    def prepare_context(self, history, current_task):
        # Always include: system prompt, current task
        core = self.system_prompt + current_task
        
        # Recent turns: full content
        recent = history[-self.recent_turns:]
        
        # Older turns: mask observations, keep decisions
        older = []
        for turn in history[:-self.recent_turns]:
            older.append({
                "input": turn["input"],
                "decision": turn["decision"],
                "observation": "[MASKED]"  # Hide intermediate work
            })
        
        # External state: query DB instead of keeping in context
        relevant_tasks = db.query_related_tasks(current_task)
        relevant_wiki = wiki.search(current_task, k=3)
        
        return compose(core, older, recent, relevant_tasks, relevant_wiki)
```

### Strategies

1. **Observation masking**: Hide reasoning traces after decisions made
2. **Session boundaries**: Butler contact = context reset opportunity
3. **External state**: Database is memory, not context window
4. **Task-scoped context**: Don't carry unrelated history
5. **Sliding window with overlap**: 512 tokens with 64-token overlap for continuity

---

## 5. The Ideal User Feedback Loop

### Current: Fixed Contact Budget
- 5 contacts/week maximum (hard limit)
- Binary: contact or don't

### Ideal: Guideline-Based Discretion

```yaml
feedback_config:
  weekly_session_guideline: 5  # Soft target, Alfred uses discretion
  session_types:
    scheduled:
      - type: daily_briefing
        time: "08:00"
        duration: 5min
      - type: weekly_review
        day: sunday
        duration: 15min
    
    urgent:
      threshold: critical_deadline_within_24h
      max_per_day: 2
      
    user_initiated:
      limit: none
      
  session_content:
    - status_summary
    - pending_decisions (max 3)
    - suggestions (max 2)
    - quick_actions (numbered for easy response)
```

**Key insight:** No hard limit — Alfred uses discretion. The ~5/week guideline lives in Alfred's identity document as behavioral context, not enforced code. Trust the system to be respectful.

---

## 6. The Ideal Zero-Downtime Updates

### Goal
Update to newer versions while keeping the system online, avoiding service interruptions.

### Implementation (Gunicorn + Blue/Green)

```bash
# Current setup
/app/versions/v0.9.1/  # Running
/app/versions/v0.9.2/  # New version, tested

# Symlink swap
ln -sfn /app/versions/v0.9.2 /app/current

# Graceful reload (no dropped requests)
kill -HUP $(cat /app/gunicorn.pid)
```

**Gunicorn HUP behavior:**
1. Start new workers with new code
2. Stop routing requests to old workers
3. Old workers finish in-flight requests
4. Old workers shut down
5. Zero requests dropped

### Database Migrations
- Use Alembic for schema migrations
- Migrations must be backwards-compatible
- Old code must work with new schema (briefly)
- Test migration on snapshot before applying

---

## 7. The Long-Term Vision (Updated)

### Phase 1: Foundation (v0.6-0.7) ✓
- Execution logging, correction feedback, self-improvement engine

### Phase 2: Skills (v0.8) ✓
- Skill registry, progressive disclosure, user-created skills

### Phase 3a: Knowledge (v0.9.0) ✓
- Document ingestion, vector search, citation system

### Phase 3b: Architecture Evolution (v0.9.1)
- ID layer for instant acknowledgment
- Alfred evolution from Butler
- Embedding-based classification
- Context management
- Zero-downtime deployment infrastructure

### Phase 3c: Learning (v0.9.2)
- Digital Aristotle: Socratic mode, spaced repetition
- Review mode with SM-2 algorithm

### Phase 4: Ego Agents (v0.9.3)
- Start with single ego (Improve)
- Prove value before adding complexity
- Container-based sandboxing
- Agent-specific web pages

### Phase 5: External Actions (v1.0)
- Durable workflows (Temporal)
- Email drafting, calendar write-back
- Human checkpoints on risky actions

### Phase 6: Friends Release (v1.0+)
- Documentation and installation guides
- Multi-user considerations
- Security hardening

### Phase 7: Public (v2.0)
- Mobile companion
- Proper sandboxing (gVisor/Firecracker)
- Community and support

---

## 8. The Ultimate Goal (Restated)

A system that:
- **Knows what you know** (wiki) ✓
- **Knows what you need to do** (tasks/projects) ✓
- **Respects your attention** (adaptive feedback, not spam)
- **Learns from your corrections** (self-improvement) ✓
- **Responds instantly** (ID layer)
- **Thinks deeply when needed** (Alfred + ego agents)
- **Acts on your behalf** (with approval for risky actions)
- **Stays completely private** (local-first) ✓
- **Never goes down** (zero-downtime updates)

---

## 9. Ego Agent Web Interface (Future Vision)

Each ego agent gets its own web page for direct interaction:

```
/agents/do      → Active tasks, execution queue, quick actions
/agents/plan    → Goals, projects, timeline view, priorities
/agents/improve → Pattern insights, system health, suggestions
/agents/know    → Wiki search, source management, knowledge gaps
/agents/interface → Configuration, preferences, session history
```

**Goals and Projects block** moves to `/agents/plan`, as that's the natural home for strategic thinking.

---

## 10. What "Done" Looks Like

The north star is achieved when:

1. **Morning:** You wake up. Alfred has already reviewed your calendar, prioritized your tasks, and has a 2-minute briefing ready.

2. **Throughout the day:** Thoughts captured via voice or text are instantly acknowledged. Tasks appear in the right projects. Calendar suggestions are offered for time-sensitive items.

3. **Decisions:** When Alfred needs input, it batches questions into focused sessions. You respond with a number ("3" for option 3) and move on.

4. **Knowledge:** When you wonder about something, the wiki provides grounded answers with citations. If it doesn't know, it says so.

5. **Learning:** The system prompts you to review concepts you're learning, using spaced repetition tuned to your recall patterns.

6. **Automation:** Email drafts appear for your approval. Calendar events are created (but not sent) until you confirm. The system acts — but never commits — without you.

7. **Evolution:** Every week, the Improve agent surfaces 2-3 ways the system could work better. You approve or dismiss. The system learns.

8. **Zero maintenance:** Updates happen invisibly. The system stays online. You never "manage" it.

This is the ideal. Every version moves closer.

---

*Co-Authored-By: Warp <agent@warp.dev>*
