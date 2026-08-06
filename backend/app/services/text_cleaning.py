"""
Cleans raw scraped text before it goes anywhere near sentiment/keyword
extraction, and flags obvious spam/ad/noise patterns so they never reach
the DB at all. Pure regex/heuristics - no model, no dependency, no
download - this runs on every single item so it needs to be fast.
"""
import re

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITY_RE = re.compile(r"&[a-zA-Z#0-9]+;")
_WHITESPACE_RE = re.compile(r"\s+")

# Promotional phrasing that shows up constantly in scraped social posts and
# press-release-style "news" but carries no actual investing signal.
_SPAM_PHRASES = [
    "click here", "subscribe now", "limited time offer", "act now",
    "buy now", "sign up today", "act fast", "dm me", "join our telegram",
    "join my discord", "guaranteed returns", "risk free", "100% profit",
    "double your money", "get rich quick", "follow for more", "link in bio",
]


def clean_text(raw: str) -> str:
    """Strips URLs/HTML/entities and collapses whitespace. Leaves casing
    and punctuation alone otherwise - sentiment analysis wants natural text,
    not a stemmed/lowercased version."""
    text = _URL_RE.sub("", raw or "")
    text = _HTML_TAG_RE.sub("", text)
    text = _HTML_ENTITY_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def is_spam_or_ad(text: str) -> bool:
    lowered = text.lower()

    if any(phrase in lowered for phrase in _SPAM_PHRASES):
        return True

    # Heavy caps-lock shouting is a common low-effort-spam signal - checked
    # only once there's enough alphabetic content for the ratio to mean anything.
    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 20:
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if caps_ratio > 0.7:
            return True

    # A wall of exclamation marks is another common spam tell.
    if text.count("!") >= 4:
        return True

    return False


def is_too_short_to_be_meaningful(text: str, min_words: int = 4) -> bool:
    """Filters near-empty posts ('lol', a bare ticker, a single emoji) that
    have no real discussion content for sentiment/topic extraction to work with."""
    return len(text.split()) < min_words
