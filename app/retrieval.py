"""Retrieval: the core of the demo.

1. Embed the question plus the photo description.
2. Score every memory: cosine similarity x recency decay x salience.
   No routing by angle with a classifier — every memory competes.
3. Take the top 8 within a token budget, grouped by angle.
4. Build the prompt with those memories, each tagged with its id.
   The model must cite memory ids for every personal claim and say
   so when no memory supports a claim.
"""

import math
import re
from datetime import datetime, timezone

from .embeddings import cosine, embed

TOP_K = 8
TOKEN_BUDGET = 2000  # tokens reserved for memories in the prompt
RECENCY_HALF_LIFE_DAYS = 90.0
CITATION_RE = re.compile(r"\[(mem_[a-z]+_\d+)\]")


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def recency_decay(created_at: str, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    age_days = max(0.0, (now - _parse_dt(created_at)).total_seconds() / 86400.0)
    return math.exp(-age_days / RECENCY_HALF_LIFE_DAYS)


def score_memory(
    query_emb: list[float], mem: dict, now: datetime | None = None
) -> float:
    sim = max(0.0, cosine(query_emb, mem["embedding"]))
    return sim * recency_decay(mem["created_at"], now) * float(mem["salience"])


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def retrieve(
    question: str,
    photo_description: str = "",
    memories: list[dict] | None = None,
    top_k: int = TOP_K,
    token_budget: int = TOKEN_BUDGET,
    now: datetime | None = None,
) -> list[dict]:
    """Score ALL memories (no angle routing) and return the top_k in budget."""
    memories = memories or []
    query_text = question if not photo_description else (
        f"{question}\nPhoto: {photo_description}"
    )
    query_emb = embed(query_text)
    scored = [
        {**mem, "score": score_memory(query_emb, mem, now)} for mem in memories
    ]
    scored.sort(key=lambda m: m["score"], reverse=True)
    picked: list[dict] = []
    used = 0
    for mem in scored:
        if len(picked) >= top_k:
            break
        cost = approx_tokens(mem["text"])
        if used + cost > token_budget:
            continue
        used += cost
        picked.append(mem)
    return picked


def group_by_angle(mems: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for mem in mems:
        grouped.setdefault(mem["angle"], []).append(mem)
    return grouped


def build_epigen_prompt(
    question: str, photo_description: str, mems: list[dict]
) -> list[dict]:
    lines = []
    for mem in mems:
        lines.append(
            f"[{mem['id']}] (angle={mem['angle']}, date={mem['created_at'][:10]},"
            f" score={mem.get('score', 0.0):.3f}): {mem['text']}"
        )
    memories_block = (
        "\n".join(lines) if lines else "(no memories retrieved)"
    )
    developer = (
        "You are Epigen, a personal memory layer. Answer the user's question"
        " using their memories below. Rules:\n"
        "1. Every personal claim in your answer MUST cite the memory id(s)"
        " it comes from, e.g. [mem_shopping_003].\n"
        "2. If no memory supports a claim, say so explicitly"
        " (\"no memory supports this\").\n"
        "3. Never invent personal facts not present in the memories.\n"
        "\nMemories:\n" + memories_block
    )
    user = question if not photo_description else (
        f"{question}\n\nPhoto description: {photo_description}"
    )
    return [
        {"role": "developer", "content": developer},
        {"role": "user", "content": user},
    ]


def extract_citations(answer: str) -> list[str]:
    seen: list[str] = []
    for m in CITATION_RE.findall(answer):
        if m not in seen:
            seen.append(m)
    return seen
