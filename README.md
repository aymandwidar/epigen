# Epigen — a personal memory layer for AI

**30-second explanation:** Every AI answers from the same generic knowledge, so "Should I buy this?" gets the same answer for everyone. Epigen stores your own history as memories across life angles (shopping, family…), retrieves the ones relevant to each question, and answers with citations to the exact memories it used. Same question, two answers: Plain Muse knows nothing about you; Epigen knows you regret $150+ jackets and are saving for an apartment.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # add MODEL_API_KEY from https://dev.meta.ai (optional; without it the app runs in labeled DEMO MODE)
.venv/bin/python scripts/seed.py
.venv/bin/python -m uvicorn app.main:app
```

Open [http://localhost:8000](http://localhost:8000) in a browser.

## How it works

1. Upload a photo + ask a question → the photo is described via Muse Spark
   image understanding, the question + description is embedded.
2. Every memory is scored: `cosine similarity × recency decay × salience`.
   No classifier routes by angle — all memories compete, top 8 win within a
   token budget, grouped by angle.
3. The prompt tags each memory with its `[id]` and instructs the model to
   cite ids for every personal claim, and to say when no memory supports one.
4. **Log outcome** (kept / returned / regretted) saves a new memory, so the
   next answer changes.

## Meta Model API (read from dev.meta.ai docs, not guessed)

- Base URL `https://api.meta.ai/v1`, endpoint `POST /v1/chat/completions`
  ([chat completions](https://dev.meta.ai/docs/protocols/chat-completions)).
- Auth: `Authorization: Bearer $MODEL_API_KEY`
  ([authentication](https://dev.meta.ai/docs/authentication)).
- Model `muse-spark-1.3` via the OpenAI SDK:
  `OpenAI(base_url="https://api.meta.ai/v1", api_key=...)`
  ([SDKs](https://dev.meta.ai/docs/sdks)).
- Photo description uses the documented image-understanding path: Chat
  Completions `{"type": "image_url", "image_url": {"url": data URL}}`
  ([image understanding](https://dev.meta.ai/docs/image-understanding)).
  Note: Muse Image *generates/edits* images and SAM *segments* them
  ([image generation](https://dev.meta.ai/docs/image-generation)), so
  describing a photo goes through Muse Spark, not those two.
- The docs list **no embedding endpoint**, so embeddings are a small local
  hashed-token model (`app/embeddings.py`) with vectors in SQLite. No AWS,
  no Bedrock, no other cloud services.

## Project layout

```
app/main.py          FastAPI: /, /api/ask, /api/outcome, /api/health
app/retrieval.py     scoring, top-8 + token budget, prompt + citations
app/meta_api.py      Meta Model API client (+ labeled DEMO MODE stubs)
app/embeddings.py    local deterministic embeddings (no cloud endpoint exists)
app/store.py         SQLite storage
static/index.html    one-page UI (two columns, cited memories, outcome buttons)
scripts/seed.py      Sam Rivera: 40 shopping + 25 family synthetic memories
scripts/reset_demo.py  restore seeded state between takes
scripts/make_demo_image.py  regenerates the old placeholder demo/jacket_drawn.png (stdlib only)
demo/jacket.png      sample $180-jacket photo (demo/jacket.png is an AI-generated product image; no real product, brand, or person)
docs/DEMO.md         3-minute recording script
tests/               scoring + seed tests (15 tests)
```

## Data

All people and history are synthetic (Sam Rivera is invented). Reset anytime:

```bash
.venv/bin/python scripts/reset_demo.py
.venv/bin/python -m pytest -q
```
