"""
YAKE (Yet Another Keyword Extractor) - unsupervised statistical keyword
extraction, no training corpus or model download needed (unlike spaCy/
transformer-based approaches), and works well on the kind of short text
(headlines, social posts) Phases 5/7 collect.
"""
import yake

# n=2 allows two-word phrases ("earnings beat", "rate cuts"), not just single
# words; dedupLim keeps near-identical keyword variants from both appearing.
_extractor = yake.KeywordExtractor(lan="en", n=2, top=5, dedupLim=0.7)


def extract_keywords(text: str, top_n: int = 5) -> list[str]:
    if not text or not text.strip():
        return []

    results = _extractor.extract_keywords(text)
    # YAKE scores are "lower is more relevant" - sort ascending before slicing.
    results.sort(key=lambda pair: pair[1])
    return [keyword for keyword, _score in results[:top_n]]
