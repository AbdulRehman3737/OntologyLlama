"""Reasoner-gated, provenance-weighted commit of candidate assertions.

Pipeline per candidate (aggregated over documents by (disease, relation, object, polarity)):
  1. domain/range  - disease must be a Disease in the ontology; phenotype ids must be HPO
                     phenotypic abnormalities (grounding guarantees this); gene symbols must
                     be known HGNC-style symbols from the gene vocabulary
  2. novelty       - already asserted -> 'known'; a phenotype that is an ancestor of an asserted
                     one adds nothing -> 'redundant'
  3. evidence      - at least k independent documents
  4. consistency   - HermiT on a per-disease module in which phenotypes are HPO classes:
                     positive  d : ∃hasPhenotype.HP_x
                     negative  d : ¬∃hasPhenotype.HP_y   (curated NOT annotations, extracted absences)
                     With the HPO subclass hierarchy, "NOT seizure" + "focal seizure" is inconsistent.
     Repair = weighted maximal consistent subset: add assertions in descending weight, keep each
     only if the module stays consistent. Curated assertions are never removed automatically:
     a curated assertion that loses is reported as 'curated_conflict' for human review.
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from hpo import ROOT, ancestors

DB = ROOT / "results" / "provenance.sqlite"


@dataclass
class Assertion:
    disease: str
    relation: str            # phenotype | inheritance | gene
    object: str
    positive: bool = True
    source: str = "extracted"   # curated | extracted
    docs: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    latest: str = "1900-01-01"
    status: str = "pending"
    reason: str = ""

    @property
    def key(self):
        return (self.disease, self.relation, self.object, self.positive)

    def weight(self) -> float:
        if self.source == "curated":
            return 10.0 + len(self.docs)
        # independent documents dominate; recency breaks ties (newer evidence slightly preferred)
        recency = (date.fromisoformat(self.latest).year - 1950) / 1000.0
        return float(len(set(self.docs))) + recency


def aggregate(candidates: list[dict]) -> list[Assertion]:
    agg: dict[tuple, Assertion] = {}
    for c in candidates:
        pos = c.get("positive", True)
        k = (c["disease"], c["relation"], c["object"], pos)
        a = agg.setdefault(k, Assertion(c["disease"], c["relation"], c["object"], pos))
        if c["doc_id"] not in a.docs:
            a.docs.append(c["doc_id"])
            a.evidence.append(c["evidence"])
        a.latest = max(a.latest, c["doc_date"])
    return list(agg.values())


class Gate:
    def __init__(self, terms, diseases: set[str], known_genes: set[str], curated: list[Assertion],
                 k: int = 1, use_reasoner: bool = True, check_redundancy: bool = True):
        self.terms, self.diseases, self.known_genes = terms, diseases, known_genes
        self.k, self.use_reasoner, self.check_redundancy = k, use_reasoner, check_redundancy
        self.curated = defaultdict(list)
        for a in curated:
            self.curated[a.disease].append(a)

    # ------------------------------------------------------------------ checks
    def _domain(self, a: Assertion) -> str | None:
        if a.disease not in self.diseases:
            return "disease not in ontology"
        if a.relation == "phenotype" and a.object not in self.terms:
            return "unknown HPO term"
        if a.relation == "gene" and a.object not in self.known_genes:
            return "unknown gene symbol"
        return None

    def _novelty(self, a: Assertion) -> str | None:
        same = [c for c in self.curated[a.disease] if c.relation == a.relation and c.positive == a.positive]
        if any(c.object == a.object for c in same):
            return "known"
        if self.check_redundancy and a.relation == "phenotype" and a.positive:
            if any(a.object in ancestors(self.terms, c.object) for c in same):
                return "redundant"
        return None

    # ------------------------------------------------------------------ reasoning
    def _consistent(self, disease: str, assertions: list[Assertion]) -> bool:
        import owlready2 as o2
        phen = [a for a in assertions if a.relation == "phenotype"]
        if not any(not a.positive for a in phen):
            return True  # without a negation this TBox cannot be violated
        w = o2.World()
        onto = w.get_ontology("http://example.org/gate#")
        with onto:
            class Disease(o2.Thing):
                pass

            class hasPhenotype(o2.ObjectProperty):
                domain = [Disease]
            classes = {}

            def cls(hid):
                if hid not in classes:
                    parents = [cls(p) for p in self.terms[hid].parents if p in self.terms] if hid in self.terms else []
                    classes[hid] = o2.types.new_class(hid.replace(":", "_"), tuple(parents) or (o2.Thing,))
                return classes[hid]
            d = Disease(disease.replace(":", "_"))
            for a in phen:
                r = hasPhenotype.some(cls(a.object))
                d.is_a.append(r if a.positive else o2.Not(r))
        try:
            o2.sync_reasoner_hermit(w, infer_property_values=False, debug=0)
            return True
        except o2.OwlReadyInconsistentOntologyError:
            return False

    def _relevant(self, base: list[Assertion], new: list[Assertion]) -> list[Assertion]:
        """Assertions that can take part in a conflict: negations and the positives they cover."""
        allx = [a for a in base + new if a.relation == "phenotype"]
        negs = [a for a in allx if not a.positive]
        out = []
        for a in allx:
            if not a.positive:
                out.append(a)
            elif any(a.object == n.object or n.object in ancestors(self.terms, a.object) for n in negs):
                out.append(a)
        return out

    def _repair(self, disease: str, new: list[Assertion]) -> None:
        base = self.curated[disease]
        rel = self._relevant(base, new)
        if not rel or self._consistent(disease, rel):
            return
        kept: list[Assertion] = []
        for a in sorted(rel, key=lambda x: -x.weight()):
            if self._consistent(disease, kept + [a]):
                kept.append(a)
            elif a.source == "curated":
                a.status, a.reason = "curated_conflict", "outweighed by extracted evidence; needs review"
            else:
                a.status, a.reason = "rejected", "conflict: inconsistent with heavier assertions"

    # ------------------------------------------------------------------ main
    def run(self, assertions: list[Assertion]) -> list[Assertion]:
        by_d = defaultdict(list)
        for a in assertions:
            r = self._domain(a)
            if r:
                a.status, a.reason = "rejected", f"domain: {r}"
                continue
            r = self._novelty(a)
            if r:
                a.status, a.reason = r, ""
                continue
            if len(set(a.docs)) < self.k:
                a.status, a.reason = "rejected", f"evidence: {len(set(a.docs))} < {self.k} documents"
                continue
            by_d[a.disease].append(a)
        for disease, new in by_d.items():
            if self.use_reasoner:
                self._repair(disease, new)
            for a in new:
                if a.status == "pending":
                    a.status = "accepted"
        return assertions


def save(assertions: list[Assertion], run: str, step: int) -> None:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute("""create table if not exists assertions(run text, step int, disease text, relation text, object text,
                   positive int, source text, status text, reason text, weight real, docs text, evidence text)""")
    con.executemany("insert into assertions values (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(run, step, a.disease, a.relation, a.object, int(a.positive), a.source, a.status, a.reason,
                      a.weight(), json.dumps(a.docs), json.dumps(a.evidence)) for a in assertions])
    con.commit()
    con.close()
