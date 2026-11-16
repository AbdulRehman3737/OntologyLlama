"""Schema-certified gaps: TBox existential restrictions checked closed-world over the ABox.

Under OWL's open-world semantics a missing filler (e.g. a MendelianDisease with no
hasCausativeGene) is not an inconsistency, so the reasoner cannot report it. We therefore read
the existentials from the TBox and check them SHACL-style over asserted + inferred facts.
A gap is a certified "known unknown": the schema says a value must exist, the ABox has none.
"""
from __future__ import annotations

from dataclasses import dataclass

from rdflib import OWL, RDF, RDFS, Graph, URIRef

from tbox import NS


@dataclass(frozen=True)
class Gap:
    individual: str     # local id, e.g. OMIM_123456
    cls: str            # class whose existential is unmet
    prop: str
    filler: str


def existentials(g: Graph) -> list[tuple[str, str, str]]:
    """(class, property, filler) for every C ⊑ ∃p.F in the graph's TBox."""
    out = []
    for cls, _, r in g.triples((None, RDFS.subClassOf, None)):
        if (r, RDF.type, OWL.Restriction) in g:
            p = g.value(r, OWL.onProperty)
            f = g.value(r, OWL.someValuesFrom)
            if p is not None and f is not None:
                out.append((_local(cls), _local(p), _local(f)))
    return sorted(out)


def _local(u: URIRef) -> str:
    return str(u).split("#")[-1]


def _instances(g: Graph, cls: str) -> set[URIRef]:
    """Instances of cls including its asserted subclasses (RDFS-level inference)."""
    classes, stack = {NS[cls]}, [NS[cls]]
    while stack:
        c = stack.pop()
        for sub in g.subjects(RDFS.subClassOf, c):
            if sub not in classes:
                classes.add(sub)
                stack.append(sub)
    return {s for c in classes for s in g.subjects(RDF.type, c)}


def find_gaps(g: Graph) -> list[Gap]:
    gaps = []
    for cls, prop, filler in existentials(g):
        for ind in _instances(g, cls):
            fillers = set(g.objects(ind, NS[prop]))
            if not any((f, RDF.type, NS[filler]) in g for f in fillers):
                gaps.append(Gap(_local(ind), cls, prop, filler))
    return sorted(gaps, key=lambda x: (x.individual, x.prop))


def gaps_for(g: Graph, individual: str) -> list[Gap]:
    return [x for x in find_gaps(g) if x.individual == individual]


if __name__ == "__main__":
    from collections import Counter

    from hpo import ROOT
    gr = Graph()
    gr.parse(ROOT / "data" / "build" / "ontology_T0.owl", format="xml")
    gs = find_gaps(gr)
    print(len(gs), "certified gaps", Counter((x.cls, x.prop) for x in gs))
