"""Local text embeddings, with an optional semantic backend.

The Meta Model API docs (dev.meta.ai) document chat, responses, messages,
image, and voice endpoints, but no embedding endpoint, so Epigen embeds
locally. Two backends, selected with EPIGEN_EMBEDDINGS (default "semantic"):

- "semantic": fastembed with BAAI/bge-small-en-v1.5, cached in .models/
  inside the project. Needs `pip install -r requirements.txt`; the model
  downloads on first use.
- "hashed": deterministic hashed token vectors, L2-normalized. No
  downloads, no cloud, deterministic (seed script and tests depend on it).

Anything else (or a semantic load failure) falls back to "hashed" with a
warning. Switching backends changes vector dimensions, so re-seed after
switching (scripts/reset_demo.py).
"""

import hashlib
import logging
import math
import os
import re

log = logging.getLogger(__name__)

HASHED_DIM = 256
SEMANTIC_MODEL = "BAAI/bge-small-en-v1.5"
_TOKEN_RE = re.compile(r"[a-z0-9']+")

_model = None
_fallback_warned = False


def _token_hash(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int.from_bytes(bytes.fromhex(digest[:8]), "little")


def embed_hashed(text: str, dim: int = HASHED_DIM) -> list[float]:
    vec = [0.0] * dim
    for token in _TOKEN_RE.findall(text.lower()):
        h = _token_hash(token)
        vec[h % dim] += 1.0
        vec[(h >> 16) % dim] -= 0.5
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


def _load_semantic():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(
            model_name=SEMANTIC_MODEL, cache_dir=".models"
        )
    return _model


def backend_in_use() -> str:
    """Which backend embed() will use right now ("semantic" or "hashed")."""
    if os.environ.get("EPIGEN_EMBEDDINGS", "semantic").lower() != "semantic":
        return "hashed"
    try:
        _load_semantic()
        return "semantic"
    except Exception:
        return "hashed"


def embedding_dim() -> int:
    """Dimension of vectors embed() currently produces."""
    if backend_in_use() == "semantic":
        vec = next(iter(_load_semantic().embed(["dimension probe"])))
        return len(list(vec))
    return HASHED_DIM


def embed(text: str, dim: int = HASHED_DIM) -> list[float]:
    if os.environ.get("EPIGEN_EMBEDDINGS", "semantic").lower() == "semantic":
        try:
            vec = list(next(iter(_load_semantic().embed([text]))))
            norm = math.sqrt(sum(v * v for v in vec))
            if norm == 0.0:
                return vec
            return [v / norm for v in vec]
        except Exception as exc:
            global _fallback_warned
            if not _fallback_warned:
                log.warning(
                    "semantic embeddings unavailable (%s); using hashed",
                    exc,
                )
                _fallback_warned = True
    return embed_hashed(text, dim)


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
