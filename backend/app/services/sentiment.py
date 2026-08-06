"""
Wraps vaderSentiment - chosen over a transformer model because it ships its
lexicon as package data (works immediately after `pip install`, no separate
download step) and is specifically tuned for short, informal text (slang,
emphasis via punctuation/caps, emoji), which is most of what Phases 5/7
collect from news headlines and social posts.
"""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

# VADER's own documented thresholds for its compound score.
_POSITIVE_THRESHOLD = 0.05
_NEGATIVE_THRESHOLD = -0.05


def analyze_sentiment(text: str) -> dict:
    scores = _analyzer.polarity_scores(text)
    compound = scores["compound"]

    if compound >= _POSITIVE_THRESHOLD:
        label = "positive"
    elif compound <= _NEGATIVE_THRESHOLD:
        label = "negative"
    else:
        label = "neutral"

    return {"sentiment_score": round(compound, 4), "sentiment_label": label}
