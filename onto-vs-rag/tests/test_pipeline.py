from collections import Counter

import pytest

from grade import grade, is_abstention
from kg import NS, get_kg, local
from ontology_layer import get_layer
from questions import generate
from textmatch import get_matcher


@pytest.fixture(scope="module")
def kg():
    return get_kg()


@pytest.fixture(scope="module")
def qs(kg):
    return generate(kg)


# ---------------------------------------------------------------- KG
def test_kg_counts(kg):
    assert len(kg.diseases) == 50
    c = Counter(kg.entity_type.values())
    assert c["Gene"] == 50 and c["Enzyme"] == 50 and c["InheritancePattern"] == 3 and c["Cofactor"] == 2
    for d in kg.diseases:
        assert len(kg.objects(d, "hasCausativeGene")) == 1
        assert len(kg.objects(d, "hasInheritancePattern")) == 1
        assert kg.objects(d, "hasSymptom")


def test_inverses_materialised(kg):
    assert NS.Phenylketonuria in kg.objects(NS.PAH, "causesDisease")
    assert NS.PhenylalanineHydroxylase in kg.objects(NS.PAH, "encodes")


def test_reasoner_infers_cofactor_responsive(kg):
    assert set(kg.cofactor_responsive) == {"BiotinidaseDeficiency", "HolocarboxylaseSynthetaseDeficiency",
                                           "MethylmalonicAcidemia", "PropionicAcidemia"}


# ---------------------------------------------------------------- questions
def test_question_counts(qs):
    c = Counter(q["category"] for q in qs)
    assert len(qs) >= 300
    assert c["unanswerable"] >= 20 and c["multi_hop"] >= 60 and c["list"] >= 35


def test_gold_reproducible_by_sparql(kg, qs):
    """Single-hop gold must equal an independent SPARQL lookup."""
    props = {"gene": "hasCausativeGene", "enzyme": "hasDeficientEnzyme", "metabolite": "accumulatesMetabolite",
             "treatment": "treatedWith", "inheritance": "hasInheritancePattern"}
    lab = {kg.label(d): local(d) for d in kg.diseases}
    for q in qs:
        if q["category"] != "single_hop" or q["subtype"] not in props or q["paraphrase"]:
            continue
        dname = next(n for n in sorted(lab, key=len, reverse=True) if n in q["question"])
        res = kg.sparql(f"SELECT ?x WHERE {{ :{lab[dname]} :{props[q['subtype']]} ?x }}")
        assert sorted(local(r[0]) for r in res) == sorted(q["gold"]), q["question"]


def test_planner_matches_gold(qs):
    layer = get_layer()
    misses = []
    for q in qs:
        p = layer.plan(q["question"])
        if q["mode"] == "yesno":
            ok = p.truth is q["gold_bool"]
        elif q["mode"] == "abstain":
            ok = p.kind in ("none", "empty")
        elif q["mode"] == "list":
            ok = set(p.results) == set(q["gold"])
        else:
            ok = bool(set(p.results) & set(q["gold"])) and set(p.results) <= set(q["gold"])
        if not ok:
            misses.append(q["question"])
    # The one known miss is the deliberate trap question (a fictional variant of a real disease).
    assert misses == ["What is the treatment for the Brannigan-Holt variant of PKU described in your sources?"]


def test_linker_resolves_every_disease_and_gene_name(kg):
    m = get_matcher()
    for d in kg.diseases:
        assert local(d) in m.entities(f"Tell me about {kg.label(d)}.", "Disease")
    for g in kg.instances("Gene"):
        assert local(g) in m.entities(f"The {kg.label(g)} gene.", "Gene")


def test_fictional_entities_do_not_link():
    layer = get_layer()
    for q in ["Which gene is mutated in Harlowe-Brenner syndrome?", "Which disease is caused by mutations in the QZR7 gene?",
              "What is the main treatment for Orvald leukoencephalopathy?"]:
        assert layer.plan(q).kind in ("none", "empty")


# ---------------------------------------------------------------- grader
Q_GENE = {"answer_type": "Gene", "mode": "single", "gold": ["PAH"], "alt": []}
Q_MSUD = {"answer_type": "Gene", "mode": "single", "gold": ["BCKDHA"], "alt": ["BCKDHB", "DBT"]}
Q_LIST = {"answer_type": "Disease", "mode": "list", "gold": ["FabryDisease", "MenkesDisease"]}
Q_YN = {"answer_type": "Disease", "mode": "yesno", "gold": [], "gold_bool": True}
Q_ABS = {"answer_type": "Gene", "mode": "abstain", "gold": []}


@pytest.mark.parametrize("ans,correct,strict,abst,hall", [
    ("Phenylketonuria is caused by mutations in the PAH gene.", True, True, False, False),
    ("It is caused by the PKN2A gene.", False, False, False, True),
    ("Either PAH or BCKDHA.", True, False, False, False),
    ("I don't know.", False, False, True, False),
])
def test_grade_single(ans, correct, strict, abst, hall):
    g = grade(Q_GENE, ans)
    assert (g["correct"], g["strict"], g["abstained"], g["hallucinated"]) == (correct, strict, abst, hall)


def test_grade_list_separator_blocks_cross_comma_match():
    q = {"answer_type": "Phenotype", "mode": "any", "gold": ["CerebellarAtaxia", "Telangiectasia"], "alt": [],
         "question": "Name one symptom of Ataxia-Telangiectasia."}
    assert grade(q, "Cerebellar Ataxia, Telangiectasia.")["correct"]


def test_grade_typo_tolerance_and_echo_masking():
    q = {"answer_type": "Treatment", "mode": "single", "gold": ["LowFatDiet"], "alt": [], "question": "How is Malonic Aciduria treated?"}
    assert grade(q, "Malonic Aciduria is treated with Low-Faat Diet.")["correct"]
    q2 = {"answer_type": "Enzyme", "mode": "single", "gold": ["CarnitinePalmitoyltransferase2"], "alt": [],
          "question": "What enzyme or protein is defective in Carnitine Palmitoyltransferase II Deficiency?"}
    # echoing the disease name must not earn the enzyme answer
    assert not grade(q2, "The enzyme defective in Carnitine Palmitoyltransferase II Deficiency is not specified.")["correct"]
    q3 = {"answer_type": "Gene", "mode": "single", "gold": ["PAH"], "alt": [], "question": "Which gene is mutated in PKU?"}
    assert not grade(q3, "It is the PAX gene.")["correct"]  # short symbols never fuzzy-match


def test_grade_accepted_alternative():
    g = grade(Q_MSUD, "MSUD is caused by mutations in BCKDHB.")
    assert g["correct"] and g["strict"]


def test_grade_list():
    g = grade(Q_LIST, "Fabry disease, Menkes disease and Wilson disease.")
    assert g["precision"] == pytest.approx(2 / 3) and g["recall"] == 1 and g["correct"] and not g["strict"]


def test_grade_yesno_and_abstain():
    assert grade(Q_YN, "Yes, it is.")["correct"]
    assert not grade(Q_YN, "No.")["correct"]
    assert grade(Q_ABS, "I don't know; that disease is not in the knowledge base.")["correct"]
    assert not grade(Q_ABS, "It is caused by the PAH gene.")["correct"]
    assert is_abstention("The context does not contain this information.")
