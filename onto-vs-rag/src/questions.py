"""Generate the benchmark question set with gold answers from the KG.

Every question records: category, subtype, answer_type (KB entity type of the answer),
mode (single | any | list | yesno | abstain), gold (KB local names) or gold_bool, and
alt (extra accepted strings from data/accepted_alternatives.json).

Templated questions use several phrasings per relation. A separate hand-written
"paraphrase" subset uses free phrasing to check the ontology layer is not just tuned
to the templates (note: written by the same author as the layer, so it is not a blind test).
"""
from __future__ import annotations

import json
import random
from collections import Counter

from kg import KG, ROOT, get_kg, local

QUESTIONS_PATH = ROOT / "data" / "questions.jsonl"
ALTS = json.loads((ROOT / "data" / "accepted_alternatives.json").read_text(encoding="utf-8"))
SEED = 42

PLACEHOLDER_METABOLITES = {
    "BiotinDeficiencyMetabolite", "CarnitineDeficiencyMetabolite", "ChlorideIonTransportDefectMetabolite",
    "CopperDeficiencyMetabolite", "DNADamageResponseImpairedMetabolite", "OrganicAcidsMixed",
}
# Classified in the OWL as amino-acid disorders although clinically urea-cycle disorders:
# excluded from class-membership questions so the gold is not contestable.
CONTESTED_CLASS = {"CitrullinemiaTypeI", "ArgininosuccinicAciduria"}

SINGLE_HOP = {
    "gene": ("hasCausativeGene", "Gene", [
        "Which gene is mutated in {D}?", "Mutations in which gene cause {D}?", "What is the causative gene of {D}?"]),
    "enzyme": ("hasDeficientEnzyme", "Enzyme", [
        "Which enzyme or protein is deficient in {D}?", "What enzyme or protein is defective in {D}?",
        "{D} is caused by a deficiency of which enzyme or protein?"]),
    "metabolite": ("accumulatesMetabolite", "Metabolite", [
        "Which metabolite accumulates in {D}?", "What substance builds up in patients with {D}?",
        "In {D}, which metabolite accumulates?"]),
    "treatment": ("treatedWith", "Treatment", [
        "What is the main treatment for {D}?", "How is {D} treated?", "Which therapy is used to manage {D}?"]),
    "inheritance": ("hasInheritancePattern", "InheritancePattern", [
        "What is the inheritance pattern of {D}?", "How is {D} inherited?", "What is the mode of inheritance of {D}?"]),
}

FICTIONAL = [
    ("Which gene is mutated in Harlowe-Brenner syndrome?", "Gene"),
    ("Which enzyme is deficient in Velmont disease?", "Enzyme"),
    ("What metabolite accumulates in Kastrup-Adeyemi syndrome?", "Metabolite"),
    ("How is Tessaro aciduria treated?", "Treatment"),
    ("What is the inheritance pattern of Quillon-Marsh disease?", "InheritancePattern"),
    ("Which disease is caused by mutations in the QZR7 gene?", "Disease"),
    ("Mutations in the TMX19B gene cause which disease?", "Disease"),
    ("Which disease results from a deficiency of glyoxalate transaminidase-4?", "Disease"),
    ("Which gene causes Dunmore-Ito disease?", "Gene"),
    ("What cofactor does the enzyme deficient in Marchetti-Lund syndrome require?", "Cofactor"),
    ("What is the main treatment for Orvald leukoencephalopathy?", "Treatment"),
    ("Which organ systems are affected by Sorensen pellucid myopathy?", "OrganSystem"),
    ("What substance builds up in patients with Brevik-Holm disease?", "Metabolite"),
    ("How is Feldkamp syndrome inherited?", "InheritancePattern"),
    ("Which metabolite accumulates in the disease caused by mutations in the KLPV2 gene?", "Metabolite"),
    ("How is the disease caused by mutations in the WRDQ1 gene treated?", "Treatment"),
    ("Which enzyme or protein is defective in Annecy-Larsen syndrome?", "Enzyme"),
    ("Name one symptom of Ostrander-Kade disease.", "Phenotype"),
    ("Mutations in which gene cause Pelletier-Varga syndrome?", "Gene"),
    ("Which diseases are treated with zentrafolimab?", "Disease"),
]

