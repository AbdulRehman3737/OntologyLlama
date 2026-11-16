"""Build the OntoEvolve pilot: stable curator changes, the disease slice and the T0 ontology.

Outputs (data/build/):
  curator_changes.jsonl  every stable addition between consecutive releases (phenotype, inheritance, gene)
  slice.json             pilot disease sets (enrichment, control, gap experiments)
  ontology_T0.owl        RDF/XML OWL of the slice at T0 (TBox from tbox.py + ABox from HPO v2023-06-06)

"Stable" = first appears in release i and is still present in the final release. This removes
the anomalous v2025-08-11 gene links (+2,188 then -2,073).

Usage: uv run python src/data_build.py [--pilot 100] [--controls 30] [--gap-unfilled 50]
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict

from rdflib import RDF, RDFS, Graph, Literal

from hpo import ROOT, TAGS, ancestors, organ_systems, pmids, read_g2d, read_hpoa, read_obo
from tbox import NS, add_tbox

BUILD = ROOT / "data" / "build"
MENDELIAN_MODES = {"HP:0000006", "HP:0000007", "HP:0001417", "HP:0001450"}  # AD, AR, X-linked, Y-linked
SEED = 42


def release_facts(tag: str) -> dict:
    h = read_hpoa(tag)
    g = read_g2d(tag)
    omim = h[h.database_id.str.startswith("OMIM:")]
    facts = {"phenotype": defaultdict(list), "inheritance": defaultdict(list), "gene": {}}
    for d, hp, ref, ev, asp in zip(omim.database_id, omim.hpo_id, omim.reference, omim.evidence, omim.aspect):
        if asp == "P":
            facts["phenotype"][(d, hp)].append((ref, ev))
        elif asp == "I":
            facts["inheritance"][(d, hp)].append((ref, ev))
    for d, sym in zip(g.disease_id, g.gene_symbol):
        if d.startswith("OMIM:"):
            facts["gene"][(d, sym)] = [("", "")]
    facts["names"] = dict(zip(h.database_id, h.disease_name))
    return facts


def stable_changes(all_facts: list[dict]) -> list[dict]:
    final = all_facts[-1]
    rows = []
    for rel in ["phenotype", "inheritance", "gene"]:
        seen = set(all_facts[0][rel])
        for i in range(1, len(TAGS)):
            cur = all_facts[i][rel]
            for key in sorted(set(cur) - seen):
                if key in final[rel]:
                    refs = [r for r, _ in cur[key]]
                    evs = sorted({e for _, e in cur[key] if e})
                    rows.append({"step": i, "tag": TAGS[i], "disease": key[0], "relation": rel, "object": key[1],
                                 "pmids": sorted({p for r in refs for p in pmids(r)}), "evidence": evs})
            seen |= set(cur)
    return rows


def is_mendelian_mode(terms, hp: str) -> bool:
    return hp in MENDELIAN_MODES or bool(ancestors(terms, hp) & MENDELIAN_MODES)


def select_slice(f0: dict, changes: list[dict], n_pilot: int, n_control: int, n_unfilled: int) -> dict:
    rng = random.Random(SEED)
    terms0 = read_obo(TAGS[0])
    d_gene0 = {d for d, _ in f0["gene"]}
    d_phen0 = {d for d, _ in f0["phenotype"]}
    d_inh0 = defaultdict(set)
    for d, hp in f0["inheritance"]:
        d_inh0[d].add(hp)
    changed = defaultdict(list)
    for c in changes:
        changed[c["disease"]].append(c)

    # A: enrichment — diseases known at T0 (gene + phenotypes) gaining >= 2 PMID-cited phenotypes
    by_step = defaultdict(list)
    for d, cs in changed.items():
        ph = [c for c in cs if c["relation"] == "phenotype" and c["pmids"]]
        if d in d_gene0 and d in d_phen0 and len(ph) >= 2:
            by_step[min(c["step"] for c in ph)].append(d)
    enrichment = []
    steps = sorted(by_step)
    per_step = max(1, n_pilot // len(steps))
    for s in steps:
        pool = sorted(by_step[s])
        enrichment += rng.sample(pool, min(per_step, len(pool)))
    rest = sorted({d for s in steps for d in by_step[s]} - set(enrichment))
    enrichment += rng.sample(rest, max(0, n_pilot - len(enrichment)))

    # Controls — known at T0 and unchanged in every release
    unchanged = sorted((d_gene0 & d_phen0) - set(changed))
    control = rng.sample(unchanged, n_control)

    # B: schema-certified gaps (closed-world check of the TBox existentials)
    mendelian0 = {d for d, modes in d_inh0.items() if any(is_mendelian_mode(terms0, m) for m in modes)}
    gene_gaps = sorted((mendelian0 & d_phen0) - d_gene0)
    filled_gene = sorted({c["disease"] for c in changes if c["relation"] == "gene" and c["disease"] in set(gene_gaps)})
    inh_gaps = sorted((d_phen0 & d_gene0) - set(d_inh0))
    filled_inh = sorted({c["disease"] for c in changes if c["relation"] == "inheritance" and c["disease"] in set(inh_gaps)})
    unfilled = rng.sample(sorted(set(gene_gaps) - set(filled_gene)), n_unfilled)
    return {"enrichment": sorted(enrichment), "control": sorted(control),
            "gap_gene_filled": filled_gene, "gap_gene_unfilled": sorted(unfilled), "gap_inheritance_filled": filled_inh,
            "counts": {"certified_gene_gaps_T0": len(gene_gaps), "certified_inheritance_gaps_T0": len(inh_gaps)}}


def build_owl(f0: dict, diseases: list[str]) -> Graph:
    terms0 = read_obo(TAGS[0])
    organs = organ_systems(terms0)
    g = add_tbox(Graph())
    for oid, oname in organs.items():
        iri = NS["organ_" + oid.replace(":", "_")]
        g.add((iri, RDF.type, NS.OrganSystem))
        g.add((iri, RDFS.label, Literal(oname)))
    dset = set(diseases)
    phen_seen, inh_seen = set(), set()
    for d in diseases:
        iri = NS[d.replace(":", "_")]
        g.add((iri, RDF.type, NS.Disease))
        g.add((iri, RDFS.label, Literal(f0["names"].get(d, d))))
        g.add((iri, NS.omimId, Literal(d)))
    for (d, sym) in f0["gene"]:
        if d in dset:
            giri = NS["gene_" + sym]
            g.add((giri, RDF.type, NS.Gene))
            g.add((giri, RDFS.label, Literal(sym)))
            g.add((giri, NS.geneSymbol, Literal(sym)))
            g.add((NS[d.replace(":", "_")], NS.hasCausativeGene, giri))
    for (d, hp) in f0["inheritance"]:
        if d in dset:
            iri = NS[hp.replace(":", "_")]
            if hp not in inh_seen:
                inh_seen.add(hp)
                g.add((iri, RDF.type, NS.InheritancePattern))
                g.add((iri, RDFS.label, Literal(terms0[hp].name if hp in terms0 else hp)))
            g.add((NS[d.replace(":", "_")], NS.hasInheritancePattern, iri))
            if is_mendelian_mode(terms0, hp):
                g.add((NS[d.replace(":", "_")], RDF.type, NS.MendelianDisease))
    for (d, hp) in f0["phenotype"]:
        if d in dset:
            iri = NS[hp.replace(":", "_")]
            if hp not in phen_seen:
                phen_seen.add(hp)
                g.add((iri, RDF.type, NS.Phenotype))
                g.add((iri, RDFS.label, Literal(terms0[hp].name if hp in terms0 else hp)))
                g.add((iri, NS.hpoId, Literal(hp)))
                for anc in ancestors(terms0, hp) | {hp}:
                    if anc in organs:
                        g.add((iri, NS.affectsOrganSystem, NS["organ_" + anc.replace(":", "_")]))
            g.add((NS[d.replace(":", "_")], NS.hasPhenotype, iri))
    from rdflib import OWL
    for cls in ["Disease", "Gene", "Phenotype", "OrganSystem", "InheritancePattern"]:
        for ind in list(g.subjects(RDF.type, NS[cls])):
            g.add((ind, RDF.type, OWL.NamedIndividual))
    return g


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=100)
    ap.add_argument("--controls", type=int, default=30)
    ap.add_argument("--gap-unfilled", type=int, default=50)
    args = ap.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)

    all_facts = [release_facts(t) for t in TAGS]
    changes = stable_changes(all_facts)
    with open(BUILD / "curator_changes.jsonl", "w", encoding="utf-8") as fh:
        for c in changes:
            fh.write(json.dumps(c) + "\n")

    sl = select_slice(all_facts[0], changes, args.pilot, args.controls, args.gap_unfilled)
    sl["tags"] = TAGS
    (BUILD / "slice.json").write_text(json.dumps(sl, indent=1), encoding="utf-8")

    diseases = sorted(set(sl["enrichment"] + sl["control"] + sl["gap_gene_filled"] + sl["gap_gene_unfilled"]
                          + sl["gap_inheritance_filled"]))
    g = build_owl(all_facts[0], diseases)
    g.serialize(BUILD / "ontology_T0.owl", format="xml")

    from collections import Counter
    print("stable changes:", Counter((c["relation"], c["step"]) for c in changes))
    print({k: (len(v) if isinstance(v, list) else v) for k, v in sl.items()})
    print("slice diseases:", len(diseases), "| triples:", len(g))


if __name__ == "__main__":
    main()
