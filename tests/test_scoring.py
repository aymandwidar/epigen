"""Tests for the retrieval scoring function (the core of the demo)."""

import inspect
from datetime import datetime, timezone

from app.embeddings import cosine, embed
from app.retrieval import (
    approx_tokens,
    build_epigen_prompt,
    extract_citations,
    group_by_angle,
    recency_decay,
    retrieve,
    score_memory,
)

NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)


def _mem(text, created_at="2026-10-01T12:00:00+00:00", salience=0.8,
         angle="shopping", mid="mem_shopping_001", emb=None):
    return {
        "id": mid,
        "angle": angle,
        "text": text,
        "created_at": created_at,
        "salience": salience,
        "source": "manual",
        "embedding": emb if emb is not None else embed(text),
    }


def test_cosine_prefers_relevant_memory():
    query = embed("should I buy this winter jacket")
    good = _mem("regretted an expensive winter jacket purchase")
    bad = _mem("grocery list and school supplies budget")
    assert score_memory(query, good, NOW) > score_memory(query, bad, NOW)


def test_recency_decay_orders_old_lower():
    query = embed("jacket purchase regret")
    new = _mem("jacket purchase regret", created_at="2026-10-20T12:00:00+00:00")
    old = _mem("jacket purchase regret", created_at="2026-05-01T12:00:00+00:00")
    assert recency_decay(new["created_at"], NOW) > recency_decay(
        old["created_at"], NOW)
    assert score_memory(query, new, NOW) > score_memory(query, old, NOW)


def test_salience_weights_otherwise_equal():
    query = embed("jacket purchase regret")
    hi = _mem("jacket purchase regret", salience=0.95)
    lo = _mem("jacket purchase regret", salience=0.20)
    assert score_memory(query, hi, NOW) > score_memory(query, lo, NOW)


def test_score_is_cosine_times_recency_times_salience():
    emb = [1.0, 0.0, 0.0]
    mem = _mem("x", salience=0.5, emb=emb)
    expected = max(0.0, cosine(emb, emb)) * recency_decay(
        mem["created_at"], NOW) * 0.5
    assert score_memory(emb, mem, NOW) == expected


def test_retrieve_takes_top_k_within_token_budget():
    mems = [_mem(f"jacket purchase number {i} regret return",
                 mid=f"mem_shopping_{i:03d}") for i in range(20)]
    got = retrieve("jacket", "", mems, top_k=8, token_budget=10**9, now=NOW)
    assert len(got) == 8
    tiny = retrieve("jacket", "", mems, top_k=8, token_budget=5, now=NOW)
    assert len(tiny) < 8
    assert sum(approx_tokens(m["text"]) for m in tiny) <= 5


def test_retrieve_does_not_route_by_angle():
    mems = [
        _mem("apartment savings deposit fund goal", angle="family",
             mid="mem_family_001"),
        _mem("jacket sweater sale return regret", angle="shopping",
             mid="mem_shopping_001"),
    ]
    got = retrieve("savings apartment jacket budget", "", mems, top_k=8,
                   token_budget=10**9, now=NOW)
    assert {m["angle"] for m in got} == {"shopping", "family"}
    sig = inspect.signature(retrieve)
    assert "angle" not in sig.parameters


def test_group_by_angle_and_prompt_tagging():
    mems = [
        _mem("jacket regret", angle="shopping", mid="mem_shopping_001"),
        _mem("apartment fund", angle="family", mid="mem_family_001"),
    ]
    grouped = group_by_angle(mems)
    assert set(grouped) == {"shopping", "family"}
    prompt = build_epigen_prompt("Should I buy this?", "", mems)
    developer = prompt[0]["content"]
    assert "[mem_shopping_001]" in developer
    assert "[mem_family_001]" in developer
    assert "cite" in developer.lower()
    assert "no memory supports" in developer.lower()


def test_extract_citations():
    answer = "Pass [mem_shopping_011] and keep saving [mem_family_003]."
    assert extract_citations(answer) == ["mem_shopping_011", "mem_family_003"]
    assert extract_citations("no citations here") == []
