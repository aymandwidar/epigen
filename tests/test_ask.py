"""Tests for the /api/ask response shape (decision JSON, map, citations)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app, parse_epigen_json, validate_citations
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
    assert obj["answer"] == "hi"
    assert obj["decision"] == "" and obj["reasons"] == []


def test_parse_epigen_json_fenced_and_prose_prefixed():
    body = ('{"decision": "Pass.", "reasons": [{"text": "r", '
            '"memory_ids": ["mem_shopping_040", 7]}], "answer": "Pass [mem_shopping_040]."}')
    fenced = parse_epigen_json("```json\n" + body + "\n```")
    assert fenced["decision"] == "Pass."
    assert fenced["reasons"] == [{"text": "r",
                                 "memory_ids": ["mem_shopping_040"]}]
    assert fenced["would_change_if"] == ""
    wrapped = parse_epigen_json("Here is my verdict:\n" + body +
                                "\nHope this helps!")
    assert wrapped == fenced
    sparse = parse_epigen_json('{"answer": "ok"}')
    assert sparse == {"decision": "", "reasons": [],
                      "would_change_if": "", "answer": "ok"}
    assert parse_epigen_json("no braces at all") is None


def test_validate_citations_drops_invented_ids(caplog):
    import logging

    obj = {
        "decision": "Pass.",
        "reasons": [
            {"text": "Jackets over $150 get returned",
             "memory_ids": ["mem_shopping_029", "mem_shopping_999"]},
            {"text": "Made-up reason", "memory_ids": ["mem_family_404"]},
        ],
        "would_change_if": "",
        "answer": "Pass.",
    }
    with caplog.at_level(logging.WARNING, logger="app.main"):
        dropped = validate_citations(obj, {"mem_shopping_029"})
    assert dropped == ["mem_shopping_999", "mem_family_404"]
    assert any("mem_shopping_999" in r.message and "mem_family_404" in r.message
               for r in caplog.records)
    assert obj["reasons"][0] == {
        "text": "Jackets over $150 get returned",
        "memory_ids": ["mem_shopping_029"],
    }
    assert obj["reasons"][1]["memory_ids"] == []
    assert obj["reasons"][1]["text"] == "Made-up reason (no memory cited)"


def test_trim_to_words():
    from app.main import trim_to_words

    short = " ".join(["word"] * 50)
    assert trim_to_words(short) == short
    sentences = [" ".join([f"s{i}w{j}" for j in range(10)]) + "."
                 for i in range(20)]
    long_text = " ".join(sentences)
    assert len(long_text.split()) == 200
    trimmed = trim_to_words(long_text)
    assert len(trimmed.split()) <= 130
    assert trimmed.endswith(".")
    assert trimmed.startswith(sentences[0])
    wall = " ".join(["word"] * 200)
    hard = trim_to_words(wall)
    assert len(hard.split()) == 130


def test_ask_error_columns(monkeypatch):
    import app.main as main_module

    def boom():
        raise RuntimeError("db gone")

    monkeypatch.setattr(main_module, "connect", boom)
    j = TestClient(app).post(
        "/api/ask", data={"question": "hi?"}).json()
    assert "db gone" in j["plain"]
    assert "db gone" in j["epigen_text"]
    assert j["cited"] == [] and j["epigen_json"] is None


def test_chat_sets_max_tokens(monkeypatch):
    import sys as _sys
    import types as _types

    import app.meta_api as meta_api

    calls = {}

    class FakeMessage:
        content = "hi"

    class FakeChoice:
        message = FakeMessage()

    class FakeResp:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return FakeResp()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, **kwargs):
            calls["client"] = kwargs

        chat = FakeChat()

    fake = _types.ModuleType("openai")
    fake.OpenAI = FakeClient
    monkeypatch.setitem(_sys.modules, "openai", fake)
    monkeypatch.setenv("MODEL_API_KEY", "test-key-not-real")
    assert meta_api.chat([{"role": "user", "content": "hi"}]) == "hi"
    assert calls["max_tokens"] == 220
    assert calls["model"] == "muse-spark-1.3"


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