# Hand-written paraphrases: (question, category, answer_type, mode, gold, alt_key)
PARAPHRASES = [
    ("My child was just diagnosed with PKU. Which gene is involved?", "single_hop", "Gene", "single", ["PAH"], "Phenylketonuria|gene"),
    ("What builds up in the body of someone with alkaptonuria?", "single_hop", "Metabolite", "single", ["HomogentisicAcid"], "Alkaptonuria|metabolite"),
    ("Which vitamin does the defective enzyme in propionic acidemia depend on?", "multi_hop", "Cofactor", "single", ["Biotin"], None),
    ("For a patient with Wilson's disease, what medication is used?", "single_hop", "Treatment", "single", ["PenicillamineTherapy"], "WilsonDisease|treatment"),
    ("Tell me the gene behind Tay-Sachs.", "single_hop", "Gene", "single", ["HEXA"], "TaySachsDisease|gene"),
    ("If someone carries a faulty GALC gene, what condition do they have?", "inverse", "Disease", "single", ["KrabbeDisease"], None),
    ("A missing Hexosaminidase A enzyme leads to what disorder?", "inverse", "Disease", "single", ["TaySachsDisease"], None),
    ("Can Fabry disease be passed down through the X chromosome, or is it autosomal?", "single_hop", "InheritancePattern", "single", ["XLinked"], None),
    ("Which protein fails to work in cystic fibrosis?", "single_hop", "Enzyme", "single", ["CysticFibrosisTransmembraneConductanceRegulator"], None),
    ("What do doctors give patients with tyrosinemia type 1?", "single_hop", "Treatment", "single", ["NitisinoneTherapy"], "TyrosinemiaTypeI|treatment"),
    ("In MCAD deficiency, what is the recommended management?", "single_hop", "Treatment", "single", ["AvoidanceOfFasting"], None),
    ("Methylmalonic acidemia: the broken enzyme needs which cofactor to function?", "multi_hop", "Cofactor", "single", ["VitaminB12"], None),
    ("The SMPD1 gene is linked to which illness?", "inverse", "Disease", "single", ["NiemannPickDiseaseTypeA"], None),
    ("What compound piles up in Refsum disease?", "single_hop", "Metabolite", "single", ["PhytanicAcid"], None),
    ("I have a patient with an HPRT1 mutation. What accumulates in their blood?", "multi_hop", "Metabolite", "single", ["UricAcid"], None),
    ("Someone has a mutation in ATP7A. How would that disease be treated?", "multi_hop", "Treatment", "single", ["CopperHistidineInjections"], None),
    ("Which body systems do the symptoms of Gaucher disease involve?", "multi_hop", "OrganSystem", "list", None, None),
    ("Give me every disease you know of that is X-linked.", "list", "Disease", "list", None, None),
    ("Which conditions cause cardiomyopathy?", "list", "Disease", "list", None, None),
    ("Name the disorders for which enzyme replacement therapy is used.", "list", "Disease", "list", None, None),
    ("Is Pompe disease considered a lysosomal storage disorder?", "yes_no", "Disease", "yesno", True, None),
    ("Would you classify Refsum disease as a fatty acid oxidation disorder?", "yes_no", "Disease", "yesno", False, None),
    ("Are Menkes disease and Lesch-Nyhan syndrome inherited the same way?", "yes_no", "InheritancePattern", "yesno", True, None),
    ("Do Wilson disease and familial hypercholesterolemia share a mode of inheritance?", "yes_no", "InheritancePattern", "yesno", False, None),
    ("Which disorders respond to cofactors because their faulty enzyme needs one?", "inferred", "Disease", "list", None, None),
    ("What gene is responsible for the Zellwegger syndrome?", "single_hop", "Gene", "single", ["PEX1"], "ZellwegerSyndrome|gene"),
    ("What is the culprit gene in Hurler syndrome?", "single_hop", "Gene", "single", ["IDUA"], None),
    ("In McArdle disease, which enzyme is missing?", "single_hop", "Enzyme", "single", ["Myophosphorylase"], None),
    ("Which gene, when mutated, gives rise to the disease that is treated with nicotinamide?", "multi_hop", "Gene", "single", ["SLC6A19"], None),
    ("What is the treatment for the Brannigan-Holt variant of PKU described in your sources?", "unanswerable", "Treatment", "abstain", None, None),
]


