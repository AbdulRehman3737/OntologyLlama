"""Vector-RAG baseline for drift QA: MiniLM over the same pre-T0 abstracts the updater read."""
from __future__ import annotations

import json
from functools import lru_cache

import numpy as np

from ground import _model
from hpo import ROOT
from sources.pubmed import PubMed


def abstracts_rag(run: str, k: int = 3):
    log = json.loads((ROOT / "results" / "runs" / run / "acquisition_log.json").read_text())
    docs_by_d = {e["disease"]: e["docs"] for e in log}
    pm = PubMed()

    @lru_cache(maxsize=None)
    def index(disease: str):
        docs = pm.fetch(docs_by_d.get(disease, []))
        passages = []
        for d in docs:
            for s in (d.title + ". " + d.text).split(". "):
                if len(s) > 30:
                    passages.append(f"{s.strip()} ({d.id})")
        if not passages:
            return [], None
        emb = _model().encode(passages, normalize_embeddings=True, show_progress_bar=False)
        return passages, emb

    def retrieve(disease: str, question: str) -> str:
        passages, emb = index(disease)
        if not passages:
            return "Retrieved passages:\n- (no abstracts were retrieved for this disease)"
        q = _model().encode([question], normalize_embeddings=True, show_progress_bar=False)[0]
        top = np.argsort(-(emb @ q))[:k]
        return "Retrieved passages:\n" + "\n".join(f"- {passages[i]}" for i in top)

    return retrieve
