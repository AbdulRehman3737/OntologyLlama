"""LLM extraction of candidate assertions from a document, restricted to the ontology's relations.

The model returns JSON (Ollama structured outputs) with a verbatim evidence sentence per item.
An item is kept only if its evidence sentence is found in the document text, so facts the model
"remembers" but the document does not state are dropped (memorisation guard).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass

import ollama
from rapidfuzz import fuzz

from ground import HPOGrounder, normalize
from sources.base import Doc

EXTRACTOR = "qwen3:8b"
OPTIONS = {"temperature": 0, "seed": 42, "num_ctx": 4096, "num_predict": 1024}

SCHEMA = {
    "type": "object",
    "properties": {
        "phenotypes": {"type": "array", "items": {
            "type": "object",
            "properties": {"phrase": {"type": "string"}, "evidence": {"type": "string"}},
            "required": ["phrase", "evidence"]}},
        "absent_phenotypes": {"type": "array", "items": {
            "type": "object",
            "properties": {"phrase": {"type": "string"}, "evidence": {"type": "string"}},
            "required": ["phrase", "evidence"]}},
        "inheritance": {"type": "array", "items": {
            "type": "object",
            "properties": {"mode": {"type": "string", "enum": [
                "autosomal recessive", "autosomal dominant", "X-linked recessive", "X-linked dominant",
                "X-linked", "mitochondrial", "Y-linked"]}, "evidence": {"type": "string"}},
            "required": ["mode", "evidence"]}},
        "genes": {"type": "array", "items": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}, "evidence": {"type": "string"}},
            "required": ["symbol", "evidence"]}},
    },
    "required": ["phenotypes", "absent_phenotypes", "inheritance", "genes"],
}

PROMPT = """You extract facts about one rare disease from a PubMed abstract, for the Human Phenotype Ontology.

Disease: {disease}
Known causative gene(s): {genes}

From the abstract below, extract ONLY facts explicitly stated about patients with this disease:
- phenotypes: abnormal clinical features observed in patients. "phrase" must be a SHORT clinical term of 1-6 words in HPO style, keeping the direction of the abnormality, e.g. "Hypogammaglobulinemia", "Recurrent bacterial infections", "Increased IgM level", "Reduced natural killer cell activity", "Intellectual disability". One feature per item; split lists. Never copy a whole sentence into "phrase".
- absent_phenotypes: features the abstract explicitly says were absent or normal, written as the abnormality that was ruled out (e.g. "normal hearing" -> "Hearing impairment").
- inheritance: the mode of inheritance, if stated.
- genes: genes stated to cause this disease (HGNC symbols).
For every item, "evidence" is a short exact quote (at most 15 words) copied from the abstract that supports it.
If the abstract is not about this disease, or a category is not stated, return an empty list for it. Do not use outside knowledge.

Title: {title}
Abstract: {text}"""

INHERITANCE_HPO = {
    "autosomal recessive": "HP:0000007", "autosomal dominant": "HP:0000006", "x-linked recessive": "HP:0001419",
    "x-linked dominant": "HP:0001423", "x-linked": "HP:0001417", "mitochondrial": "HP:0001427", "y-linked": "HP:0001450",
}


@dataclass
class Candidate:
    disease: str
    relation: str          # phenotype | inheritance | gene
    object: str            # HPO id or gene symbol
    phrase: str
    evidence: str
    doc_id: str
    doc_date: str
    ground_score: float
    ground_method: str
    positive: bool = True


def evidence_in(evidence: str, text: str, threshold: float = 85) -> bool:
    e, t = normalize(evidence), normalize(text)
    if not e:
        return False
    return e in t or fuzz.partial_ratio(e, t) >= threshold


def call_llm(disease: str, genes: list[str], doc: Doc, model: str = EXTRACTOR, with_text: bool = True) -> tuple[dict, float]:
    prompt = PROMPT.format(disease=disease, genes=", ".join(genes) or "unknown", title=doc.title,
                           text=doc.text if with_text else "(abstract withheld)")
    t0 = time.perf_counter()
    kwargs = {"think": False} if model.startswith("qwen3") else {}
    r = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}], format=SCHEMA,
                    options=OPTIONS, **kwargs)
    secs = time.perf_counter() - t0
    try:
        return json.loads(r["message"]["content"]), secs
    except json.JSONDecodeError:
        return {"phenotypes": [], "absent_phenotypes": [], "inheritance": [], "genes": []}, secs


def extract(disease_id: str, disease: str, genes: list[str], doc: Doc, grounder: HPOGrounder,
            model: str = EXTRACTOR, raw: dict | None = None) -> tuple[list[Candidate], dict]:
    if raw is None:
        raw, secs = call_llm(disease, genes, doc, model)
    else:
        secs = 0.0
    text = f"{doc.title}\n{doc.text}"
    out: list[Candidate] = []
    stats = {"secs": secs, "items": 0, "no_evidence": 0, "ungrounded": 0}
    for key, positive in (("phenotypes", True), ("absent_phenotypes", False)):
        for p in raw.get(key, []):
            stats["items"] += 1
            if not evidence_in(p.get("evidence", ""), text):
                stats["no_evidence"] += 1
                continue
            hid, score, method = grounder.ground(p.get("phrase", ""))
            if hid is None:
                stats["ungrounded"] += 1
                continue
            out.append(Candidate(disease_id, "phenotype", hid, p["phrase"], p["evidence"], doc.id,
                                 doc.available.isoformat(), score, method, positive))
    for i in raw.get("inheritance", []):
        stats["items"] += 1
        hid = INHERITANCE_HPO.get(str(i.get("mode", "")).lower())
        if hid and evidence_in(i.get("evidence", ""), text):
            out.append(Candidate(disease_id, "inheritance", hid, i["mode"], i["evidence"], doc.id,
                                 doc.available.isoformat(), 1.0, "enum"))
        else:
            stats["no_evidence"] += 1
    for g in raw.get("genes", []):
        stats["items"] += 1
        sym = str(g.get("symbol", "")).strip().upper()
        if sym and evidence_in(g.get("evidence", ""), text) and sym in text.upper():
            out.append(Candidate(disease_id, "gene", sym, sym, g["evidence"], doc.id, doc.available.isoformat(), 1.0, "symbol"))
        else:
            stats["no_evidence"] += 1
    return out, {**stats, "raw": raw}


def to_dict(c: Candidate) -> dict:
    return asdict(c)
