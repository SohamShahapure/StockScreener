from app.services import text_cleaning


def test_clean_text_strips_urls_and_html():
    raw = 'Check this out <b>now</b>! https://example.com/foo &amp; more info'
    cleaned = text_cleaning.clean_text(raw)
    assert "https://" not in cleaned
    assert "<b>" not in cleaned
    assert "&amp;" not in cleaned


def test_clean_text_collapses_whitespace():
    raw = "AAPL   just    beat\n\nearnings   estimates"
    assert text_cleaning.clean_text(raw) == "AAPL just beat earnings estimates"


def test_spam_phrase_detected():
    assert text_cleaning.is_spam_or_ad("Click here to double your money guaranteed returns!")


def test_normal_discussion_not_flagged_as_spam():
    assert not text_cleaning.is_spam_or_ad(
        "Apple's Q3 earnings beat estimates on strong iPhone sales in China"
    )


def test_all_caps_shouting_flagged_as_spam():
    assert text_cleaning.is_spam_or_ad("THIS STOCK IS GOING TO THE MOON BUY NOW BEFORE ITS TOO LATE")


def test_excessive_exclamation_flagged_as_spam():
    assert text_cleaning.is_spam_or_ad("Huge news!!!! Don't miss this!!!!")


def test_too_short_is_flagged():
    assert text_cleaning.is_too_short_to_be_meaningful("lol nice")
    assert text_cleaning.is_too_short_to_be_meaningful("🚀🚀🚀")


def test_normal_length_is_not_flagged_as_too_short():
    assert not text_cleaning.is_too_short_to_be_meaningful(
        "Apple shares rose after the company reported record services revenue"
    )
