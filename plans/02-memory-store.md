# Plan 02 — Experience Memory Store

## Purpose

A persistent, searchable store of life experiences — professional, academic, personal — that powers cover letter generation. Unlike the resume YAML bank (which is structured, curated content), the memory store captures raw human experiences and surfaces the most relevant ones for a given job.

The key property: **experiences are captured once and retrieved automatically**. You never type the same story into a prompt again.

## What Makes This Different from the YAML Bank

| YAML Bank | Memory Store |
|-----------|-------------|
| Curated resume bullets | Raw narratives + refined stories |
| Professional only | Personal, academic, volunteer, life lessons |
| Manually edited | Captured conversationally via Telegram |
| Selected by Claude reading all entries | Retrieved by vector similarity + scoring |
| Output: resume bullets | Output: cover letter narrative material |

## Experience Data Model

Each entry in the memory store:

```yaml
id: hackathon-cu-2024
date: 2024-03                    # absolute YYYY-MM — required for recency weighting
type: achievement                # see types below
source: academic                 # see sources below
title: Won CU Boulder Hackathon 2024
raw: >
  We had 24 hours. Team of 4. Built a food waste reduction app for
  dining halls. Won 1st out of 40 teams. I led the team and did
  most of the backend.
refined: >
  Led a 4-person team in a 24-hour hackathon, building a food waste
  reduction system for university dining halls. Delivered a working
  backend under time pressure and won 1st place among 40 teams.
themes:
  - leadership
  - time-pressure
  - problem-solving
  - teamwork
  - full-stack
impact: "1st place, 40 teams"
relevance_signals:              # phrases that map to JD language
  - fast-paced environment
  - cross-functional team
  - shipping under pressure
  - end-to-end ownership
used_in:
  - Ramp                        # companies where this was used
interview_led_to: true          # feedback loop — did this help?
```

### Experience Types

- `achievement` — awards, wins, recognition
- `challenge` — a hard situation and how it was handled
- `growth` — a lesson learned, a skill developed
- `mentorship` — mentoring or being mentored
- `technical` — a specific technical problem solved
- `personal` — life experience, value formed, perspective gained
- `volunteer` — community, extracurricular, service

### Experience Sources

- `work` — full-time or internship
- `academic` — coursework, research, class projects
- `personal` — outside work and school
- `volunteer` — community involvement, clubs

## Retrieval and Scoring

When generating a cover letter, the system:

1. Embeds the job description → gets a vector
2. Embeds each stored experience → stored vectors
3. Computes a score per experience:

```
score = (semantic_similarity × 0.5)
      + (recency_weight      × 0.3)
      + (outcome_weight      × 0.2)
```

**Semantic similarity**: cosine similarity between JD embedding and experience embedding.

**Recency weight**: exponential decay — recent experiences score higher.
```
recency = e^(-λ × months_ago)
```
λ controls decay speed. Starting value: λ = 0.05 (a 12-month-old experience retains ~55% of a fresh one's weight; 24-month-old retains ~30%).

**Outcome weight**: did this experience, when used previously, correlate with getting an interview?
- `interview_led_to: true` → weight boost
- `interview_led_to: false` → weight penalty
- No data yet → neutral

Top 3–5 experiences are passed to the cover letter generator.

## Storage Implementation

### Why ChromaDB

Three options were evaluated:

| | ChromaDB | Raw SQLite + embeddings API | Mem0 (hosted) |
|--|---------|----------------------------|---------------|
| Runs locally | ✅ | ✅ | ❌ (data leaves machine) |
| Embedding infrastructure | Built in | Manual | Built in |
| Semantic search | Built in | Manual (cosine) | Built in |
| Custom scoring formula | ✅ wrapper | ✅ native | ❌ limited |
| Outcome feedback loop | ✅ via metadata | ✅ via column | ❌ |
| Deduplication | ✅ | Manual | ✅ |
| External API dependency | Optional | Required (embeddings) | Required |
| Phase 3 migration path | Swap to Mem0 or Vectorize | Rewrite | Already hosted |

**ChromaDB** wins for Phase 2: runs in-process (no server), handles embeddings natively, supports rich metadata filtering, and keeps all data local. The custom scoring wrapper is small — ChromaDB handles similarity, Python handles recency + outcome weighting on top.

### Phase 2 (local) — ChromaDB

```
memory/
  chroma/         — ChromaDB persisted storage (gitignored)
  store.py        — add/update an experience
  query.py        — retrieve top-k for a given JD string
  feedback.py     — record interview outcome, update metadata
```

Each experience is stored as a ChromaDB document:

```python
collection.add(
    ids=["hackathon-cu-2024"],
    documents=["refined narrative text — what gets embedded"],
    metadatas=[{
        "date": "2024-03",          # YYYY-MM — for recency decay
        "type": "achievement",
        "source": "academic",
        "title": "Won CU Boulder Hackathon 2024",
        "raw": "We had 24 hours...",
        "themes": "leadership,time-pressure,problem-solving,teamwork",
        "impact": "1st place, 40 teams",
        "relevance_signals": "fast-paced,cross-functional,shipping under pressure",
        "used_in": "Ramp",          # comma-separated, updated on use
        "interview_led_to": -1,     # -1=unknown, 1=yes, 0=no
    }]
)
```

Note: ChromaDB metadata values must be strings, ints, or floats — arrays are stored as comma-separated strings and parsed on retrieval.

### Scoring wrapper (`query.py`)

ChromaDB returns semantic similarity scores. The wrapper applies recency and outcome weighting on top:

```python
import math
from datetime import datetime

def score(similarity, metadata):
    # Recency: exponential decay, λ=0.05
    months_ago = months_between(metadata["date"], datetime.now())
    recency = math.exp(-0.05 * months_ago)

    # Outcome: boost/penalise based on interview feedback
    outcome_map = {1: 1.0, 0: 0.5, -1: 0.75}  # yes/no/unknown
    outcome = outcome_map[metadata["interview_led_to"]]

    return (similarity * 0.5) + (recency * 0.3) + (outcome * 0.2)
```

Query flow:
1. ChromaDB returns top-20 by semantic similarity
2. Python re-ranks by full score formula
3. Returns top 3–5 to the cover letter skill

### Embeddings

ChromaDB's default embedding function (`all-MiniLM-L6-v2`) runs locally via `sentence-transformers` — no API key needed. This is the zero-dependency path.

If you want higher quality embeddings and have an OpenAI key, swap to `OpenAIEmbeddingFunction` with `text-embedding-3-small` — one line change in `store.py`.

### Phase 3 (cloud, if moving to Moltworker)

Swap ChromaDB for **Mem0** (hosted) or **Cloudflare Vectorize**. The `store.py` / `query.py` interface stays the same — only the backend changes. The custom scoring wrapper is portable regardless of backend.

## Dependencies

```
chromadb
sentence-transformers   # for local embeddings (pulls ~90MB model on first run)
```

Or with OpenAI embeddings:
```
chromadb
openai
```

## Multi-modal Input (Future)

- PDFs: extract text, store as `raw`
- Images: describe with Claude vision, store description as `raw`
- No schema changes needed — `raw` can hold extracted text from any source
