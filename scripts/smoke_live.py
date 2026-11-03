"""Manual live-API smoke test. The owner runs this themselves:

    .venv/bin/python scripts/smoke_live.py

Loads .env, then calls describe_photo on demo/jacket.png, plain_answer,
and the Epigen path (retrieve + prompt + answer + parse). For each step
prints: status, seconds, word count, first 300 chars of the raw reply,
and whether the JSON parsed. Errors print type + message.
Never prints the key.
"""

import os
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def load_dotenv(path: str = ".env") -> None:
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return
    with open(full, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


def report(name: str, fn):
    t0 = time.perf_counter()
    try:
        raw = fn()
        dt = time.perf_counter() - t0
        text = raw if isinstance(raw, str) else str(raw)
        print(f"[{name}] status=OK seconds={dt:.1f} words={len(text.split())}")
        print("  first 300 chars: " + text[:300].replace("\n", " "))
        return text
    except Exception as exc:
        dt = time.perf_counter() - t0
        print(f"[{name}] status=ERROR seconds={dt:.1f}")
        print(f"  error: {type(exc).__name__}: {exc}")
        return None


def main() -> int:
    load_dotenv()
    if not os.environ.get("MODEL_API_KEY"):
        print("MODEL_API_KEY is not set; aborting.")
        return 2

    from app import meta_api
    from app.main import parse_epigen_json
    from app.retrieval import build_epigen_prompt, retrieve
    from app.store import connect, load_memories

    question = "Should I buy this $180 jacket?"
    with open(os.path.join(ROOT, "demo", "jacket.png"), "rb") as f:
        photo = f.read()

    desc = report("describe_photo",
                  lambda: meta_api.describe_photo(photo, "image/png"))
    if desc is None:
        return 1

    report("plain_answer", lambda: meta_api.plain_answer(question, desc))

    def epigen_path():
        conn = connect()
        try:
            memories = load_memories(conn)
        finally:
            conn.close()
        retrieved = retrieve(question, desc, memories)
        raw = meta_api.epigen_answer(
            build_epigen_prompt(question, desc, retrieved)
        )
        parsed = parse_epigen_json(raw)
        print(f"  json parsed: {parsed is not None}"
              + (f", decision: {parsed.get('decision')}" if parsed else ""))
        return raw

    text = report("epigen_path", epigen_path)
    return 0 if text is not None else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"fatal: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        sys.exit(1)
