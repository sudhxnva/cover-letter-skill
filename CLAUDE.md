# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current State

Only `seed/experiences.json` and `PLAN.md` exist. The `worker/` and `frontend/` directories need to be created. Read `PLAN.md` for full spec before building.

---

## Development Commands

### Wrangler (Worker)
```bash
# From worker/
wrangler dev                          # local dev with remote D1/Vectorize
wrangler deploy                       # deploy to production

# One-time setup
wrangler d1 create cover-letter-experiences
wrangler vectorize create experiences --dimensions=384 --metric=cosine
wrangler secret put ANTHROPIC_API_KEY

# Apply schema
wrangler d1 execute cover-letter-experiences --file=src/schema.sql

# Run seed script (after worker/ is bootstrapped)
wrangler run seed/seed.ts
```

### Frontend
```bash
# From frontend/
npm run dev       # Vite dev server
npm run build     # production build → dist/

# Deploy to Pages
wrangler pages deploy dist --project-name=cover-letter-skill
```

### Wrangler path (if not global)
```
/Users/sudhanva/Documents/personal/code/sudhanva-dev-final/node_modules/.bin/wrangler
```

---

## What This Is

A cover letter generation web app backed by a personal experience memory store.
Part of a larger job application pipeline (see `/Users/sudhanva/Documents/jobapps`).

The user pastes a job URL or JD text. An agent retrieves the most relevant personal
experiences, displays them as interactive nodes in a graph UI, and streams a tailored
cover letter. The user can expand nodes to see full experience details.

Full spec and UX description: `PLAN.md` in this directory. Read it before starting.

---

## Build Scope (Scaffold Demo)

This session builds a **scaffold demo** — enough to show live. Not the full product.

**In scope:**
- Worker + Cloudflare Agents SDK — URL fetch → JD extraction → experience retrieval → cover letter generation
- D1 database — seeded with 6 experiences from `seed/experiences.json`
- Vectorize index — embeddings for all 6 experiences via Workers AI
- Frontend on Pages — two-panel layout, React Flow graph, nodes appear live, cover letter streams, node expand (read-only)

**Out of scope for this session:**
- Node editing + save flow
- Re-embedding on edit
- Telegram path
- Auth (Cloudflare Access)
- More than 6 seed experiences

---

## Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Agent | Cloudflare Agents SDK — `AIChatAgent` | Human-in-the-loop, real-time state sync |
| Embeddings | Workers AI — `@cf/baai/bge-small-en-v1.5` | No external API needed |
| Vector search | Cloudflare Vectorize | Similarity search, returns IDs + scores |
| Full content | Cloudflare D1 | SQLite, fetched by ID after Vectorize query |
| Generation | Claude API — `claude-sonnet-4-6` | Requires `ANTHROPIC_API_KEY` secret |
| Frontend | React + React Flow | Node graph + cover letter panel |
| Hosting | Cloudflare Pages | |
| URL fetching | r.jina.ai proxy | All URLs including LinkedIn job postings |

---

## Cloudflare Account

- **Account:** Sudhanva
- **Account ID:** `0b5e10a591aec1e13627125281ef9f13`
- **Wrangler:** `/Users/sudhanva/Documents/personal/code/sudhanva-dev-final/node_modules/.bin/wrangler`
  (or install globally: `npm install -g wrangler`)
- **Auth:** Already logged in via OAuth
- **Vectorize:** Available and confirmed working on this account
- **Existing Pages projects:** `sudhanva-dev` (sudhanva.dev), `swe-logs`

---

## Project Structure to Create

```
cover-letter-skill/
  CLAUDE.md                  ← this file
  PLAN.md                    ← full spec
  seed/
    experiences.json         ← 6 seed experiences (already written)
  worker/
    src/
      index.ts               ← Worker entrypoint + routes
      agent.ts               ← AIChatAgent — core flow
      experience.ts          ← D1 read, Vectorize query/upsert, scoring
      scoring.ts             ← recency + outcome weighting
      types.ts               ← shared types
    wrangler.toml
    package.json
    tsconfig.json
  frontend/
    src/
      App.tsx
      components/
        GraphCanvas.tsx       ← React Flow canvas
        ExperienceNode.tsx    ← node component, expandable (read-only for now)
        CoverLetterPanel.tsx  ← streaming cover letter output
    package.json
    vite.config.ts
```

---

## Agent Flow

