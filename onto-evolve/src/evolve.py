"""One OntoEvolve update run: acquire -> extract -> gate -> commit, using only documents available
before a cut-off date (leakage-free).

Triggers:
  enrichment  every slice disease with a known gene: mine the literature for phenotypes/inheritance
  gaps        schema-certified gaps (gaps.py): targeted search for the missing gene / inheritance
Raw LLM outputs are cached per (model, disease, document), so ablations re-run the gate only.

Usage:
  uv run python src/evolve.py --run t0 --cutoff 2023-06-06 --docs 15
  uv run python src/evolve.py --run t0-nogate --no-reasoner --reuse t0     # ablation, no LLM calls
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import date

from rdflib import RDF, RDFS, Graph, Literal

import extract as X
from gate import Assertion, Gate, aggregate, save
from gaps import find_gaps
from ground import HPOGrounder
from hpo import ROOT, TAGS, pmids, read_g2d, read_hpoa, read_obo
from sources.pubmed import PubMed
from tbox import NS

BUILD = ROOT / "data" / "build"
RUNS = ROOT / "results" / "runs"
XCACHE = ROOT / "data" / "cache" / "extract"


def short_name(name: str) -> str:
    n = name.split(";")[0]
    n = re.sub(r",?\s*(type\s+)?[0-9IVX]+[A-Z]?$", "", n.strip(), flags=re.I)   # drop trailing subtype numbers
    return n.strip()


def query_for(name: str, genes: list[str], gap: str | None) -> str:
    sn = short_name(name)
    if gap == "hasCausativeGene" or not genes:
        return f'"{sn}"[tiab] AND (gene[tiab] OR mutation*[tiab] OR variant*[tiab])'
    g = " OR ".join(f"{s}[tiab]" for s in genes[:3])
    return f'({g}) AND ("{sn}"[tiab] OR patient*[tiab] OR case[tiab] OR famil*[tiab])'


def curated_for(diseases: list[str]) -> dict[str, list[Assertion]]:
    import pandas as pd
    raw = pd.read_csv(ROOT / "data" / "raw" / TAGS[0] / "phenotype.hpoa", sep="\t", comment="#", dtype=str)
    raw = raw[raw.database_id.isin(diseases) & raw.aspect.isin(["P", "I"])]
    out = {d: [] for d in diseases}
    for d, hp, q, ref, asp in zip(raw.database_id, raw.hpo_id, raw.qualifier, raw.reference, raw.aspect):
        out[d].append(Assertion(d, "phenotype" if asp == "P" else "inheritance", hp, q != "NOT", "curated",
                                [f"PMID:{p}" for p in pmids(ref)] or [str(ref)], [], "1900-01-01", "curated"))
    g = read_g2d(TAGS[0])
    g = g[g.disease_id.isin(diseases)]
    for d, sym in zip(g.disease_id, g.gene_symbol):
        out[d].append(Assertion(d, "gene", sym, True, "curated", ["mim2gene"], [], "1900-01-01", "curated"))
    return out


def extract_cached(model: str, disease: str, name: str, genes: list[str], doc, grounder) -> tuple[list, dict]:
    XCACHE.mkdir(parents=True, exist_ok=True)
    f = XCACHE / f"{model.replace(':', '_')}__{disease.replace(':', '_')}__{doc.id.replace(':', '_')}.json"
    raw = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    cands, st = X.extract(disease, name, genes, doc, grounder, model=model, raw=raw)
    if raw is None:
        f.write_text(json.dumps(st["raw"]), encoding="utf-8")
    return cands, st


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--cutoff", default=TAGS[0][1:])
    ap.add_argument("--docs", type=int, default=15)
    ap.add_argument("--model", default=X.EXTRACTOR)
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--no-reasoner", action="store_true")
    ap.add_argument("--no-redundancy", action="store_true")
    ap.add_argument("--no-evidence-check", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="only the first N diseases (smoke test)")
    args = ap.parse_args()
    cutoff = date.fromisoformat(args.cutoff)
    out_dir = RUNS / args.run
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.no_evidence_check:
        X.evidence_in = lambda e, t, threshold=85: True

    sl = json.loads((BUILD / "slice.json").read_text())
    g = Graph()
    g.parse(BUILD / "ontology_T0.owl", format="xml")
    gaps = {gp.individual.replace("_", ":", 1): gp.prop for gp in find_gaps(g)}
    names = dict(zip(read_hpoa(TAGS[0]).database_id, read_hpoa(TAGS[0]).disease_name))
    g0 = read_g2d(TAGS[0])
    genes = g0.groupby("disease_id").gene_symbol.apply(lambda s: sorted(set(s))).to_dict()
    known_genes = set(g0.gene_symbol) | set(read_g2d(TAGS[-1]).gene_symbol)   # HGNC-style vocabulary
    diseases = sorted(set(sl["enrichment"] + sl["control"] + sl["gap_gene_filled"] + sl["gap_gene_unfilled"]
                          + sl["gap_inheritance_filled"]))
    if args.limit:
        diseases = diseases[: args.limit]
    grounder = HPOGrounder(TAGS[0])     # vocabulary as of T0
    pm = PubMed()
    curated = curated_for(diseases)

    candidates, log = [], []
    t_start = time.time()
    for i, d in enumerate(diseases, 1):
        q = query_for(names.get(d, d), genes.get(d, []), gaps.get(d))
        ids = pm.search(q, date(1900, 1, 1), cutoff, limit=args.docs)
        docs = [doc for doc in pm.fetch(ids) if doc.text.strip() and doc.available < cutoff]
        n_c = 0
        for doc in docs:
            cands, st = extract_cached(args.model, d, names.get(d, d), genes.get(d, []), doc, grounder)
            candidates += [X.to_dict(c) for c in cands]
            n_c += len(cands)
        log.append({"disease": d, "query": q, "docs": [doc.id for doc in docs], "candidates": n_c,
                    "trigger": "gap:" + gaps[d] if d in gaps else "enrichment"})
        el = time.time() - t_start
        print(f"[{i}/{len(diseases)}] {d} docs={len(docs)} cands={n_c}  {el / 60:.1f} min, ~{el / i * (len(diseases) - i) / 60:.0f} min left", flush=True)

    assertions = aggregate(candidates)
    all_curated = [a for v in curated.values() for a in v]
    gate = Gate(read_obo(TAGS[0]), set(diseases), known_genes, all_curated, k=args.k,
                use_reasoner=not args.no_reasoner, check_redundancy=not args.no_redundancy)
    gate.run(assertions)
    save(assertions + [a for a in all_curated if a.status == "curated_conflict"], args.run, 0)

    # commit accepted assertions into a new OWL version
    for a in assertions:
        if a.status != "accepted" or not a.positive:
            continue
        di = NS[a.disease.replace(":", "_")]
        if a.relation == "phenotype":
            o = NS[a.object.replace(":", "_")]
            g.add((o, RDF.type, NS.Phenotype))
            g.add((o, RDFS.label, Literal(grounder.label(a.object))))
            g.add((di, NS.hasPhenotype, o))
        elif a.relation == "gene":
            o = NS["gene_" + a.object]
            g.add((o, RDF.type, NS.Gene))
            g.add((o, RDFS.label, Literal(a.object)))
            g.add((di, NS.hasCausativeGene, o))
        elif a.relation == "inheritance":
            o = NS[a.object.replace(":", "_")]
            g.add((o, RDF.type, NS.InheritancePattern))
            g.add((di, NS.hasInheritancePattern, o))
    g.serialize(out_dir / "ontology.owl", format="xml")
    with open(out_dir / "assertions.jsonl", "w", encoding="utf-8") as fh:
        for a in assertions:
            fh.write(json.dumps({**a.__dict__, "weight": a.weight()}) + "\n")
    (out_dir / "acquisition_log.json").write_text(json.dumps(log, indent=1))
    from collections import Counter
    summary = {"args": vars(args), "diseases": len(diseases), "candidates": len(candidates),
               "assertions": len(assertions), "status": Counter(a.status for a in assertions),
               "remaining_gaps": len(find_gaps(g))}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
