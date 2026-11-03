# Epigen demo script — 3 minutes, one screen recording

Reset before every take: `.venv/bin/python scripts/reset_demo.py`
Start: `.venv/bin/python -m uvicorn app.main:app`, open http://localhost:8000.

## 0:00–0:30 — The problem (show the empty question box)

Say: *"Every AI gives the same answer to everyone. Ask five apps 'Should I buy
this?' and you get five versions of generic advice — because none of them know
you. Epigen is a personal memory layer: your own history, retrieved by
relevance, cited in the answer."*

## 0:30–1:10 — The $180 jacket (upload + ask)

1. Click **Choose File**, select `demo/jacket.png`.
2. Question is prefilled: `Should I buy this $180 jacket?` Click **Ask both**.

Say: *"Plain Muse on the left gives decent generic advice — check the fit,
compare prices, sleep on it. It knows nothing about me. Epigen on the right
says pass — and look at why."*

3. Scroll to **Cited memories**. Point at a shopping citation, then a family one.

Say: *"It cites my own history: I regretted the $189 denim jacket and returned
the $175 corduroy — a pattern of regretting clothing over $150 — AND it pulls
a family angle: I'm saving for an apartment with my partner, so $180 competes
with that goal. Two life domains, one answer, every claim cited."*

## 1:10–2:00 — Log outcome, ask again (the memory layer learns)

1. Click **Returned**.
2. Read the confirmation: *"Saved mem_outcome_066 — ask again to see the change."*
3. Click **Ask both** again. Point at the new `[mem_outcome_066]` citation at
   the top of the Epigen answer.

Say: *"I logged the outcome — returned. That just became a memory, and the
next answer leads with it. The system learns from what actually happened, not
just what I said I'd do."*

## 2:00–2:40 — The close (vision)

Say: *"That's the whole idea, and the biology metaphor is deliberate — like
epigenetics, every memory is stored, but only the relevant ones get expressed
in each answer. Today it's shopping and family. Tomorrow it's your doctor
saying 'is this normal for me?', your code reviewer knowing your past bugs,
your advisor knowing your real budget. The model stays general. The memory
gets personal. That's Epigen."*

## Backup lines (if something misbehaves live)

- No API key: *"Running in demo mode with the same retrieval and citations —
  plug in MODEL_API_KEY for live Muse Spark answers."*
- Wrong retrieval: *"Scores are cosine similarity times recency times
  salience — recent, important, relevant memories win."*
