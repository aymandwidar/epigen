"""Tests for the Epigen MCP server (stdio tools over the same store)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mcp_server import handle
from scripts.seed import main as seed_main


def _seeded(tmp_path, monkeypatch):
    db = str(tmp_path / "mcp.db")
    seed_main(db)
    monkeypatch.setenv("EPIGEN_DB", db)
    monkeypatch.setenv("EPIGEN_EMBEDDINGS", "hashed")


def _call(name, args, call_id=1):
    return handle({
        "jsonrpc": "2.0",
        "id": call_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": args},
    })


def test_tools_list(tmp_path, monkeypatch):
    _seeded(tmp_path, monkeypatch)
    resp = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = [t["name"] for t in resp["result"]["tools"]]
    assert names == ["recall", "capture", "log_outcome"]


def test_recall_returns_8_ids(tmp_path, monkeypatch):
    _seeded(tmp_path, monkeypatch)
    resp = _call("recall", {"query": "Should I buy this $180 jacket?", "k": 8})
    mems = json.loads(resp["result"]["content"][0]["text"])
    ids = [m["id"] for m in mems]
    assert len(ids) == 8
    assert len(set(ids)) == 8
    assert all(m["score"] > 0 for m in mems)


def test_capture_and_log_outcome(tmp_path, monkeypatch):
    _seeded(tmp_path, monkeypatch)
    created = json.loads(_call(
        "capture", {"text": "Lily needs new glasses", "angle": "family"}
    )["result"]["content"][0]["text"])
    assert created["id"].startswith("mem_mcp_")
    logged = json.loads(_call(
        "log_outcome", {"memory_id": created["id"], "outcome": "kept"}
    )["result"]["content"][0]["text"])
    assert logged["re"] == created["id"]
    bad = _call("log_outcome", {"memory_id": "mem_nope_000",
                                "outcome": "kept"})
    assert "error" in bad
