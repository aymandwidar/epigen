"""Epigen FastAPI app: one page, two answers, memory citations."""

import asyncio
import json
import logging
import os
import re

log = logging.getLogger(__name__)

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import meta_api
from .embeddings import embed, embedding_dim
from .retrieval import (
    build_epigen_prompt,
    extract_citations,
    group_by_angle,
    retrieve,
)
from .store import connect, load_memories, save_memory, utcnow_iso

app = FastAPI(title="Epigen")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "demo_mode": not meta_api.has_key()}


@app.get("/api/memories")
def list_memories():
    """All memories for the memory map; scores arrive via /api/ask."""
    conn = connect()
    try:
        memories = load_memories(conn)
    finally:
        conn.close()
    return {
        "count": len(memories),
        "memories": [
            {"id": m["id"], "angle": m["angle"], "text": m["text"]}
            for m in memories
        ],
    }


TRIM_WORDS = 130  # same server-side cap for Plain and Epigen answers


def trim_to_words(text: str, limit: int = TRIM_WORDS) -> str:
    """Trim to ~limit words at a sentence boundary."""
    words = text.split()
    if len(words) <= limit:
        return text
    kept: list[str] = []
    count = 0
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        n = len(sentence.split())
        if count + n > limit:
            break
        kept.append(sentence)
        count += n
    if not kept:
        return " ".join(words[:limit]).rstrip(",;:") + "…"
    return " ".join(kept)


def _error_result(msg: str) -> dict:
    return {
        "plain": msg,
        "epigen": msg,
        "epigen_json": None,
        "epigen_text": msg,
        "photo_description": "",
        "cited": [],
        "grouped": {},
        "map": [],
        "demo_mode": not meta_api.has_key(),
    }


@app.post("/api/ask")
async def ask(
    question: str = Form("Should I buy this?"),
    photo: UploadFile | None = File(default=None),
):
    try:
        return await _run_ask(question, photo)
    except Exception as exc:
        # Never leave a column blank; key material is never logged.
        log.exception("/api/ask failed")
        return _error_result(
            f"Something went wrong ({exc}). Please try again."
        )


async def _run_ask(question: str, photo: UploadFile | None):
    conn = connect()
    memories = load_memories(conn)
    conn.close()
    qdim = embedding_dim()
    stale = [m["id"] for m in memories if len(m["embedding"]) != qdim]
    if stale:
        log.warning(
            "dropping %d memories with stale embedding dim "
            "(re-seed after switching EPIGEN_EMBEDDINGS): %s",
            len(stale), stale[:8],
        )
        memories = [m for m in memories if len(m["embedding"]) == qdim]

    photo_description = ""
    filename = ""
    if photo is not None and photo.filename:
        filename = photo.filename
        image_bytes = await photo.read()
        mime = photo.content_type or "image/png"
        if meta_api.has_key():
            try:
                photo_description = meta_api.describe_photo(image_bytes, mime)
            except Exception as exc:
                photo_description = (
                    f"Photo {filename} could not be described ({exc})."
                )
        else:
            photo_description = meta_api.stub_photo_description(filename)

    retrieved = retrieve(question, photo_description, memories)
    prompt = build_epigen_prompt(question, photo_description, retrieved)

    async def _plain() -> str:
        try:
            if meta_api.has_key():
                return await asyncio.to_thread(
                    meta_api.plain_answer, question, photo_description
                )
            return meta_api.stub_plain(question, photo_description)
        except Exception as exc:
            return f"Plain Muse unavailable: {exc}"

    async def _epigen() -> str:
        try:
            if meta_api.has_key():
                return await asyncio.to_thread(meta_api.epigen_answer, prompt)
            return meta_api.stub_epigen(question, retrieved)
        except Exception as exc:
            return f"Epigen unavailable: {exc}"

    plain, epigen_text = await asyncio.gather(_plain(), _epigen())

    plain = trim_to_words(plain)

    epigen_json = parse_epigen_json(epigen_text)
    by_id = {m["id"]: m for m in retrieved}
    if epigen_json is not None:
        validate_citations(epigen_json, set(by_id))
    if epigen_json is not None:
        cited_ids = [
            mid
            for r in epigen_json.get("reasons", [])
            if isinstance(r, dict)
            for mid in r.get("memory_ids", [])
        ]
    else:
        cited_ids = extract_citations(epigen_text)
    seen: set[str] = set()
    cited = []
    for cid in cited_ids:
        if cid in by_id and cid not in seen:
            seen.add(cid)
            cited.append(
                {
                    "id": cid,
                    "angle": by_id[cid]["angle"],
                    "score": round(by_id[cid]["score"], 4),
                    "text": by_id[cid]["text"],
                }
            )
    if not cited:
        cited = [
            {
                "id": m["id"],
                "angle": m["angle"],
                "score": round(m["score"], 4),
                "text": m["text"],
            }
            for m in retrieved
        ]

    epigen_text_out = trim_to_words(
        epigen_json.get("answer", epigen_text)
        if epigen_json is not None else epigen_text
    )
    memory_map = [
        {
            "id": m["id"],
            "angle": m["angle"],
            "text": m["text"],
            "score": round(by_id[m["id"]]["score"], 4)
            if m["id"] in by_id else None,
        }
        for m in memories
    ]

    return {
        "plain": plain,
        "epigen": epigen_text,
        "epigen_json": epigen_json,
        "epigen_text": epigen_text_out,
        "photo_description": photo_description,
        "cited": cited,
        "grouped": {
            angle: [m["id"] for m in ms]
            for angle, ms in group_by_angle(retrieved).items()
        },
        "map": memory_map,
        "demo_mode": not meta_api.has_key(),
    }


