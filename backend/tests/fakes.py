"""
A deterministic, bag-of-words-style "embedding" function for tests. It's
not semantically meaningful the way a real sentence-transformer model is -
its only job is to let us prove the *storage and retrieval plumbing* (the
code we actually wrote) works correctly, without a ~90MB download that
this sandbox's network can't reach anyway. Two texts that share more
vocabulary get closer vectors, which is enough to test ranking behavior
deterministically.
"""
import hashlib

_VOCAB_SIZE = 64


def _text_to_vector(text: str) -> list[float]:
    vector = [0.0] * _VOCAB_SIZE
    for word in text.lower().split():
        idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % _VOCAB_SIZE
        vector[idx] += 1.0
    # normalize so cosine/L2 distance behaves sensibly regardless of doc length
    norm = sum(v * v for v in vector) ** 0.5
    if norm > 0:
        vector = [v / norm for v in vector]
    return vector


class FakeEmbeddingFunction:
    def __call__(self, input):  # noqa: A002 - name required by Chroma's protocol
        return [_text_to_vector(text) for text in input]

    def is_legacy(self) -> bool:
        return False

    def embed_query(self, input):  # noqa: A002
        return self.__call__(input)

    def name(self) -> str:
        return "fake-embedding-function"
