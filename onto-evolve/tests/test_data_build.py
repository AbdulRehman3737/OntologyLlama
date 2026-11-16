import json

import pytest

from data_build import BUILD, MENDELIAN_MODES, is_mendelian_mode
from hpo import TAGS, ancestors, organ_systems, pmids, read_obo


@pytest.fixture(scope="module")
def changes():
    return [json.loads(l) for l in open(BUILD / "curator_changes.jsonl", encoding="utf-8")]


@pytest.fixture(scope="module")
def sl():
    return json.loads((BUILD / "slice.json").read_text(encoding="utf-8"))


def test_obo_parse():
    t = read_obo(TAGS[0])
    assert t["HP:0001250"].name == "Seizure"
    assert "HP:0000118" in ancestors(t, "HP:0001250")
    assert 20 <= len(organ_systems(t)) <= 30


def test_mendelian_modes():
    t = read_obo(TAGS[0])
    assert is_mendelian_mode(t, "HP:0000007")          # autosomal recessive
    assert is_mendelian_mode(t, "HP:0001419")          # X-linked recessive (descendant)
    assert not is_mendelian_mode(t, "HP:0001427")      # mitochondrial
    assert MENDELIAN_MODES


def test_pmid_parse():
    assert pmids("PMID:123;OMIM:456;PMID:789") == ["123", "789"]


def test_changes_are_stable_and_first_seen(changes):
    keys = [(c["disease"], c["relation"], c["object"]) for c in changes]
    assert len(keys) == len(set(keys)), "each change appears once (first release it appeared in)"
    assert all(1 <= c["step"] <= len(TAGS) - 1 for c in changes)
    # anomalous v2025-08-11 gene spike must be filtered out by the stability rule
    assert sum(1 for c in changes if c["relation"] == "gene" and c["tag"] == "v2025-08-11") < 300


def test_slice_disjoint_and_sized(sl):
    sets = ["enrichment", "control", "gap_gene_filled", "gap_gene_unfilled"]
    for i, a in enumerate(sets):
        for b in sets[i + 1:]:
            assert not set(sl[a]) & set(sl[b]), (a, b)
    assert len(sl["enrichment"]) == 100 and len(sl["control"]) == 30


def test_controls_have_no_changes(changes, sl):
    changed = {c["disease"] for c in changes}
    assert not changed & set(sl["control"])


def test_owl_consistent_with_hermit():
    import owlready2 as o2
    w = o2.World()
    with open(BUILD / "ontology_T0.owl", "rb") as fh:
        onto = w.get_ontology("http://example.org/ontoevolve").load(fileobj=fh)
    o2.sync_reasoner_hermit(w, infer_property_values=False, debug=0)  # raises if inconsistent
    assert len(list(onto.individuals())) > 1000
