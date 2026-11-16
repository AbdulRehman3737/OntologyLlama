"""Ground free-text phenotype phrases to HPO terms, using only the vocabulary of a given release.

1. exact match of the normalised phrase against HPO names and synonyms;
2. otherwise MiniLM nearest neighbour over names+synonyms, accepted if cosine >= threshold.
Only descendants of 'Phenotypic abnormality' (HP:0000118) are allowed.
"""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np

from hpo import PHENOTYPIC_ABNORMALITY, ROOT, ancestors, read_obo

CACHE = ROOT / "data" / "cache" / "embeddings"
EMB_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def normalize(text: str) -> str:
    t = text.lower().replace("β", "beta").replace("α", "alpha")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMB_MODEL, device="cpu")


class HPOGrounder:
    def __init__(self, tag: str, threshold: float = 0.82):
        self.tag, self.threshold = tag, threshold
        self.terms = read_obo(tag)
        self.allowed = {t.id for t in self.terms.values()
                        if not t.obsolete and PHENOTYPIC_ABNORMALITY in ancestors(self.terms, t.id)}
        self.strings: list[str] = []
        self.ids: list[str] = []
        self.exact: dict[str, str] = {}
        for hid in sorted(self.allowed):
            t = self.terms[hid]
            for s in [t.name, *t.synonyms]:
                n = normalize(s)
                if n:
                    self.exact.setdefault(n, hid)
                    self.strings.append(s)
                    self.ids.append(hid)
        self._emb = None

    def _embeddings(self) -> np.ndarray:
        if self._emb is None:
            CACHE.mkdir(parents=True, exist_ok=True)
            f = CACHE / f"hpo_{self.tag}.npy"
            if f.exists() and np.load(f).shape[0] == len(self.strings):
                self._emb = np.load(f)
            else:
                self._emb = _model().encode(self.strings, normalize_embeddings=True, batch_size=256, show_progress_bar=False)
                np.save(f, self._emb)
        return self._emb

    def ground(self, phrase: str) -> tuple[str | None, float, str]:
        """Return (hpo_id, score, method). method in exact | embedding | none."""
        n = normalize(phrase)
        if n in self.exact:
            return self.exact[n], 1.0, "exact"
        if not n:
            return None, 0.0, "none"
        q = _model().encode([phrase], normalize_embeddings=True, show_progress_bar=False)[0]
        sims = self._embeddings() @ q
        i = int(np.argmax(sims))
        if sims[i] >= self.threshold:
            return self.ids[i], float(sims[i]), "embedding"
        return None, float(sims[i]), "none"

    def label(self, hid: str) -> str:
        return self.terms[hid].name if hid in self.terms else hid

    def related(self, a: str, b: str) -> bool:
        """True if a and b are the same term or one is an ancestor of the other."""
        return a == b or a in ancestors(self.terms, b) or b in ancestors(self.terms, a)
