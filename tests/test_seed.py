"""Tests for the seed script: one invented person, Sam Rivera."""

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.seed import FAMILY, SHOPPING, build_memories, main

PRICE_RE = re.compile(r"\$(\d[\d,]*)")


def _prices(text):
    return [int(p.replace(",", "")) for p in PRICE_RE.findall(text)]


def test_counts():
    assert len(SHOPPING) == 40
    assert len(FAMILY) == 25
    assert len(build_memories()) == 65


def test_memory_schema():
    for mem in build_memories():
        assert set(mem) == {"id", "angle", "text", "created_at",
                            "salience", "source", "embedding"}
        assert mem["angle"] in ("shopping", "family")
        assert 0.0 <= mem["salience"] <= 1.0
        assert mem["source"] in ("manual", "photo", "outcome")
        norm = math.sqrt(sum(v * v for v in mem["embedding"]))
        assert norm > 0.9, mem["id"]


def test_ids_unique_and_prefixed():
    ids = [m["id"] for m in build_memories()]
    assert len(set(ids)) == len(ids)
    for m in build_memories():
        assert m["id"].startswith(f"mem_{m['angle']}_")


def test_clothing_over_150_regret_pattern():
    hits = [t for _, _, _, _, t in SHOPPING
            if any(p > 150 for p in _prices(t))
            and ("egrett" in t or "eturned" in t)
            and "clothing" in t]
    assert len(hits) >= 4


def test_budget_rules_brands_and_outcomes():
    texts = [t for _, _, _, _, t in SHOPPING]
    assert any("budget" in t for t in texts)
    assert any("Patagonia" in t for t in texts)
    assert any("Muji" in t for t in texts)
    for outcome in ("Kept", "Returned", "Regretted", "Loved"):
        assert any(outcome in t for t in texts), outcome


def test_family_goal_preferences_and_kid_costs():
    texts = [t for _, _, _, _, t in FAMILY]
    blob = "\n".join(texts)
    assert "$15,000" in blob
    assert "September 2027" in blob
    assert "Alex" in blob
    assert "Lily" in blob


def test_seed_roundtrip(tmp_path):
    db = str(tmp_path / "test.db")
    main(db)
    import sqlite3

    conn = sqlite3.connect(db)
    n = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    angles = sorted(r[0] for r in
                    conn.execute("SELECT DISTINCT angle FROM memories"))
    conn.close()
    assert n == 65
    assert angles == ["family", "shopping"]
