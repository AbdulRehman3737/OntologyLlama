"""Knowledge graph loading: rdflib graph + inverse materialisation + HermiT reasoning.

The source OWL file is never modified. The missing defined-class axiom for
CofactorResponsiveDisorder is added in memory before running the reasoner.
"""
from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path

from rdflib import OWL, RDF, RDFS, Graph, Namespace, URIRef

ROOT = Path(__file__).resolve().parent.parent
OWL_PATH = ROOT / "data" / "ontology.owl"
INFERRED_CACHE = ROOT / "data" / "inferred.json"

NS = Namespace("http://www.semanticweb.org/rareGeneticDiseases/ontology#")

# Entity types used throughout the benchmark (leaf type for each individual).
ENTITY_TYPES = [
    "Disease", "Gene", "Enzyme", "Metabolite", "Phenotype",
    "OrganSystem", "Treatment", "Cofactor", "InheritancePattern",
]
DISEASE_SUBCLASSES = [
    "AminoAcidMetabolismDisorder", "OrganicAcidemia", "UreaCycleDisorder",
    "FattyAcidOxidationDisorder", "LysosomalStorageDisorder", "GlycogenStorageDisease",
    "PeroxisomalDisorder", "OtherMonogenicDisorder",
]


def local(iri) -> str:
    return str(iri).split("#")[-1]


def run_reasoner() -> list[str]:
    """Run HermiT via owlready2 and return local names of inferred CofactorResponsiveDisorder members."""
    import owlready2 as o2

    world = o2.World()
    with open(OWL_PATH, "rb") as fh:
        onto = world.get_ontology("http://www.semanticweb.org/rareGeneticDiseases/ontology").load(fileobj=fh)
    ns = onto.get_namespace(str(NS))
    with onto:
        ns.CofactorResponsiveDisorder.equivalent_to.append(
            ns.Disease & ns.hasDeficientEnzyme.some(ns.Enzyme & ns.requiresCofactor.some(ns.Cofactor))
        )
    o2.sync_reasoner_hermit(world, infer_property_values=False, debug=0)
    return sorted(ind.name for ind in ns.CofactorResponsiveDisorder.instances())


def inferred_members(refresh: bool = False) -> list[str]:
    if INFERRED_CACHE.exists() and not refresh:
        return json.loads(INFERRED_CACHE.read_text())["CofactorResponsiveDisorder"]
    members = run_reasoner()
    INFERRED_CACHE.write_text(json.dumps({"CofactorResponsiveDisorder": members}, indent=2))
    return members


class KG:
    def __init__(self, refresh_reasoner: bool = False):
        g = Graph()
        g.parse(OWL_PATH, format="xml")
        self.asserted_triples = len(g)
        # Materialise owl:inverseOf
        for p, _, q in list(g.triples((None, OWL.inverseOf, None))):
            for s, _, o in list(g.triples((None, p, None))):
                g.add((o, q, s))
            for s, _, o in list(g.triples((None, q, None))):
                g.add((o, p, s))
        # Reasoner-inferred class membership
        self.cofactor_responsive = inferred_members(refresh_reasoner)
        for name in self.cofactor_responsive:
            g.add((NS[name], RDF.type, NS.CofactorResponsiveDisorder))
        self.g = g

    # ---------- basic accessors ----------
    def label(self, iri) -> str:
        lab = self.g.value(URIRef(iri) if not isinstance(iri, URIRef) else iri, RDFS.label)
        return str(lab) if lab is not None else local(iri)

    def objects(self, s, prop: str) -> list[URIRef]:
        return sorted(set(self.g.objects(s, NS[prop])), key=str)

    def subjects(self, prop: str, o) -> list[URIRef]:
        return sorted(set(self.g.subjects(NS[prop], o)), key=str)

    def instances(self, cls: str) -> list[URIRef]:
        return sorted(set(self.g.subjects(RDF.type, NS[cls])), key=str)

    @cached_property
    def diseases(self) -> list[URIRef]:
        out = set()
        for sc in DISEASE_SUBCLASSES:
            out.update(self.instances(sc))
        return sorted(out, key=str)

    @cached_property
    def entity_type(self) -> dict[URIRef, str]:
        """Map every individual to its benchmark type."""
        m: dict[URIRef, str] = {d: "Disease" for d in self.diseases}
        for t in ENTITY_TYPES:
            if t == "Disease":
                continue
            for i in self.instances(t):
                m.setdefault(i, t)
        return m

    def disease_class(self, d) -> str:
        for sc in DISEASE_SUBCLASSES:
            if (d, RDF.type, NS[sc]) in self.g:
                return sc
        raise KeyError(d)

    def class_label(self, cls: str) -> str:
        return self.label(NS[cls])

    @cached_property
    def surface_forms(self) -> dict[str, URIRef]:
        """Lower-cased surface form -> IRI (labels + gene symbols + local names)."""
        forms: dict[str, URIRef] = {}
        for iri in self.entity_type:
            forms[self.label(iri).lower()] = iri
            for sym in self.g.objects(iri, NS.geneSymbol):
                forms[str(sym).lower()] = iri
        return forms

    def triples_of(self, s) -> list[tuple[URIRef, URIRef, URIRef]]:
        return [(s, p, o) for p, o in self.g.predicate_objects(s) if str(p).startswith(str(NS))]

    def sparql(self, q: str):
        return self.g.query(q, initNs={"": NS, "rdfs": RDFS, "rdf": RDF})


_KG: KG | None = None


def get_kg() -> KG:
    global _KG
    if _KG is None:
        _KG = KG()
    return _KG


if __name__ == "__main__":
    kg = KG(refresh_reasoner=True)
    print("asserted triples:", kg.asserted_triples, "after materialisation:", len(kg.g))
    print("diseases:", len(kg.diseases))
    from collections import Counter
    print(Counter(kg.entity_type.values()))
    print("CofactorResponsiveDisorder (HermiT):", kg.cofactor_responsive)
