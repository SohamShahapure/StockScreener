from app.services import nlp_pipeline


def test_pipeline_filters_spam_and_enriches_survivors():
    items = [
        {"title": "Apple beats Q3 earnings estimates on strong iPhone sales", "url": "https://a.com/1"},
        {"title": "CLICK HERE FOR GUARANTEED RETURNS BUY NOW!!!!", "url": "https://a.com/2"},
        {"title": "lol", "url": "https://a.com/3"},
    ]

    result = nlp_pipeline.process_items(items, text_field="title")

    assert len(result) == 1
    survivor = result[0]
    assert survivor["url"] == "https://a.com/1"
    assert "sentiment_score" in survivor
    assert "sentiment_label" in survivor
    assert isinstance(survivor["keywords"], list)


def test_pipeline_dedupes_near_identical_items():
    items = [
        {"title": "Apple beats Q3 earnings estimates on strong iPhone sales", "url": "https://a.com/1"},
        {"title": "Apple beats Q3 earnings estimate on strong iPhone sale", "url": "https://a.com/2"},
        {"title": "Tesla recalls vehicles over a software issue affecting braking", "url": "https://a.com/3"},
    ]

    result = nlp_pipeline.process_items(items, text_field="title")

    # near-duplicate (2) dropped, distinct story (3) kept
    urls = {r["url"] for r in result}
    assert urls == {"https://a.com/1", "https://a.com/3"}


def test_pipeline_preserves_other_fields():
    items = [
        {
            "title": "Apple beats Q3 earnings estimates on strong iPhone sales",
            "url": "https://a.com/1",
            "source": "Reuters",
            "published_at": "2026-07-20T10:00:00Z",
        }
    ]

    result = nlp_pipeline.process_items(items, text_field="title")

    assert result[0]["source"] == "Reuters"
    assert result[0]["published_at"] == "2026-07-20T10:00:00Z"


def test_pipeline_empty_input_returns_empty_list():
    assert nlp_pipeline.process_items([], text_field="title") == []
