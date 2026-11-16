"""Run every arm over every question; results are appended to a JSONL file so runs can resume.

Usage:
  uv run python src/run.py                      # full run -> results/responses.jsonl
  uv run python src/run.py --limit 10 --out results/smoke.jsonl
  uv run python src/run.py --ids q001 q120 --arms C_ontology
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time

from arms import ARMS, DISPATCH
from grade import grade
from kg import ROOT
from questions import load


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="*", default=ARMS)
    ap.add_argument("--limit", type=int, default=None, help="random stratified sample of N questions")
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--out", default=str(ROOT / "results" / "responses.jsonl"))
    args = ap.parse_args()

    qs = load()
    if args.ids:
        qs = [q for q in qs if q["id"] in set(args.ids)]
    if args.limit:
        rng = random.Random(7)
        by_cat: dict[str, list] = {}
        for q in qs:
            by_cat.setdefault(q["category"], []).append(q)
        picked = [rng.choice(v) for v in by_cat.values()]
        rest = [q for q in qs if q not in picked]
        qs = picked + rng.sample(rest, max(0, args.limit - len(picked)))

    done = set()
    try:
        with open(args.out, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                done.add((r["id"], r["arm"]))
    except FileNotFoundError:
        pass

    todo = [(q, a) for q in qs for a in args.arms if (q["id"], a) not in done]
    print(f"{len(todo)} calls to make ({len(done)} already done)", flush=True)
    t0 = time.time()
    with open(args.out, "a", encoding="utf-8") as fh:
        for i, (q, arm) in enumerate(todo, 1):
            res = DISPATCH[arm](q["question"])
            g = grade(q, res["answer"])
            rec = {"id": q["id"], "arm": arm, "category": q["category"], "subtype": q["subtype"],
                   "paraphrase": q["paraphrase"], "question": q["question"], "mode": q["mode"],
                   "gold": q["gold_labels"] if q["mode"] != "yesno" else q["gold_bool"], **res, "grade": g}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 20 == 0 or i == len(todo):
                el = time.time() - t0
                print(f"[{i}/{len(todo)}] {el/60:.1f} min elapsed, ~{el/i*(len(todo)-i)/60:.1f} min left", flush=True)


if __name__ == "__main__":
    sys.exit(main())
