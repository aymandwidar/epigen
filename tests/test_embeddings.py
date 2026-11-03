"""Tests for the embedding backends (semantic with hashed fallback)."""

import os
import sys
import types

import app.embeddings as emb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.seed import main as seed_main


def _reset(monkeypatch):
    monkeypatch.setattr(emb, "_model", None)
    monkeypatch.setattr(emb, "_fallback_warned", False)


def test_hashed_backend(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("EPIGEN_EMBEDDINGS", "hashed")
    vec = emb.embed("jacket regret return")
    assert len(vec) == emb.HASHED_DIM
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-6
    assert emb.backend_in_use() == "hashed"


def test_semantic_fallback_to_hashed(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("EPIGEN_EMBEDDINGS", "semantic")
    monkeypatch.setitem(sys.modules, "fastembed", None)
    vec = emb.embed("jacket regret return")
    assert len(vec) == emb.HASHED_DIM
    assert emb.backend_in_use() == "hashed"


def test_semantic_backend_mocked(monkeypatch):
    fake = types.ModuleType("fastembed")
    seen = {}

    class FakeTextEmbedding:
        def __init__(self, **kwargs):
            seen.update(kwargs)

        def embed(self, texts):
            return iter([[0.1] * 384 for _ in texts])

    fake.TextEmbedding = FakeTextEmbedding
    _reset(monkeypatch)
    monkeypatch.setenv("EPIGEN_EMBEDDINGS", "semantic")
    monkeypatch.setitem(sys.modules, "fastembed", fake)
    vec = emb.embed("hello world")
    assert len(vec) == 384
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-6
    assert seen["model_name"] == emb.SEMANTIC_MODEL
    assert seen["cache_dir"] == ".models"
    assert emb.backend_in_use() == "semantic"
    assert emb.embedding_dim() == 384


def test_reseed_works_with_both_backends(monkeypatch, tmp_path):
    _reset(monkeypatch)
    monkeypatch.setenv("EPIGEN_EMBEDDINGS", "hashed")
    mems = seed_main(str(tmp_path / "h.db"))
    assert len(mems) == 65
    assert all(len(m["embedding"]) == emb.HASHED_DIM for m in mems)

    fake = types.ModuleType("fastembed")

    class FakeTextEmbedding:
        def __init__(self, **kwargs):
            pass

        def embed(self, texts):
            return iter([[0.2] * 384 for _ in texts])

    fake.TextEmbedding = FakeTextEmbedding
    _reset(monkeypatch)
    monkeypatch.setenv("EPIGEN_EMBEDDINGS", "semantic")
    monkeypatch.setitem(sys.modules, "fastembed", fake)
    mems = seed_main(str(tmp_path / "s.db"))
    assert len(mems) == 65
    assert all(len(m["embedding"]) == 384 for m in mems)
