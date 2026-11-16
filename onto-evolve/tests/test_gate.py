from gate import Assertion, Gate, aggregate
from gaps import find_gaps
from hpo import TAGS, read_obo

TERMS = read_obo(TAGS[0])
SEIZURE, FOCAL = "HP:0001250", "HP:0007359"   # Focal-onset seizure is a descendant of Seizure


def gate(curated, **kw):
    return Gate(TERMS, {"OMIM:1"}, {"PAH"}, curated, **kw)


def ext(obj, positive=True, docs=("PMID:1",), latest="2020-01-01", relation="phenotype"):
    return Assertion("OMIM:1", relation, obj, positive, "extracted", list(docs), ["e"] * len(docs), latest)


def test_domain_rejections():
    out = gate([]).run([Assertion("OMIM:999", "phenotype", SEIZURE, docs=["PMID:1"]),
                        ext("NOTAGENE", relation="gene")])
    assert [a.status for a in out] == ["rejected", "rejected"]
    assert "domain" in out[0].reason


def test_known_and_redundant():
    cur = [Assertion("OMIM:1", "phenotype", FOCAL, source="curated", docs=["PMID:9"])]
    out = gate(cur).run([ext(FOCAL), ext(SEIZURE)])
    assert out[0].status == "known"
    assert out[1].status == "redundant"   # Seizure is an ancestor of an asserted term


def test_evidence_threshold():
    out = gate([], k=2).run([ext(SEIZURE)])
    assert out[0].status == "rejected" and "evidence" in out[0].reason


def test_hierarchical_conflict_is_repaired_by_weight():
    # curated: NOT seizure; extracted: focal seizure from one paper -> inconsistent via HPO hierarchy
    cur = [Assertion("OMIM:1", "phenotype", SEIZURE, positive=False, source="curated", docs=["PMID:9"])]
    out = gate(cur).run([ext(FOCAL)])
    assert out[0].status == "rejected" and "conflict" in out[0].reason


def test_extracted_conflict_resolved_by_more_documents():
    strong = ext(FOCAL, docs=("PMID:1", "PMID:2", "PMID:3"))
    weak = ext(SEIZURE, positive=False, docs=("PMID:4",))
    out = gate([]).run([strong, weak])
    assert strong.status == "accepted" and weak.status == "rejected"


def test_reasoner_off_accepts_conflict():
    cur = [Assertion("OMIM:1", "phenotype", SEIZURE, positive=False, source="curated", docs=["PMID:9"])]
    out = gate(cur, use_reasoner=False).run([ext(FOCAL)])
    assert out[0].status == "accepted"


def test_aggregate_counts_independent_docs():
    c = {"disease": "OMIM:1", "relation": "phenotype", "object": SEIZURE, "evidence": "x", "doc_date": "2020-01-01"}
    agg = aggregate([{**c, "doc_id": "PMID:1"}, {**c, "doc_id": "PMID:1"}, {**c, "doc_id": "PMID:2"}])
    assert len(agg) == 1 and agg[0].docs == ["PMID:1", "PMID:2"]


def test_gaps_on_t0(tmp_path):
    from rdflib import Graph

    from hpo import ROOT
    g = Graph()
    g.parse(ROOT / "data" / "build" / "ontology_T0.owl", format="xml")
    gaps = find_gaps(g)
    assert sum(1 for x in gaps if x.prop == "hasCausativeGene") == 84