def _labels(kg: KG, names) -> list[str]:
    from kg import NS
    return [kg.label(NS[n]) for n in names]


def generate(kg: KG | None = None) -> list[dict]:
    kg = kg or get_kg()
    rng = random.Random(SEED)
    L = kg.label
    D = list(kg.diseases)
    qs: list[dict] = []

    def add(category, subtype, question, answer_type, mode, gold=None, gold_bool=None, alt_key=None, paraphrase=False):
        q = {
            "id": f"q{len(qs) + 1:03d}", "category": category, "subtype": subtype, "question": question,
            "answer_type": answer_type, "mode": mode, "gold": gold or [], "gold_bool": gold_bool,
            "alt": ALTS.get(alt_key, []) if alt_key else [], "paraphrase": paraphrase,
        }
        q["gold_labels"] = _labels(kg, q["gold"])
        qs.append(q)

    # ---- single-hop: 18 per relation (inheritance stratified so it is not ~all "autosomal recessive")
    for rel, (prop, atype, templates) in SINGLE_HOP.items():
        pool = D
        if rel == "metabolite":
            pool = [d for d in D if not {local(o) for o in kg.objects(d, prop)} & PLACEHOLDER_METABOLITES]
        if rel == "inheritance":
            non_ar = [d for d in D if local(kg.objects(d, prop)[0]) != "AutosomalRecessive"]
            ar = [d for d in D if d not in non_ar]
            chosen = non_ar + rng.sample(ar, 18 - len(non_ar))
        else:
            chosen = rng.sample(pool, 18)
        for d in chosen:
            add("single_hop", rel, rng.choice(templates).format(D=L(d)), atype, "single",
                gold=[local(o) for o in kg.objects(d, prop)], alt_key=f"{local(d)}|{rel}")
    for d in rng.sample(D, 10):
        add("single_hop", "symptom", rng.choice(["Name one symptom of {D}.", "What is a clinical feature of {D}?"]).format(D=L(d)),
            "Phenotype", "any", gold=[local(o) for o in kg.objects(d, "hasSymptom")])

    # ---- inverse: 25 gene->disease, 25 enzyme->disease
    for g in rng.sample(kg.instances("Gene"), 25):
        dis = kg.objects(g, "causesDisease")
        add("inverse", "gene_to_disease", rng.choice([
            "Mutations in the {G} gene cause which disease?", "Which disease is caused by mutations in {G}?"]).format(G=L(g)),
            "Disease", "single", gold=[local(x) for x in dis])
    for e in rng.sample(kg.instances("Enzyme"), 25):
        dis = kg.objects(e, "isDeficientEnzymeOf")
        add("inverse", "enzyme_to_disease", rng.choice([
            "Deficiency of {E} causes which disease?", "Which disease results from a deficiency of {E}?"]).format(E=L(e)),
            "Disease", "single", gold=[local(x) for x in dis])

    # ---- multi-hop
    for d in D:
        cof = [c for e in kg.objects(d, "hasDeficientEnzyme") for c in kg.objects(e, "requiresCofactor")]
        if cof:
            add("multi_hop", "disease_enzyme_cofactor", rng.choice([
                "Which cofactor does the enzyme deficient in {D} require?",
                "What vitamin cofactor is needed by the enzyme that is defective in {D}?"]).format(D=L(d)),
                "Cofactor", "single", gold=[local(c) for c in cof])
    for d in rng.sample(D, 20):
        organs = sorted({local(o) for p in kg.objects(d, "hasSymptom") for o in kg.objects(p, "affectsOrganSystem")})
        add("multi_hop", "disease_symptom_organ", f"Which organ systems are affected by the symptoms of {L(d)}?",
            "OrganSystem", "list", gold=organs)
    genes = kg.instances("Gene")
    for g in rng.sample([g for g in genes if not {local(m) for d in kg.objects(g, "causesDisease")
                                                   for m in kg.objects(d, "accumulatesMetabolite")} & PLACEHOLDER_METABOLITES], 18):
        d = kg.objects(g, "causesDisease")[0]
        add("multi_hop", "gene_disease_metabolite",
            f"Which metabolite accumulates in the disease caused by mutations in the {L(g)} gene?",
            "Metabolite", "single", gold=[local(m) for m in kg.objects(d, "accumulatesMetabolite")],
            alt_key=f"{local(d)}|metabolite")
    for g in rng.sample(genes, 18):
        d = kg.objects(g, "causesDisease")[0]
        add("multi_hop", "gene_disease_treatment", f"How is the disease caused by mutations in the {L(g)} gene treated?",
            "Treatment", "single", gold=[local(t) for t in kg.objects(d, "treatedWith")], alt_key=f"{local(d)}|treatment")

    # ---- list / aggregation
    for sc in ["OrganicAcidemia", "FattyAcidOxidationDisorder", "LysosomalStorageDisorder",
               "GlycogenStorageDisease", "PeroxisomalDisorder"]:
        add("list", "class_members", f"List all {kg.class_label(sc).lower()}s in the knowledge base.", "Disease", "list",
            gold=[local(x) for x in kg.instances(sc)])
    add("list", "inheritance_members", "Which diseases are inherited in an X-linked manner?", "Disease", "list",
        gold=[local(x) for x in kg.subjects("hasInheritancePattern", kg.surface_forms["x-linked"])])
    shared_sym = [p for p in kg.instances("Phenotype") if len(kg.objects(p, "isSymptomOf")) >= 2]
    for p in rng.sample(shared_sym, min(14, len(shared_sym))):
        add("list", "symptom_to_diseases", f"Which diseases present with {L(p).lower()}?", "Disease", "list",
            gold=[local(x) for x in kg.objects(p, "isSymptomOf")])
    for t in [t for t in kg.instances("Treatment") if len(kg.objects(t, "isTreatmentFor")) >= 2]:
        add("list", "treatment_to_diseases", f"Which diseases are treated with {L(t).lower()}?", "Disease", "list",
            gold=[local(x) for x in kg.objects(t, "isTreatmentFor")])
    for o in kg.instances("OrganSystem"):
        dis = sorted({local(d) for p in kg.subjects("affectsOrganSystem", o) for d in kg.objects(p, "isSymptomOf")})
        if 2 <= len(dis) <= 10:
            add("list", "organ_to_diseases", f"Which diseases have symptoms affecting the {L(o).lower()}?", "Disease", "list", gold=dis)

    # ---- yes/no: class membership (15) + shared inheritance (15)
    classes = ["AminoAcidMetabolismDisorder", "OrganicAcidemia", "UreaCycleDisorder", "FattyAcidOxidationDisorder",
               "LysosomalStorageDisorder", "GlycogenStorageDisease", "PeroxisomalDisorder"]
    eligible = [d for d in D if kg.disease_class(d) in classes and local(d) not in CONTESTED_CLASS]
    for i, d in enumerate(rng.sample(eligible, 15)):
        truth = i % 2 == 0
        cls = kg.disease_class(d) if truth else rng.choice([c for c in classes if c != kg.disease_class(d)])
        cl = kg.class_label(cls).lower()
        add("yes_no", "class_membership", f"Is {L(d)} {'an' if cl[0] in 'aeiou' else 'a'} {cl}?", "Disease", "yesno", gold_bool=truth)
    inh = {d: kg.objects(d, "hasInheritancePattern")[0] for d in D}
    non_ar = [d for d in D if local(inh[d]) != "AutosomalRecessive"]
    for i in range(15):
        truth = i % 2 == 0
        if truth:
            a, b = rng.sample(non_ar if i % 4 == 0 else D, 2)
            while inh[a] != inh[b]:
                a, b = rng.sample(D, 2)
        else:
            a = rng.choice(non_ar)
            b = rng.choice([d for d in D if inh[d] != inh[a]])
        add("yes_no", "shared_inheritance", f"Do {L(a)} and {L(b)} have the same inheritance pattern?",
            "InheritancePattern", "yesno", gold_bool=truth)

    # ---- inferred (HermiT): 1 list + 4 yes + 4 no
    cr = [d for d in D if local(d) in kg.cofactor_responsive]
    add("inferred", "cofactor_responsive_list",
        "Which diseases are cofactor-responsive disorders, meaning their deficient enzyme requires a cofactor?",
        "Disease", "list", gold=[local(d) for d in cr])
    for d in cr:
        add("inferred", "cofactor_responsive_yesno", f"Is {L(d)} a cofactor-responsive disorder?", "Disease", "yesno", gold_bool=True)
    for d in rng.sample([d for d in D if d not in cr], 4):
        add("inferred", "cofactor_responsive_yesno", f"Is {L(d)} a cofactor-responsive disorder?", "Disease", "yesno", gold_bool=False)

    # ---- unanswerable (fictional entities)
    for qtext, atype in FICTIONAL:
        add("unanswerable", "fictional_entity", qtext, atype, "abstain")

    # ---- hand-written paraphrases
    for qtext, cat, atype, mode, gold, alt_key in PARAPHRASES:
        if mode == "yesno":
            add(cat, "paraphrase", qtext, atype, mode, gold_bool=gold, paraphrase=True)
        elif mode == "list":
            add(cat, "paraphrase", qtext, atype, mode, gold=_paraphrase_list_gold(kg, qtext), paraphrase=True)
        else:
            add(cat, "paraphrase", qtext, atype, mode, gold=gold, alt_key=alt_key, paraphrase=True)
    return qs


