"""List every answer whose grade changes when typo tolerance is on (for manual checking)."""
import json
from collections import Counter

import grade as G
from kg import ROOT
from questions import load

Q = {q["id"]: q for q in load()}
R = [json.loads(line) for line in open(ROOT / "results" / "responses.jsonl", encoding="utf-8")]
flips = []
for r in R:
    q = Q[r["id"]]
    G.TYPO_TOLERANT = False
    a = G.grade(q, r["answer"])["score"]
    G.TYPO_TOLERANT = True
    b = G.grade(q, r["answer"])["score"]
    if a != b:
        flips.append((r["arm"], q["question"], q["gold_labels"], r["answer"], a, b))
print(Counter(f[0] for f in flips))
for arm, qq, g, a, s0, s1 in flips:
    print(f"[{arm[:2]}] {s0:.2f}->{s1:.2f} {qq} | GOLD {g}\n    {a[:230]!r}")
