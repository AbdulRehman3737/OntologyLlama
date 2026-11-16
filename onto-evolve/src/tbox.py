"""Schema (TBox) for the OntoEvolve ontology, in the same style as the first study's OWL.

Only axioms that are true of the domain are added. Notably, inheritance patterns are NOT
made disjoint per disease (a disease can be reported with several modes).

The existential restrictions are what makes a gap "schema-certified". Under OWL's open
world a missing filler is not an inconsistency, so gaps.py checks them closed-world
(SHACL-style) over asserted + inferred facts.
"""
from __future__ import annotations

from rdflib import OWL, RDF, RDFS, BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection

NS = Namespace("http://example.org/ontoevolve#")
ONTOLOGY_IRI = URIRef("http://example.org/ontoevolve")

CLASSES = {
    "Disease": "A rare disease (OMIM entry).",
    "MendelianDisease": "A disease with a known Mendelian basis; must have a causative gene.",
    "Gene": "A human gene (HGNC symbol).",
    "Phenotype": "An HPO phenotypic abnormality term.",
    "OrganSystem": "A top-level HPO phenotypic abnormality branch.",
    "InheritancePattern": "An HPO mode of inheritance term.",
}
TYPE_CLASSES = ["Disease", "Gene", "Phenotype", "OrganSystem", "InheritancePattern"]

# name: (domain, range, inverse, functional)
OBJECT_PROPERTIES = {
    "hasCausativeGene": ("Disease", "Gene", "causesDisease", False),
    "hasPhenotype": ("Disease", "Phenotype", "isPhenotypeOf", False),
    "hasInheritancePattern": ("Disease", "InheritancePattern", "isInheritancePatternOf", False),
    "affectsOrganSystem": ("Phenotype", "OrganSystem", None, False),
}

# Existential restrictions -> expected slots (class, property, filler class)
EXISTENTIALS = [
    ("MendelianDisease", "hasCausativeGene", "Gene"),
    ("Disease", "hasInheritancePattern", "InheritancePattern"),
    ("Disease", "hasPhenotype", "Phenotype"),
]


def add_tbox(g: Graph) -> Graph:
    g.bind("", NS)
    g.add((ONTOLOGY_IRI, RDF.type, OWL.Ontology))
    for c, comment in CLASSES.items():
        g.add((NS[c], RDF.type, OWL.Class))
        g.add((NS[c], RDFS.label, Literal(c)))
        g.add((NS[c], RDFS.comment, Literal(comment)))
    g.add((NS.MendelianDisease, RDFS.subClassOf, NS.Disease))
    # pairwise disjoint top-level types
    adc = BNode()
    g.add((adc, RDF.type, OWL.AllDisjointClasses))
    lst = BNode()
    Collection(g, lst, [NS[c] for c in TYPE_CLASSES])
    g.add((adc, OWL.members, lst))
    for p, (dom, rng, inv, functional) in OBJECT_PROPERTIES.items():
        g.add((NS[p], RDF.type, OWL.ObjectProperty))
        g.add((NS[p], RDFS.domain, NS[dom]))
        g.add((NS[p], RDFS.range, NS[rng]))
        if functional:
            g.add((NS[p], RDF.type, OWL.FunctionalProperty))
        if inv:
            g.add((NS[inv], RDF.type, OWL.ObjectProperty))
            g.add((NS[inv], OWL.inverseOf, NS[p]))
            g.add((NS[inv], RDFS.domain, NS[rng]))
            g.add((NS[inv], RDFS.range, NS[dom]))
    for cls, prop, filler in EXISTENTIALS:
        r = BNode()
        g.add((r, RDF.type, OWL.Restriction))
        g.add((r, OWL.onProperty, NS[prop]))
        g.add((r, OWL.someValuesFrom, NS[filler]))
        g.add((NS[cls], RDFS.subClassOf, r))
    for dp in ["omimId", "hpoId", "geneSymbol"]:
        g.add((NS[dp], RDF.type, OWL.DatatypeProperty))
    return g