def _paraphrase_list_gold(kg: KG, q: str) -> list[str]:
    from kg import NS
    if "Gaucher" in q:
        return sorted({local(o) for p in kg.objects(NS.GaucherDisease, "hasSymptom") for o in kg.objects(p, "affectsOrganSystem")})
    if "X-linked" in q:
        return [local(x) for x in kg.subjects("hasInheritancePattern", NS.XLinked)]
    if "cardiomyopathy" in q:
        return [local(x) for x in kg.objects(NS.Cardiomyopathy, "isSymptomOf")]
    if "enzyme replacement" in q:
        return [local(x) for x in kg.objects(NS.EnzymeReplacementTherapy, "isTreatmentFor")]
    if "cofactors" in q:
        return list(kg.cofactor_responsive)
    raise ValueError(q)


def save(qs: list[dict]) -> None:
    with open(QUESTIONS_PATH, "w", encoding="utf-8") as fh:
        for q in qs:
            fh.write(json.dumps(q, ensure_ascii=False) + "\n")


def load() -> list[dict]:
    with open(QUESTIONS_PATH, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


if __name__ == "__main__":
    qs = generate()
    save(qs)
    print(len(qs), "questions")
    print(Counter(q["category"] for q in qs))
    rng = random.Random(1)
    for q in rng.sample(qs, 8):
        print("-", q["category"], "|", q["question"], "->", q["gold_labels"] or q["gold_bool"])
