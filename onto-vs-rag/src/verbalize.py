"""Turn the KG into English text chunks for the vector-RAG arm.

Every asserted fact, every inverse and the reasoner's inferred class membership is
expressed in text, so RAG sees the same knowledge as the ontology layer. Chunks are
entity-centred (the usual way a KB is converted for RAG), plus one chunk per class /
inheritance pattern / organ system listing its members, so aggregation questions are
answerable from a single chunk too.
"""
from __future__ import annotations

import json

from kg import DISEASE_SUBCLASSES, KG, ROOT, get_kg, local

CHUNKS_PATH = ROOT / "data" / "rag_chunks.json"


def _join(names: list[str]) -> str:
    if not names:
        return "none"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def build_chunks(kg: KG) -> list[dict]:
    L = kg.label
    chunks: list[dict] = []

    def add(cid: str, text: str):
        chunks.append({"id": cid, "text": text})

    for d in kg.diseases:
        n = L(d)
        cl = kg.class_label(kg.disease_class(d)).lower()
        s = [f"{n} is {'an' if cl[0] in 'aeiou' else 'a'} {cl}."]
        if local(d) in kg.cofactor_responsive:
            s.append(f"{n} is a cofactor-responsive disorder.")
        gene = [L(x) for x in kg.objects(d, "hasCausativeGene")]
        enz = [L(x) for x in kg.objects(d, "hasDeficientEnzyme")]
        met = [L(x) for x in kg.objects(d, "accumulatesMetabolite")]
        sym = [L(x) for x in kg.objects(d, "hasSymptom")]
        trt = [L(x) for x in kg.objects(d, "treatedWith")]
        inh = [L(x) for x in kg.objects(d, "hasInheritancePattern")]
        s.append(f"It is caused by mutations in the {_join(gene)} gene.")
        s.append(f"The deficient enzyme or protein is {_join(enz)}.")
        s.append(f"The metabolite that accumulates is {_join(met)}.")
        s.append(f"Symptoms include {_join(sym).lower()}.")
        s.append(f"It is treated with {_join(trt).lower()}.")
        s.append(f"Inheritance is {_join(inh).lower()}.")
        add(f"disease:{local(d)}", " ".join(s))

    for g in kg.instances("Gene"):
        dis = [L(x) for x in kg.objects(g, "causesDisease")]
        prot = [L(x) for x in kg.objects(g, "encodes")]
        add(f"gene:{local(g)}", f"The {L(g)} gene encodes {_join(prot)}. Mutations in {L(g)} cause {_join(dis)}.")

    for e in kg.instances("Enzyme"):
        gene = [L(x) for x in kg.objects(e, "encodedBy")]
        dis = [L(x) for x in kg.objects(e, "isDeficientEnzymeOf")]
        cof = [L(x) for x in kg.objects(e, "requiresCofactor")]
        t = f"{L(e)} is encoded by the {_join(gene)} gene. Deficiency of {L(e)} causes {_join(dis)}."
        t += f" {L(e)} requires the cofactor {_join(cof)}." if cof else f" {L(e)} has no cofactor recorded."
        add(f"enzyme:{local(e)}", t)

    for m in kg.instances("Metabolite"):
        dis = [L(x) for x in kg.objects(m, "isAccumulatedIn")]
        add(f"metabolite:{local(m)}", f"{L(m)} accumulates in {_join(dis)}.")

    for p in kg.instances("Phenotype"):
        dis = [L(x) for x in kg.objects(p, "isSymptomOf")]
        org = [L(x) for x in kg.objects(p, "affectsOrganSystem")]
        add(f"phenotype:{local(p)}", f"{L(p)} affects the {_join(org)}. {L(p)} is a symptom of {_join(dis)}.")

    for t in kg.instances("Treatment"):
        dis = [L(x) for x in kg.objects(t, "isTreatmentFor")]
        add(f"treatment:{local(t)}", f"{L(t)} is a treatment for {_join(dis)}.")

    for c in kg.instances("Cofactor"):
        enz = [L(x) for x in kg.subjects("requiresCofactor", c)]
        add(f"cofactor:{local(c)}", f"{L(c)} is a cofactor required by {_join(enz)}.")

    for o in kg.instances("OrganSystem"):
        phen = kg.subjects("affectsOrganSystem", o)
        dis = sorted({L(d) for p in phen for d in kg.objects(p, "isSymptomOf")})
        add(f"organ:{local(o)}", f"Symptoms affecting the {L(o)} are {_join([L(p) for p in phen]).lower()}. "
            f"Diseases with symptoms affecting the {L(o)}: {_join(dis)}.")

    for ip in kg.instances("InheritancePattern"):
        dis = [L(x) for x in kg.subjects("hasInheritancePattern", ip)]
        add(f"inheritance:{local(ip)}", f"Diseases with {L(ip).lower()} inheritance: {_join(dis)}.")

    for sc in DISEASE_SUBCLASSES + ["CofactorResponsiveDisorder"]:
        members = [L(x) for x in (kg.instances(sc) if sc != "CofactorResponsiveDisorder"
                                  else [d for d in kg.diseases if local(d) in kg.cofactor_responsive])]
        extra = (" A cofactor-responsive disorder is a disease whose deficient enzyme requires a cofactor."
                 if sc == "CofactorResponsiveDisorder" else "")
        add(f"class:{sc}", f"{kg.class_label(sc)}s in the knowledge base: {_join(members)}.{extra}")

    return chunks


def get_chunks(refresh: bool = False) -> list[dict]:
    if CHUNKS_PATH.exists() and not refresh:
        return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    chunks = build_chunks(get_kg())
    CHUNKS_PATH.write_text(json.dumps(chunks, indent=1, ensure_ascii=False), encoding="utf-8")
    return chunks


if __name__ == "__main__":
    ch = get_chunks(refresh=True)
    print(len(ch), "chunks")
    for c in ch[:2] + ch[-3:]:
        print("-", c["id"], "|", c["text"])
