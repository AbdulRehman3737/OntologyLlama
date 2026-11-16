"""The four experimental arms behind one interface: answer(question) -> dict."""
from __future__ import annotations

import time

from llm import ask
from ontology_layer import get_layer
from rag import VectorRAG, get_rag

ARMS = ["A_closed_book", "B_vector_rag", "C_ontology", "D_ontology_verified", "C0_ontology_facts_only"]
# C0 is an ablation: the ontology layer's retrieved facts but WITHOUT the computed query-result line.


def closed_book(q: str) -> dict:
    r = ask(q)
    return {"answer": r["text"], "llm_answer": r["text"], "context": None, **_meta(r)}


def vector_rag(q: str) -> dict:
    t0 = time.perf_counter()
    chunks = get_rag().retrieve(q)
    retrieval_s = time.perf_counter() - t0
    ctx = VectorRAG.context(chunks)
    r = ask(q, ctx)
    return {"answer": r["text"], "llm_answer": r["text"], "context": ctx, "retrieved": [c["id"] for c in chunks],
            "retrieval_s": round(retrieval_s, 3), **_meta(r)}


def _ontology(q: str, verify: bool, with_result: bool = True) -> dict:
    layer = get_layer()
    t0 = time.perf_counter()
    plan = layer.plan(q)
    retrieval_s = time.perf_counter() - t0
    ctx = layer.context(plan, with_result=with_result)
    r = ask(q, ctx)
    out = {"answer": r["text"], "llm_answer": r["text"], "context": ctx, "retrieval_s": round(retrieval_s, 3),
           "plan": {"kind": plan.kind, "target_type": plan.target_type, "anchors": plan.anchors,
                    "class": plan.class_name, "sparql": plan.sparql, "results": plan.results,
                    "truth": plan.truth, "fuzzy": plan.fuzzy}, **_meta(r)}
    if verify:
        final, action = layer.verify(plan, r["text"])
        out["answer"], out["verify_action"] = final, action
    return out


def ontology(q: str) -> dict:
    return _ontology(q, verify=False)


def ontology_verified(q: str) -> dict:
    return _ontology(q, verify=True)


def ontology_facts_only(q: str) -> dict:
    return _ontology(q, verify=False, with_result=False)


def _meta(r: dict) -> dict:
    return {"latency_s": r["latency_s"], "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"]}


DISPATCH = {"A_closed_book": closed_book, "B_vector_rag": vector_rag,
            "C_ontology": ontology, "D_ontology_verified": ontology_verified,
            "C0_ontology_facts_only": ontology_facts_only}