def validate_citations(epigen_json: dict, valid_ids: set[str]) -> list[str]:
    """Keep only memory_ids retrieved for this request.

    Drops invented ids from reasons (and therefore chips), logs a warning
    naming them, and marks reasons left with no valid ids "(no memory cited)".
    Returns the dropped ids.
    """
    dropped: list[str] = []
    for reason in epigen_json.get("reasons", []):
        if not isinstance(reason, dict):
            continue
        keep: list[str] = []
        for mid in reason.get("memory_ids", []):
            if mid in valid_ids:
                if mid not in keep:
                    keep.append(mid)
            elif mid not in dropped:
                dropped.append(mid)
        reason["memory_ids"] = keep
        text = str(reason.get("text") or "")
        if not keep and "(no memory cited)" not in text:
            reason["text"] = (text + " (no memory cited)").strip()
    if dropped:
        log.warning("Epigen cited unknown memories, dropped: %s", dropped)
    return dropped


def parse_epigen_json(text: str) -> dict | None:
    """Parse the Epigen JSON reply; None when it is plain text (fallback).

    Tolerates ```json fences and prose around the object: the first {...}
    block is decoded, missing fields get safe defaults, and only a reply
    with no usable "answer" falls back to plain text.
    """
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    obj = None
    try:
        obj = json.loads(t)
    except (json.JSONDecodeError, ValueError):
        pass
    if not isinstance(obj, dict):
        start = t.find("{")
        if start < 0:
            return None
        try:
            obj, _ = json.JSONDecoder().raw_decode(t[start:])
        except (json.JSONDecodeError, ValueError):
            return None
    if not isinstance(obj, dict):
        return None
    answer = obj.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return None
    reasons = obj.get("reasons")
    if not isinstance(reasons, list):
        reasons = []
    return {
        "decision": str(obj.get("decision") or ""),
        "reasons": [
            {
                "text": str(r.get("text") or ""),
                "memory_ids": [m for m in r.get("memory_ids", [])
                               if isinstance(m, str)],
            }
            for r in reasons
            if isinstance(r, dict)
        ],
        "would_change_if": str(obj.get("would_change_if") or ""),
        "answer": answer,
    }


@app.post("/api/outcome")
async def log_outcome(payload: dict):
    """Log an outcome (kept/returned/regretted) as a new memory."""
    outcome = str(payload.get("outcome", "")).lower()
    if outcome not in ("kept", "returned", "regretted", "loved"):
        return JSONResponse(
            {"error": "outcome must be kept, returned, regretted, or loved"},
            status_code=400,
        )
    item = str(payload.get("item", "the jacket"))
    price = payload.get("price", "")
    price_txt = f" (${price})" if price else ""
    note = str(payload.get("note", "")).strip()
    text = f"{outcome.capitalize()} {item}{price_txt}."
    if note:
        text += f" Note: {note}"
    conn = connect()
    existing = load_memories(conn)
    n = len(existing)
    mem = {
        "id": f"mem_outcome_{n + 1:03d}",
        "angle": "shopping",
        "text": text,
        "created_at": utcnow_iso(),
        "salience": 0.9,
        "source": "outcome",
        "embedding": embed(text),
    }
    save_memory(conn, mem)
    conn.commit()
    conn.close()
    return {"ok": True, "memory": {k: mem[k] for k in ("id", "angle", "text")}}
