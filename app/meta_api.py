"""Meta Model API client.

All API facts below come from dev.meta.ai docs (checked 2026-11-03):
- Base URL: https://api.meta.ai/v1, endpoint POST /v1/chat/completions
- Auth: Authorization: Bearer $MODEL_API_KEY (env var MODEL_API_KEY)
- Model: muse-spark-1.3 (Standard; -contributor variant also exists)
- SDK: pip install openai, then OpenAI(base_url="https://api.meta.ai/v1",
  api_key=...).chat.completions.create(model="muse-spark-1.3", messages=[...]);
  answer text at choices[0].message.content.
- Photo description uses the documented image-understanding path: Chat
  Completions content blocks of {"type": "image_url",
  "image_url": {"url": <public URL or base64 data URL>}}.
  (Muse Image generates/edits images and SAM segments them, so neither is
  the describe path; Muse Spark's image understanding is.)
- The docs list no embedding endpoint, so embeddings stay local
  (see app/embeddings.py).

With no MODEL_API_KEY set, the app runs in DEMO MODE: deterministic local
stubs that still show the plain-vs-Epigen difference, clearly labeled.
"""

import base64
import os

BASE_URL = "https://api.meta.ai/v1"
MODEL = os.environ.get("EPIGEN_MODEL", "muse-spark-1.3")


def has_key() -> bool:
    return bool(os.environ.get("MODEL_API_KEY"))


def _client():
    from openai import OpenAI

    return OpenAI(base_url=BASE_URL, api_key=os.environ["MODEL_API_KEY"])


def chat(messages: list[dict], model: str = MODEL) -> str:
    client = _client()
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content or ""


def describe_photo(image_bytes: bytes, mime: str = "image/png") -> str:
    """Describe an uploaded photo via Muse Spark image understanding."""
    data_url = (
        f"data:{mime};base64," + base64.b64encode(image_bytes).decode("ascii")
    )
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Describe this item for a shopping decision:"
                    " what is it, color, style, apparent quality, and any"
                    " visible price tag or brand. One short paragraph.",
                },
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]
    return chat(messages)


def plain_answer(question: str, photo_description: str = "") -> str:
    """Generic answer with no personal context."""
    user = question if not photo_description else (
        f"{question}\n\nPhoto description: {photo_description}"
    )
    messages = [
        {
            "role": "developer",
            "content": "Answer as a generic shopping/finance assistant."
            " You know nothing about this user. Give broadly useful advice"
            " and note the trade-offs. Do not invent personal facts.",
        },
        {"role": "user", "content": user},
    ]
    return chat(messages)


def epigen_answer(messages: list[dict]) -> str:
    """Answer from the memory-grounded prompt built by retrieval."""
    return chat(messages)


# ---- DEMO MODE stubs (no key): deterministic, clearly labeled ----------


def stub_photo_description(filename: str) -> str:
    return (
        f"A dark wool-blend winter jacket in the uploaded photo ({filename}),"
        " looks new, listed at about $180."
    )


def stub_plain(question: str, photo_description: str) -> str:
    return (
        "A $180 winter jacket is a reasonable buy if the fit, warmth, and"
        " return policy check out. Compare the price with similar jackets,"
        " check the material and warranty, and sleep on it before deciding."
        f" (Your question: {question.strip() or 'Should I buy this?'})"
    )


def stub_epigen(question: str, mems: list[dict]) -> str:
    shopping = [m for m in mems if m["angle"] == "shopping"]
    family = [m for m in mems if m["angle"] == "family"]
    parts = []
    if shopping:
        ids = " ".join(f"[{m['id']}]" for m in shopping[:4])
        parts.append(
            "You have regretted clothing purchases over $150 before"
            f" {ids} — expensive jackets tended to go back unworn."
        )
    if family:
        ids = " ".join(f"[{m['id']}]" for m in family[:4])
        parts.append(
            "You are also saving for the apartment with your partner"
            f" {ids}, so $180 now competes directly with that goal."
        )
    if not parts:
        return (
            "No memory supports a personal recommendation"
            " (no memory supports this claim)."
        )
    return (
        "I'd pass on the $180 jacket. " + " ".join(parts)
        + " If you still want it, wait 48 hours and check it against"
        " your $200/month clothing budget first."
    )
