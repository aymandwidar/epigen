"""Epigen MCP server (stdio, dependency-free).

Exposes the same SQLite store and retrieval to other AI tools:

- recall(query, k=8): top-k memories for a question, with scores.
- capture(text, angle): save a new manual memory, returns its id.
- log_outcome(memory_id, outcome): record kept/returned/regretted/loved
  for a memory, saved as a new outcome memory linked to the original.

Speaks newline-delimited JSON-RPC on stdin/stdout. No handshake required,
so `echo '<request>' | python app/mcp_server.py` works for a quick check.
No new cloud services; everything stays in the local SQLite database.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.embeddings import embed  # noqa: E402
from app.retrieval import retrieve  # noqa: E402
from app.store import connect, load_memories, save_memory, utcnow_iso  # noqa: E402
import app.store as store  # noqa: E402

SERVER_INFO = {"name": "epigen", "version": "0.1.0"}
VALID_OUTCOMES = ("kept", "returned", "regretted", "loved")

TOOLS = [
    {
        "name": "recall",
        "description": "Retrieve the top-k memories relevant to a question.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 8},
            },
            "required": ["query"],
        },
    },
    {
        "name": "capture",
        "description": "Save a new memory with free text and an angle.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "angle": {"type": "string"},
            },
            "required": ["text", "angle"],
        },
    },
    {
        "name": "log_outcome",
        "description": "Record kept/returned/regretted/loved for a memory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memory_id": {"type": "string"},
                "outcome": {"type": "string"},
            },
            "required": ["memory_id", "outcome"],
        },
    },
]


def _db_path() -> str:
    return os.environ.get("EPIGEN_DB", store.DB_PATH)


def tool_recall(query: str, k: int = 8) -> list[dict]:
    conn = connect(_db_path())
    try:
        memories = load_memories(conn)
    finally:
        conn.close()
    return [
        {
            "id": m["id"],
            "angle": m["angle"],
            "score": round(m["score"], 4),
            "text": m["text"],
        }
        for m in retrieve(query, "", memories, top_k=int(k))
    ]


def tool_capture(text: str, angle: str) -> dict:
    text, angle = text.strip(), angle.strip()
    if not text:
        raise ValueError("text must not be empty")
    if not angle:
        raise ValueError("angle must not be empty")
    conn = connect(_db_path())
    try:
        n = len(load_memories(conn))
        mem_id = f"mem_mcp_{n + 1:03d}"
        while conn.execute(
            "SELECT 1 FROM memories WHERE id = ?", (mem_id,)
        ).fetchone():
            n += 1
            mem_id = f"mem_mcp_{n + 1:03d}"
        mem = {
            "id": mem_id,
            "angle": angle,
            "text": text,
            "created_at": utcnow_iso(),
            "salience": 0.7,
            "source": "manual",
            "embedding": embed(text),
        }
        save_memory(conn, mem)
        conn.commit()
    finally:
        conn.close()
    return {"id": mem_id, "angle": angle, "text": text}


def tool_log_outcome(memory_id: str, outcome: str) -> dict:
    outcome = str(outcome).lower()
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {VALID_OUTCOMES}")
    conn = connect(_db_path())
    try:
        mems = load_memories(conn)
        ref = next((m for m in mems if m["id"] == memory_id), None)
        if ref is None:
            raise ValueError(f"unknown memory_id: {memory_id}")
        mem_id = f"mem_outcome_{len(mems) + 1:03d}"
        mem = {
            "id": mem_id,
            "angle": ref["angle"],
            "text": f"{outcome.capitalize()} (re {memory_id}): {ref['text']}",
            "created_at": utcnow_iso(),
            "salience": 0.9,
            "source": "outcome",
            "embedding": embed(
                f"{outcome} {ref['text']}"),
        }
        save_memory(conn, mem)
        conn.commit()
    finally:
        conn.close()
    return {"id": mem_id, "re": memory_id, "outcome": outcome}


def handle(request: object) -> dict | None:
    if not isinstance(request, dict):
        return _error(None, -32600, "invalid request")
    req_id = request.get("id")
    method = request.get("method")
    if method is None:
        return None  # notification; no reply
    params = request.get("params") or {}
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            if name == "recall":
                result = {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(tool_recall(
                            args.get("query", ""),
                            int(args.get("k", 8))))}],
                }
            elif name == "capture":
                result = {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(tool_capture(
                            args.get("text", ""), args.get("angle", "")))}],
                }
            elif name == "log_outcome":
                result = {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(tool_log_outcome(
                            args.get("memory_id", ""),
                            args.get("outcome", "")))}],
                }
            else:
                return _error(req_id, -32602, f"unknown tool: {name}")
        else:
            return _error(req_id, -32601, f"unknown method: {method}")
    except (ValueError, KeyError) as exc:
        return _error(req_id, -32602, str(exc))
    except Exception as exc:  # never leak internals details beyond a message
        return _error(req_id, -32603, f"{type(exc).__name__}: {exc}")
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(
                _error(None, -32700, "parse error")) + "\n")
            sys.stdout.flush()
            continue
        response = handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
