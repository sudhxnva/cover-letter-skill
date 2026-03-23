# Cover Letter Skill — Plan

## What This Is

Phase 2 of the job application pipeline. Takes a job description, retrieves the most relevant
personal experiences from a persistent memory store, and generates a tailored cover letter.

Two surfaces:
- **Web app**: interactive graph UI — experience nodes, arrows to cover letter, inline editing
- **Telegram**: non-interactive — cover letter + list of experiences used, reply to refine

---

## User Experience

### Web App

1. Paste a job description or drop a job URL into a text field. Hit Generate.

2. The page splits: left panel is the graph area, right panel is the cover letter area.
   Both start empty.

3. Experience nodes appear on the left one by one as the agent retrieves them. Each node
   shows the experience title and a one-line summary. An arrow draws from each node toward
   the right panel.

4. The cover letter streams into the right panel once experiences are retrieved.

5. You review the nodes. If one is thin — missing detail, wrong framing — you click it.
   The node expands and shows all stored fields:

   | Field | Description |
   |---|---|
   | Title | Short label for the experience |
   | Raw | The original captured narrative, unpolished |
   | Refined | The cleaned-up version used in generation |
   | Themes | e.g. leadership, time-pressure, problem-solving |
   | Impact | Quantified outcome if available |
   | Relevance signals | Phrases that map to JD language |
   | Date | Month + year |
   | Type / Source | achievement · academic, challenge · work, etc. |
   | Used before | Companies where this experience was previously used |
   | Helped get interview? | Feedback loop — yes / no / unknown |

6. You edit the `refined` text (or any field) directly. Hit save.
   - Persists to D1 immediately
   - Re-embeds the refined text and updates Vectorize
   - Cover letter does not auto-regenerate — you hit Regenerate manually

7. Regenerate produces an updated cover letter using the corrected experience.

### Telegram

Same retrieval and generation pipeline, no interactivity.

Cover letter is sent as the main message. A follow-up message lists the experiences used:

```
Here's your cover letter for [Company].

Experiences referenced:
• [Title 1]
• [Title 2]
• [Title 3]

Reply "refine [title]" to add more detail to any of these.
```

"Refine" triggers a follow-up capture flow (future — Phase 2c).

---

## Architecture

### Storage: Vectorize + D1

ChromaDB (used in local Phase 2) cannot run in Cloudflare Workers — it's a Python library
running in V8 isolates. The Cloudflare equivalent is Vectorize + D1 together.

**Vectorize** — similarity search layer
- Stores: embedding vector + lightweight metadata per experience
- Metadata kept minimal (ID, date, type, source, interview_led_to) due to size limits
- Query returns: top-k IDs + similarity scores

**D1** — full content layer
- Stores: complete experience object (all fields)
- Fetched by ID after Vectorize returns candidates
- Edits from the web app write here first, then trigger re-embedding to Vectorize

**Schema (D1):**

```sql
CREATE TABLE experiences (
  id                TEXT PRIMARY KEY,
  date              TEXT,           -- YYYY-MM
  type              TEXT,           -- achievement | challenge | growth | mentorship | technical | personal | volunteer
  source            TEXT,           -- work | academic | personal | volunteer
  title             TEXT,
  raw               TEXT,
  refined           TEXT,           -- this is what gets embedded
  themes            TEXT,           -- comma-separated
  impact            TEXT,
  relevance_signals TEXT,           -- comma-separated
  used_in           TEXT,           -- comma-separated company names
  interview_led_to  INTEGER,        -- -1=unknown, 1=yes, 0=no
  updated_at        TEXT
);
```

### Retrieval + Scoring

Same scoring formula from `plans/02-memory-store.md`:

```
score = (semantic_similarity × 0.5)
      + (recency_weight      × 0.3)
      + (outcome_weight      × 0.2)
```

Flow:
1. Workers AI (`@cf/baai/bge-small-en-v1.5`) embeds the JD
2. Vectorize returns top-20 by similarity
3. Worker applies recency decay + outcome weighting
4. D1 fetches full content for top 3–5
5. Passed to agent

Recency decay: `e^(-0.05 × months_ago)` — same λ as the local ChromaDB implementation.
Outcome weights: `{ yes: 1.0, no: 0.5, unknown: 0.75 }`

### Agent: Cloudflare Agents SDK

Using `AIChatAgent` from the Cloudflare Agents SDK (not LangGraph).

Key reasons:
- Built-in state that syncs to connected clients in real-time via WebSocket — this is what
  drives the nodes appearing in the UI as the agent retrieves experiences
- State survives hibernation — close the tab, come back, your session and edits are intact
- Human-in-the-loop built in — agent pauses after retrieval, waits for edits, continues
- Native Cloudflare integrations — Vectorize, Workers AI, D1 are first-class

Agent flow:

```
receive JD
    ↓
embed JD (Workers AI)
    ↓
query Vectorize → score → fetch D1
    ↓
setState({ experiences, phase: 'review' })   ← nodes appear in UI
    ↓
[WAIT: human reviews, edits nodes if needed]
    ↓
receive signal: 'generate'
    ↓
stream cover letter (Workers AI or Claude API)
    ↓
setState({ coverLetter, phase: 'done' })     ← right panel updates
```

