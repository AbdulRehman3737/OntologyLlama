"""Extractor bake-off on abstracts that curators actually cited.

Gold for (disease, PMID) = phenotype annotations in the final HPO release for that disease that
cite that PMID. Metrics per model:
  precision_exact     extracted HPO id is in gold
  precision_related   extracted id is gold or an ancestor/descendant of a gold term
  recall_exact / recall_related
  secs per abstract
  memorisation: with the abstract withheld, how many raw items still match gold (should be ~0)

Usage: uv run python src/bakeoff.py --models qwen3:8b [qwen2.5:7b] --n 50
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict

from extract import call_llm, extract
from ground import HPOGrounder
from hpo import ROOT, TAGS, pmids, read_g2d, read_hpoa
from sources.pubmed import PubMed

OUT = ROOT / "results" / "bakeoff.jsonl"


def build_items(n: int) -> list[dict]:
    sl = json.loads((ROOT / "data" / "build" / "slice.json").read_text())
    hF = read_hpoa(TAGS[-1])
    hF = hF[(hF.aspect == "P") & hF.database_id.isin(sl["enrichment"])]
    gold = defaultdict(set)
    names = {}
    for d, hp, ref, name in zip(hF.database_id, hF.hpo_id, hF.reference, hF.disease_name):
        names[d] = name
        for p in pmids(ref):
            gold[(d, p)].add(hp)
    g0 = read_g2d(TAGS[0])
    genes = g0.groupby("disease_id").gene_symbol.apply(lambda s: sorted(set(s))).to_dict()
    keys = sorted(k for k, v in gold.items() if len(v) >= 3)
    rng = random.Random(7)
    rng.shuffle(keys)
    docs = {d.id: d for d in PubMed().fetch([f"PMID:{p}" for _, p in keys[: n * 2]])}
    items = []
    for d, p in keys:
        doc = docs.get(f"PMID:{p}")
        if doc and len(doc.text) > 200:
            items.append({"disease": d, "name": names[d], "genes": genes.get(d, []), "doc": doc, "gold": gold[(d, p)]})
        if len(items) == n:
            break
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen3:8b"])
    ap.add_argument("--n", type=int, default=50)
    args = ap.parse_args()
    grounder = HPOGrounder(TAGS[-1])
    items = build_items(args.n)
    print(f"{len(items)} abstracts, mean gold {sum(len(i['gold']) for i in items) / len(items):.1f} terms")
    summary = {}
    with open(OUT, "w", encoding="utf-8") as fh:
        for model in args.models:
            tp_e = tp_r = n_ext = rec_e = rec_r = n_gold = mem_hits = mem_items = 0
            secs = 0.0
            for it in items:
                cands, st = extract(it["disease"], it["name"], it["genes"], it["doc"], grounder, model=model)
                ext = {c.object for c in cands if c.relation == "phenotype" and c.positive}
                gold = it["gold"]
                n_ext += len(ext)
                tp_e += len(ext & gold)
                tp_r += sum(1 for e in ext if any(grounder.related(e, g) for g in gold))
                rec_e += len(gold & ext)
                rec_r += sum(1 for g in gold if any(grounder.related(e, g) for e in ext))
                n_gold += len(gold)
                secs += st["secs"]
                raw_nt, _ = call_llm(it["name"], it["genes"], it["doc"], model=model, with_text=False)
                mem_items += len(raw_nt.get("phenotypes", []))
                mem = {grounder.ground(p.get("phrase", ""))[0] for p in raw_nt.get("phenotypes", [])}
                mem_hits += len((mem - {None}) & gold)
                fh.write(json.dumps({"model": model, "disease": it["disease"], "pmid": it["doc"].id,
                                     "gold": sorted(gold), "extracted": sorted(ext), "stats": {k: v for k, v in st.items() if k != "raw"},
                                     "no_abstract_items": len(raw_nt.get("phenotypes", []))}) + "\n")
            summary[model] = {
                "precision_exact": tp_e / max(n_ext, 1), "precision_related": tp_r / max(n_ext, 1),
                "recall_exact": rec_e / n_gold, "recall_related": rec_r / n_gold,
                "secs_per_abstract": secs / len(items), "extracted_per_abstract": n_ext / len(items),
                "no_abstract_items_per_abstract": mem_items / len(items), "no_abstract_gold_hits": mem_hits,
            }
            print(model, json.dumps({k: round(v, 3) for k, v in summary[model].items()}))
    (ROOT / "results" / "bakeoff_summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
