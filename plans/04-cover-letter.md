# Plan 04 — Cover Letter Generation Skill

## Purpose

Generate a tailored, narrative cover letter that draws from the memory store — not just the resume. The output should tell a story a resume can't, pass ATS keyword filters, and require minimal editing.

## The Problem with Current Approach

ChatGPT custom GPT + static resume doc:
- Only knows what's on the resume
- Manually re-entering experiences every time
- Output sounds like a paraphrased resume, not a story
- No memory between sessions

## Design Principles

1. **Story over summary** — answer "why you, specifically" not "here are my qualifications"
2. **ATS first, human second** — keywords from the JD must appear naturally
3. **Verbatim experience narratives** — pulled from memory store, not synthesized
4. **One edit, not a rewrite** — the draft needs light touch-ups, not structural rewrites
5. **Voice consistency** — should sound like you, not generic AI output

## Cover Letter Structure

```
[Opening]
  Why this company specifically — something real, not flattery.
  Reference something concrete (product, mission, recent news).

[Proof of fit — experience 1]
  Top retrieved experience, connected to the role's core requirement.

[Proof of fit — experience 2 or skills bridge]
  Second retrieved experience, or a technical capability that bridges
  your background to the JD's emphasis.

[Personal stake]
  Why this kind of work matters to you — optional but powerful.
  Can draw from a personal/growth type experience in the memory store.

[Closing]
  Brief. No "I look forward to hearing from you."
  One sentence on what you'd bring, one on next steps.
```

## Generation Workflow

### Step 1: Fetch and parse the JD
Same as `generate-resume` — URL via `r.jina.ai` or pasted text.

Extract: company name, role title, core technical requirements, soft skill signals, values/mission language.

### Step 2: Query the memory store

```
score = (semantic_similarity × 0.5)
      + (recency_weight      × 0.3)
      + (outcome_weight      × 0.2)
```

Retrieve top 3–5 experiences. If a specific experience was just captured in the same session, inject it at the top regardless of score.

### Step 3: Read resume context

Read `resume-skill/resume/bank/experience.yaml` and `projects.yaml` — for consistency, not for copying bullets.

### Step 4: Generate the draft

- JD (parsed)
- Resume context (consistency check)
- Top experiences from memory store (refined narratives)
- Tone: conversational but professional, first person, no corporate jargon
- Length: 3–4 paragraphs, under 400 words
- ATS: naturally include key technical terms from the JD

### Step 5: Keyword audit

Verify these appear: role title or variant, 3–5 technical keywords from JD, company name. If missing, regenerate the relevant paragraph — don't bolt keywords on.

### Step 6: Deliver

Send as text in Telegram (not PDF — easier to copy into application forms). Ask:

> "Here's the draft. I used [experience 1] and [experience 2]. Want any changes?"

## Skill Location

`cover-letter-skill/.claude/commands/generate-cover-letter.md`

## Integration with Resume Skill

Default flow when you send a job link:
1. `generate-resume` runs → produces PDF
2. `generate-cover-letter` runs → produces text
3. Both delivered together via Telegram

Either can be run independently.

## ATS vs. Storytelling — Why It's Not a Conflict

ATS scores resumes heavily, cover letters lightly. The cover letter's ATS job is simple: contain the right keywords, avoid formatting that breaks parsing (no tables, multi-column).

The retrieved experiences solve both simultaneously — they're specific (signals authenticity to humans) and keyword-rich by nature (they come from real technical and professional contexts).

## Feedback Loop

After each application, if you hear back:
- "I got an interview at Stripe" → update `interview_led_to` on the experiences used
- This feeds `outcome_weight` in future retrievals
- Over time, the system learns which stories land

Feedback captured via Telegram — skill updates the relevant experience entries automatically.