### Frontend: Cloudflare Pages

- React + React Flow for the node graph
- Nodes: left panel, one per retrieved experience
- Edges: arrows from each node to the cover letter panel
- Click node → drawer opens with all D1 fields, editable
- Save → PUT /experiences/:id → D1 write + Vectorize re-embed
- Regenerate button → sends 'generate' signal to agent via WebSocket
- Cover letter panel: streams in using SSE or WebSocket

### Re-embedding on Edit

When a node is saved with a changed `refined` field:

```
PUT /experiences/:id
    ↓
Write full object to D1
    ↓
Workers AI embeds new refined text
    ↓
Vectorize upsert (same ID, new vector)
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| Agent runtime | Cloudflare Agents SDK (AIChatAgent) |
| Embeddings | Workers AI — @cf/baai/bge-small-en-v1.5 |
| Vector search | Cloudflare Vectorize |
| Full content store | Cloudflare D1 (SQLite) |
| Cover letter generation | Claude API (claude-sonnet-4-6) — requires Anthropic API key from console.anthropic.com |
| Frontend | React + React Flow, deployed on Cloudflare Pages |
| API | Cloudflare Workers |

### Auth: Cloudflare Access

Single-user personal app — using Cloudflare Access (Zero Trust) rather than Auth0.

- Configured entirely in the Cloudflare dashboard, zero code changes
- Wraps the Pages app with a Google/GitHub login screen automatically
- Free for personal use
- Keeps everything on Cloudflare

Auth0 would require SDK integration, callback routes, and session handling — overkill for
one user. Cloudflare Access is the right tool here.

---

## Seed Data

Starting with the 6 experience narratives already stored in memory. These will be manually
inserted into D1 and embedded into Vectorize before the first generation run.

Experiences to seed:
- iOS app leadership (failure/ownership)
- MUN — building Gatsby site + Electron moderator software
- Drone + CNN research (published paper)
- CTF / ethical hacking workshop
- Ramakrishna Math (8 years of Sunday volunteering)
- Cabbie + agentic systems (current direction)

---

## Repo Structure

```
cover-letter-skill/
  PLAN.md                     ← this file
  worker/
    src/
      agent.ts                ← AIChatAgent — retrieval + generation flow
      experience.ts           ← D1 read/write, Vectorize query/upsert
      scoring.ts              ← recency + outcome weighting
      index.ts                ← Worker entrypoint, routes
    wrangler.toml
  frontend/
    src/
      App.tsx
      components/
        ExperienceNode.tsx     ← React Flow node, expandable
        CoverLetterPanel.tsx   ← streaming output panel
        GraphCanvas.tsx        ← React Flow canvas + edges
    package.json
```

---

## JD Input — URL via r.jina.ai

All URLs (LinkedIn job postings, Greenhouse, Lever, company pages) are fetched via
`r.jina.ai` proxy. The LinkedIn MCP is a Claude Code tool — it doesn't run inside a
Cloudflare Worker. r.jina.ai handles LinkedIn job URLs cleanly.

```
receive URL
    ↓
fetch https://r.jina.ai/{url} → raw markdown text
    ↓
Workers AI extracts: company, role, themes, keywords
    ↓
embed extracted text → Vectorize query
```

Paste input (raw JD text) skips the fetch step and goes straight to extraction.

---

## Build Order — Scaffold Demo

Scoped to what's demoable in a weekend. Full editing/persistence is post-demo.

```
Phase A — Backend (Day 1)
  1. Cloudflare account check: confirm credits applied, Workers Paid active, Vectorize available
  2. Install Wrangler: npm install -g wrangler && wrangler login
  3. D1 schema + manually seed 6 experiences
  4. Vectorize index + embed all 6 via Workers AI
  5. Retrieval + scoring logic (experience.ts, scoring.ts)
  6. Agent flow — URL fetch → extraction → retrieval → setState → generate (agent.ts)
  7. Worker routes + WebSocket

Phase B — Frontend (Day 2)
  8. React app skeleton on Pages — two-panel layout
  9. GraphCanvas with hardcoded mock nodes (React Flow) — nail the visual first
  10. Wire to agent WebSocket — nodes appear live as agent runs
  11. Cover letter panel — streaming text
  12. Basic node expand (read-only for scaffold) — shows all D1 fields

Deferred (post-interview)
  - Editable nodes + save flow
  - Re-embed on save
  - Telegram path
  - Auth (Cloudflare Access)
```

---

## Future

- **Refine with Claude**: button on expanded node triggers a chat workflow to flesh out
  the experience interactively, then saves the result
- **Outcome feedback**: after an application, mark whether it led to an interview —
  updates `interview_led_to` in D1 and adjusts future scoring
- **Experience capture**: Telegram flow to add new experiences conversationally
  (currently planned in `plans/03-capture-experience.md`)
- **Highlight mapping**: hover a node → highlight the sentence in the cover letter
  that references that experience
