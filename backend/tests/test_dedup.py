from app.services import dedup


def test_normalize_strips_punctuation_and_case():
    assert dedup.normalize_for_dedup("Apple's Q3 Earnings BEAT Estimates!") == "apples q3 earnings beat estimates"


def test_identical_text_is_near_duplicate():
    seen = [dedup.normalize_for_dedup("Apple beats Q3 earnings estimates")]
    assert dedup.is_near_duplicate("Apple beats Q3 earnings estimates", seen)


def test_near_identical_text_is_near_duplicate():
    seen = [dedup.normalize_for_dedup("Apple beats Q3 earnings estimates on strong iPhone sales")]
    # same story, minor rewording - should still be caught
    assert dedup.is_near_duplicate("Apple beats Q3 earnings estimates on strong iPhone sale", seen)


def test_distinct_text_is_not_duplicate():
    seen = [dedup.normalize_for_dedup("Apple beats Q3 earnings estimates")]
    assert not dedup.is_near_duplicate("Tesla recalls vehicles over software issue", seen)


def test_empty_after_normalization_counts_as_duplicate():
    # e.g. text that was only punctuation/emoji before cleaning
    assert dedup.is_near_duplicate("!!! ??? ...", [])
