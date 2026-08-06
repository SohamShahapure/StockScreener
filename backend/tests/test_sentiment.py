from app.services import sentiment


def test_clearly_positive_text():
    result = sentiment.analyze_sentiment("Apple crushed earnings expectations, stock surges on great news")
    assert result["sentiment_label"] == "positive"
    assert result["sentiment_score"] > 0


def test_clearly_negative_text():
    result = sentiment.analyze_sentiment("Company misses estimates badly, shares plunge on terrible outlook")
    assert result["sentiment_label"] == "negative"
    assert result["sentiment_score"] < 0


def test_neutral_factual_text():
    result = sentiment.analyze_sentiment("The company will report earnings on Thursday")
    assert result["sentiment_label"] == "neutral"


def test_score_is_rounded_and_bounded():
    result = sentiment.analyze_sentiment("Best quarter ever, incredible results, amazing growth")
    assert -1.0 <= result["sentiment_score"] <= 1.0
