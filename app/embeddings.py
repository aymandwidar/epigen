"""Deterministic local text embeddings.

The Meta Model API docs (dev.meta.ai) document chat, responses, messages,
image, and voice endpoints, but no embedding endpoint, so Epigen embeds
locally: hashed token vectors, L2-normalized. No downloads, no cloud,
deterministic (seed script and tests depend on that).
"""

import hashlib
import math
import re

DIM = 256
_TOKEN_RE = re.compile(r"[a-z0-9']+")


def _token_hash(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "little")


def embed(text: str, dim: int = DIM) -> list[float]:
    vec = [0.0] * dim
    for token in _TOKEN_RE.findall(text.lower()):
        h = _token_hash(token)
        vec[h % dim] += 1.0
        vec[(h >> 16) % dim] -= 0.5
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))
