"""Tests for the /api/ask response shape (decision JSON, map, citations)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app, parse_epigen_json
from app.store import connect as store_connect
from scripts.seed import main as seed_main


def _client(tmp_path):
    db = str(tmp_path / "ask.db")
    seed_main(db)
    main_module.connect = lambda: store_connect(db)
    return TestClient(app)


def test_parse_epigen_json():
    assert parse_epigen_json("just text") is None
    assert parse_epigen_json('{"nope": 1}') is None
    obj = parse_epigen_json('```json\n{"answer": "hi"}\n```')
    assert obj == {"answer": "hi"}


def _ask(client):
    with open("demo/jacket.png", "rb") as f:
        return client.post(
            "/api/ask",
            data={"question": "Should I buy this $180 jacket?"},
            files={"photo": ("jacket.png", f, "image/png")},
        ).json()


def test_ask_shape(tmp_path):
    j = _ask(_client(tmp_path))
    assert set(["plain", "epigen", "epigen_json", "epigen_text",
                "photo_description", "cited", "grouped", "map",
                "demo_mode"]) <= set(j)
    ej = j["epigen_json"]
    assert ej["decision"] and ej["would_change_if"] and ej["answer"]
    assert len(ej["reasons"]) >= 1
    assert len(j["plain"].split()) <= 120
    assert len(j["epigen_text"].split()) <= 120


def test_cited_come_from_reasons_and_map_marks_top8(tmp_path):
    j = _ask(_client(tmp_path))
    reason_ids = [mid for r in j["epigen_json"]["reasons"]
                  for mid in r["memory_ids"]]
    assert [c["id"] for c in j["cited"]] == list(dict.fromkeys(
        mid for mid in reason_ids
        if mid in {m["id"] for m in j["map"] if m["score"] is not None}))
    lit = [m for m in j["map"] if m["score"] is not None]
    dim = [m for m in j["map"] if m["score"] is None]
    assert len(j["map"]) == 65
    assert len(lit) == 8
    assert len(dim) == 57
    assert {m["angle"] for m in lit} == {"shopping", "family"}


def test_outcome_changes_next_answer(tmp_path):
    client = _client(tmp_path)
    new_id = client.post("/api/outcome", json={
        "outcome": "returned", "item": "the $180 jacket", "price": 180,
    }).json()["memory"]["id"]
    j2 = client.post("/api/ask",
                     data={"question": "Should I buy this $180 jacket?"}).json()
    assert new_id in [c["id"] for c in j2["cited"]]
    assert new_id in json.dumps(j2["epigen_json"])
