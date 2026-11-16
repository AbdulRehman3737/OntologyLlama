"""Vector RAG baseline: MiniLM embeddings over the verbalised KG chunks, cosine top-k."""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from kg import ROOT
from verbalize import get_chunks

EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMB_CACHE = ROOT / "data" / "rag_embeddings.npy"
TOP_K = 4


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMB_MODEL, device="cpu")


class VectorRAG:
    def __init__(self, k: int = TOP_K):
        self.k = k
        self.chunks = get_chunks()
        if EMB_CACHE.exists():
            emb = np.load(EMB_CACHE)
            if emb.shape[0] != len(self.chunks):
                emb = self._embed_all()
        else:
            emb = self._embed_all()
        self.emb = emb

    def _embed_all(self) -> np.ndarray:
        emb = _model().encode([c["text"] for c in self.chunks], normalize_embeddings=True, batch_size=64)
        np.save(EMB_CACHE, emb)
        return emb

    def retrieve(self, question: str, k: int | None = None) -> list[dict]:
        q = _model().encode([question], normalize_embeddings=True)[0]
        scores = self.emb @ q
        idx = np.argsort(-scores)[: k or self.k]
        return [{**self.chunks[i], "score": float(scores[i])} for i in idx]

    @staticmethod
    def context(chunks: list[dict]) -> str:
        return "Retrieved passages:\n" + "\n".join(f"- {c['text']}" for c in chunks)


_RAG: VectorRAG | None = None


def get_rag() -> VectorRAG:
    global _RAG
    if _RAG is None:
        _RAG = VectorRAG()
    return _RAG
