"""
The Phase 8 pipeline: takes raw fetched items (from NewsAPI/Reddit/
StockTwits, before they ever touch the DB) and returns only the ones worth
keeping, each enriched with sentiment + keywords. Everything filtered out
here - spam, near-duplicates, too-short-to-be-meaningful - never reaches
storage, so the DB only ever holds the "high-quality textual knowledge
base" this phase's objective calls for.
"""
from app.services import dedup, sentiment, text_cleaning, topic_extraction


def process_items(items: list[dict], text_field: str) -> list[dict]:
    """`items`: raw dicts with at least `text_field` (news items use
    "title", social posts use "content") plus whatever other keys the
    caller wants preserved (url, author, score, posted_at, ...).

    Returns a new list - same shape, minus filtered-out items, plus
    sentiment_score / sentiment_label / keywords on each survivor. The
    cleaned text replaces the original in `text_field`.
    """
    seen_normalized: list[str] = []
    processed: list[dict] = []

    for item in items:
        raw_text = item.get(text_field) or ""
        cleaned = text_cleaning.clean_text(raw_text)

        if text_cleaning.is_too_short_to_be_meaningful(cleaned):
            continue
        if text_cleaning.is_spam_or_ad(cleaned):
            continue
        if dedup.is_near_duplicate(cleaned, seen_normalized):
            continue

        seen_normalized.append(dedup.normalize_for_dedup(cleaned))

        sentiment_result = sentiment.analyze_sentiment(cleaned)
        keywords = topic_extraction.extract_keywords(cleaned)

        enriched = dict(item)
        enriched[text_field] = cleaned
        enriched["sentiment_score"] = sentiment_result["sentiment_score"]
        enriched["sentiment_label"] = sentiment_result["sentiment_label"]
        enriched["keywords"] = keywords
        processed.append(enriched)

    return processed
