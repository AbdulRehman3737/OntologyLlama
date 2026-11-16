"""Back-test OntoEvolve runs against real HPO curator releases.

Gold = stable curator additions after T0 (steps 1..6, still present in the final release).
For every run (results/runs/<name>/assertions.jsonl):

Enrichment (phenotypes on enrichment + control diseases)
  added             accepted, positive, new phenotype assertions
  confirmed         added AND later added by curators (exact HPO id)
  confirmed_related added AND equal/ancestor/descendant of a later curator addition
  precision_lb      confirmed / added   (lower bound: not-yet-curated is not the same as wrong)
  recall            share of curator additions the run recovered (exact)
  lead_time         for confirmed: months between T0 and the release where curators added it
  control_adds      additions on control diseases (curators changed nothing there in 3 years)
Gaps
  gene gaps the run filled, and how many match the gene curators later added

Usage: uv run python src/backtest.py t0 t0-nogate ...
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from datetime import date

from hpo import ROOT, TAGS, ancestors, read_obo

BUILD = ROOT / "data" / "build"
RUNS = ROOT / "results" / "runs"
T0 = date.fromisoformat(TAGS[0][1:])


def load_gold():
    sl = json.loads((BUILD / "slice.json").read_text())
    ch = [json.loads(l) for l in open(BUILD / "curator_changes.jsonl", encoding="utf-8")]
    gold = defaultdict(dict)   # (relation, disease) -> {object: tag}
    for c in ch:
        gold[(c["relation"], c["disease"])][c["object"]] = c["tag"]
    return sl, gold


def related(terms, a: str, b: str) -> bool:
    return a == b or a in ancestors(terms, b) or b in ancestors(terms, a)


def score(run: str, sl: dict, gold: dict, terms) -> dict:
    rows = [json.loads(l) for l in open(RUNS / run / "assertions.jsonl", encoding="utf-8")]
    acc = [r for r in rows if r["status"] == "accepted" and r["positive"]]
    enr, ctl = set(sl["enrichment"]), set(sl["control"])

    # --- enrichment
    added = [r for r in acc if r["relation"] == "phenotype" and r["disease"] in enr]
    conf, conf_rel, leads = 0, 0, []
    for r in added:
        g = gold.get(("phenotype", r["disease"]), {})
        if r["object"] in g:
            conf += 1
            leads.append((date.fromisoformat(g[r["object"]][1:]) - T0).days / 30.44)
        if any(related(terms, r["object"], o) for o in g):
            conf_rel += 1
    total_gold = sum(len(gold.get(("phenotype", d), {})) for d in enr)
    found_gold = sum(1 for d in enr for o in gold.get(("phenotype", d), {})
                     if any(r["object"] == o and r["disease"] == d for r in added))
    control_adds = [r for r in acc if r["relation"] == "phenotype" and r["disease"] in ctl]

    # --- gene gaps
    gfilled = {r["disease"]: r["object"] for r in acc if r["relation"] == "gene"}
    gap_f, gap_u = set(sl["gap_gene_filled"]), set(sl["gap_gene_unfilled"])
    gene_hits = sum(1 for d in gap_f if d in gfilled and gfilled[d] in gold.get(("gene", d), {}))
    gene_wrong = sum(1 for d in gap_f if d in gfilled and gfilled[d] not in gold.get(("gene", d), {}))

    statuses = defaultdict(int)
    for r in rows:
        statuses[r["status"]] += 1
    return {
        "run": run,
        "added": len(added),
        "confirmed": conf,
        "confirmed_related": conf_rel,
        "precision_lb": conf / len(added) if added else 0.0,
        "precision_related_lb": conf_rel / len(added) if added else 0.0,
        "recall": found_gold / total_gold if total_gold else 0.0,
        "gold_additions": total_gold,
        "lead_time_months_median": statistics.median(leads) if leads else None,
        "lead_times": leads,
        "control_adds": len(control_adds),
        "control_adds_per_disease": len(control_adds) / max(len(ctl), 1),
        "gene_gaps_filled_on_curated_set": sum(1 for d in gap_f if d in gfilled),
        "gene_gaps_correct": gene_hits,
        "gene_gaps_wrong": gene_wrong,
        "gene_gaps_filled_on_uncurated_set": sum(1 for d in gap_u if d in gfilled),
        "statuses": dict(statuses),
    }


def main(runs: list[str]) -> None:
    sl, gold = load_gold()
    terms = read_obo(TAGS[-1])
    res = [score(r, sl, gold, terms) for r in runs]
    out = ROOT / "results" / "backtest.json"
    out.write_text(json.dumps(res, indent=1))
    cols = ["run", "added", "confirmed", "precision_lb", "precision_related_lb", "recall", "lead_time_months_median",
            "control_adds_per_disease", "gene_gaps_filled_on_curated_set", "gene_gaps_correct", "gene_gaps_filled_on_uncurated_set"]
    print(" | ".join(cols))
    for r in res:
        print(" | ".join(f"{r[c]:.3f}" if isinstance(r[c], float) else str(r[c]) for c in cols))


if __name__ == "__main__":
    main(sys.argv[1:] or ["t0"])
