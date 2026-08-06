"""
Catches duplicate/near-duplicate content that the existing symbol+url
uniqueness constraint (Phase 5/7) can't see - the same story syndicated
under a different URL, or a near-identical crosspost with a word or two
changed. Pure difflib, no embedding model needed at this scale (we're
comparing a handful of freshly-fetched items per request, not a corpus).
"""
import difflib
import re

_PUNCT_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_for_dedup(text: str) -> str:
    text = text.lower()
    text = _PUNCT_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def is_near_duplicate(text: str, seen_normalized: list[str], threshold: float = 0.9) -> bool:
    """`seen_normalized` should already be normalized (via normalize_for_dedup)
    - callers build this list up as they process a batch, so each new item
    is compared against everything kept so far."""
    normalized = normalize_for_dedup(text)
    if not normalized:
        return True  # nothing left after normalization isn't meaningful content anyway

    for seen in seen_normalized:
        ratio = difflib.SequenceMatcher(None, normalized, seen).ratio()
        if ratio >= threshold:
            return True
    return False