```
1. Receive job URL or raw JD text via WebSocket message

2. If URL:
   - fetch https://r.jina.ai/{url} → markdown text
   - Use Workers AI to extract: company, role, key themes, keywords

3. Embed the extracted JD text using Workers AI (@cf/baai/bge-small-en-v1.5)

4. Query Vectorize → top-20 by similarity
   Apply scoring in Worker:
     score = (similarity × 0.5) + (recency × 0.3) + (outcome × 0.2)
     recency = e^(-0.05 × months_ago)
     outcome = { 1: 1.0, 0: 0.5, -1: 0.75 }[interview_led_to]
   Select top 3–5

5. Fetch full experience objects from D1 by ID

6. setState({ experiences, phase: 'review' })
   ← frontend receives this, nodes appear in the graph

7. Wait for 'generate' signal from frontend via WebSocket
   (user has reviewed nodes; in scaffold this fires automatically after a short delay)

8. Stream cover letter using Claude API (claude-sonnet-4-6)
   Context: JD summary + top experiences (refined text + themes + impact)

9. setState({ coverLetter, phase: 'done' })
   ← frontend cover letter panel updates
```

---

## D1 Schema

```sql
CREATE TABLE IF NOT EXISTS experiences (
  id                TEXT PRIMARY KEY,
  date              TEXT,
  type              TEXT,
  source            TEXT,
  title             TEXT NOT NULL,
  raw               TEXT,
  refined           TEXT,
  themes            TEXT,
  impact            TEXT,
  relevance_signals TEXT,
  used_in           TEXT,
  interview_led_to  INTEGER DEFAULT -1,
  updated_at        TEXT DEFAULT (datetime('now'))
);
```

---

## Vectorize Index

- **Index name:** `experiences`
- **Dimensions:** 384 (output of `@cf/baai/bge-small-en-v1.5`)
- **Metric:** cosine

Create with:
```bash
wrangler vectorize create experiences --dimensions=384 --metric=cosine
```

Each vector:
- `id`: same as D1 experience ID
- `values`: embedding of the `refined` field
- `metadata`: `{ date, type, source, interview_led_to }` (lightweight only — full content is in D1)

---

## Seed Data

All 6 seed experiences are in `seed/experiences.json`. Load them with a one-time script
or wrangler D1 execute after schema creation. Also embed and upsert all 6 to Vectorize.

Write a `seed/seed.ts` script that:
1. Reads `experiences.json`
2. Inserts all rows into D1
3. Embeds each `refined` field via Workers AI
4. Upserts vectors to Vectorize

Run via: `wrangler d1 execute` for D1, and a local script for Vectorize upsert.

---

## Environment Variables / Secrets

Set via wrangler:
```bash
wrangler secret put ANTHROPIC_API_KEY
```

In `wrangler.toml`:
```toml
[[d1_databases]]
binding = "DB"
database_name = "cover-letter-experiences"
database_id = "<created by wrangler>"

[[vectorize]]
binding = "VECTORIZE"
index_name = "experiences"

[ai]
binding = "AI"
```

---

## Frontend State (driven by agent setState)

The frontend connects to the agent via WebSocket. Agent state shape:

```typescript
type AgentState = {
  phase: 'idle' | 'fetching' | 'extracting' | 'retrieving' | 'review' | 'generating' | 'done' | 'error'
  jd: { company?: string; role?: string; summary?: string } | null
  experiences: Experience[]   // populated one by one during retrieval
  coverLetter: string         // streamed in during generation
  error?: string
}
```

Nodes appear as `experiences` array fills. Cover letter streams as `coverLetter` string grows.
The graph canvas re-renders on each state update.

---

## React Flow Setup

- Nodes: one per experience, positioned vertically on the left
- Edges: from each experience node to a single "Cover Letter" target node on the right
- Experience node shows: title + one-line summary
- Click to expand: shows all fields from the Experience object (read-only in scaffold)
- Cover Letter node: contains the streaming text (or links to the right panel)

Use `@xyflow/react` (React Flow v12+).

---

## Key Decisions (Do Not Revisit)

- **No ChromaDB** — can't run in CF Workers (Python library). Vectorize + D1 is the stack.
- **CF Agents SDK over LangGraph** — real-time state sync to frontend is built in, cleaner for this use case
- **r.jina.ai for all URLs** — LinkedIn MCP is a Claude Code tool, not available in Workers
- **Claude API for generation** — Workers AI models are too weak for cover letter quality
- **Cloudflare Access for auth** — deferred to post-demo; no auth in scaffold
- **Scaffold scope** — node editing/persistence is post-demo; read-only expand is fine
