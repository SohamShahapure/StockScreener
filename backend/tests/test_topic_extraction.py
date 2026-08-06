from app.services import topic_extraction


def test_extracts_keywords_from_normal_text():
    keywords = topic_extraction.extract_keywords(
        "Apple reported record iPhone sales in China driving strong quarterly earnings growth"
    )
    assert len(keywords) > 0
    assert all(isinstance(k, str) for k in keywords)


def test_empty_text_returns_no_keywords():
    assert topic_extraction.extract_keywords("") == []
    assert topic_extraction.extract_keywords("   ") == []


def test_respects_top_n():
    keywords = topic_extraction.extract_keywords(
        "Apple reported record iPhone sales in China driving strong quarterly earnings growth "
        "as services revenue also hit an all-time high this quarter",
        top_n=2,
    )
    assert len(keywords) <= 2
