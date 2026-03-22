# Plan 03 — Experience Capture Skill

## Purpose

A conversational skill that captures life experiences on the fly — while applying to a job, or any time you remember something worth storing. Accessible via Telegram so you never need to open a laptop to add to your memory store.

## The Core Problem It Solves

Right now: you remember a relevant experience → you type it manually into every prompt → it's forgotten after the session.

With this skill: you describe it once → the system asks follow-up questions → stores it with full context → it surfaces automatically next time a relevant JD comes in.

## Trigger Phrases

The skill activates when the user says:
- "Remember this..."
- "Add this to my memory..."
- "I just thought of something..."
- "Oh — also, when I was at [company/school]..."

Also available as an explicit command: `/capture` or `/remember`.

## The Conversation Flow

The goal is to feel like talking to someone genuinely curious — not filling out a form. Questions should extract a STAR structure (Situation, Task, Action, Result) without ever using those words.

### Example — Achievement

```
You: "Remember this — I won a hackathon at CU last year"

Bot: "Nice. What were you building, and was this solo or a team?"

You: "Team of 4. We built a food waste app for dining halls."

Bot: "What was your specific role — leading, building, pitching, all of it?"

You: "I led the team and did most of the backend."

Bot: "How many teams were you competing against, and was winning
     expected or a surprise?"

You: "40 teams. Total surprise — we almost gave up at 3am."

Bot: "That '3am almost gave up' moment is worth keeping.
     What pulled you through it?"

You: "We cut half the features and focused on making one thing work really well."

Bot: "Got it. What did you take away from that night that you
     couldn't have learned in a classroom?"

You: "Ruthless scoping beats trying to do everything."

Bot: "Saved. [shows refined summary]
     Want me to include this in the Stripe cover letter I'm working on?"
```

### Example — Mentorship / Challenge

```
You: "Add this — I had a really hard performance review conversation
     with a junior dev I was informally mentoring"

Bot: "What made it hard — the feedback itself, or the dynamic between you?"

You: "Both. He wasn't meeting expectations and I had to be honest
     without making him feel like a failure."

Bot: "How did you approach it? Did you plan it out or go in raw?"

You: "I planned it. Wrote down specific examples so it wasn't vague."

Bot: "How did he respond, and what happened after?"

You: "Defensive at first, but came around. Got promoted 6 months later."

Bot: "Saved. This sits well under mentorship and leadership themes.
     Any company you've used this story for before?"
```

## Follow-up Question Strategy

Questions are designed to surface:

1. **Specificity** — numbers, team sizes, time frames, outcomes
2. **The human detail** — the "3am almost gave up" moment, the emotional texture
3. **The lesson or principle** — what you'd take into a new job
4. **What you specifically did** vs. what the team did

Questions to avoid: "Can you describe the situation?" (too open), "What was the result?" (too formulaic).

## Detecting Multiple Experiences

If the user describes more than one experience in a session, detect the shift:

- New time reference ("Also, back in 2023...")
- New setting ("At work there was this time...")
- Explicit signal ("One more thing...")
- Topic clearly unrelated to the previous one

When detected: finish and confirm the current one, then start fresh.

## Output: What Gets Stored

After follow-ups, the skill:

1. Constructs the structured entry (see `plans/02-memory-store.md` for schema)
2. Infers: `type`, `source`, `themes`, `relevance_signals` from conversation
3. Stores `raw` (your words verbatim) and `refined` (structured narrative)
4. Generates an embedding and stores it
5. Shows you the refined summary for a quick sanity check
6. Asks if you want it included in any currently open application

## What the Skill Does NOT Do

- Does not invent details you didn't provide
- Does not rephrase in corporate-speak — uses your voice
- Does not require you to categorize the experience yourself
- Does not interrupt the application flow — capture and apply are parallel

## Skill Location

`cover-letter-skill/.claude/commands/capture-experience.md`

## Implementation Notes

After the conversational capture phase, the skill calls `memory/embed.py` to generate the embedding and insert into `experiences.db`. Returns the `id` of the stored experience so it can be injected into `generate-cover-letter` in the same session.

## Future: Multi-modal Capture

- Photo (certificate, whiteboard) → Claude vision describes it → stored as `raw`
- PDF (award letter) → text extracted → same flow
- Telegram already supports receiving images and documents — no UI change needed
