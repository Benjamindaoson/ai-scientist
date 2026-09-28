from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class HashingEmbeddingProvider:
    dimension: int = 1024
    model_name: str = "test/hashing-1024"

    @property
    def config(self) -> dict:
        return {"algorithm": "sha256-token-hashing", "dimension": self.dimension, "local": True}

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dimension] += 1.0 if digest[4] % 2 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class BGEEmbeddingProvider:
    model_name = "BAAI/bge-m3"
    dimension = 1024
    config = {"normalize_embeddings": True, "local": True}

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Install the literature embedding extra to use BAAI/bge-m3") from exc
        self._model = SentenceTransformer(self.model_name)

    def embed(self, text: str) -> list[float]:
        return self._model.encode([text], normalize_embeddings=True)[0].tolist()

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True, batch_size=min(128, len(texts))).tolist()
