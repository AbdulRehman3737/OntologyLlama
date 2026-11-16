"""Drift QA: does a self-updating ontology answer questions whose answers changed after T0?

Question: "Has <phenotype> been reported in patients with <disease>?"
  drift     gold yes: curators added it after T0 (static T0 ontology does not have it)
  stable    gold yes: already annotated at T0
  excluded  gold no : curated NOT annotation (explicitly excluded)
Arms (TinyLlama answers in all, same prompt frame as the first study):
  A closed-book
  B vector RAG over the same pre-T0 abstracts the updater read
  C static ontology at T0
  D self-updating ontology (an OntoEvolve run)
  F oracle ontology at the final release (upper bound)
The ontology arms give the model the disease's facts for that phenotype and its HPO relatives,
with provenance (curated / extracted from PMID ...), and say explicitly when nothing is recorded.

Usage: uv run python src/drift_qa.py --run t0 [--n 300]
"""
from __future__ import annotations

import argparse
import json
import random
import time

import ollama

from hpo import ROOT, TAGS, ancestors, read_hpoa, read_obo

ANSWER_MODEL = "tinyllama"
OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 80, "num_ctx": 2048, "repeat_penalty": 1.0}
SYSTEM = ("You are a medical genetics assistant. Answer the question with Yes or No first, then one short sentence. "
          "If you do not know, say \"I don't know\".")
OUT = ROOT / "results" / "drift_qa"


def build_questions(n: int, seed: int = 3) -> list[dict]:
    sl = json.loads((ROOT / "data" / "build" / "slice.json").read_text())
    enr = sl["enrichment"]
    terms = read_obo(TAGS[-1])
    ch = [json.loads(l) for l in open(ROOT / "data" / "build" / "curator_changes.jsonl", encoding="utf-8")]
    h0 = read_hpoa(TAGS[0])
    import pandas as pd
    raw0 = pd.read_csv(ROOT / "data" / "raw" / TAGS[0] / "phenotype.hpoa", sep="\t", comment="#", dtype=str)
    names = dict(zip(h0.database_id, h0.disease_name))
    rng = random.Random(seed)
    drift = [(c["disease"], c["object"]) for c in ch if c["relation"] == "phenotype" and c["disease"] in enr and c["object"] in terms]
    t0p = h0[(h0.aspect == "P") & h0.database_id.isin(enr)]
    stable = list(zip(t0p.database_id, t0p.hpo_id))
    nots = raw0[(raw0.qualifier == "NOT") & (raw0.aspect == "P")]
    excluded = [(d, p) for d, p in zip(nots.database_id, nots.hpo_id) if d in set(sl["enrichment"] + sl["control"])]
    qs = []
    for kind, pool, gold, k in [("drift", drift, True, n // 2), ("stable", stable, True, n // 4), ("excluded", excluded, False, n // 4)]:
        for d, p in rng.sample(pool, min(k, len(pool))):
            qs.append({"kind": kind, "disease": d, "hpo": p, "gold": gold,
                       "question": f"Has {terms[p].name.lower()} been reported in patients with {names.get(d, d)}?"})
    return qs


def ontology_context(facts: dict, terms, d: str, p: str, label: str) -> str:
    """facts[(d)] -> list of (hpo, positive, provenance)."""
    rel = [(h, pos, prov) for h, pos, prov in facts.get(d, []) if h == p or h in ancestors(terms, p) or p in ancestors(terms, h)]
    lines = []
    for h, pos, prov in rel[:8]:
        verb = "has been reported" if pos else "has been explicitly excluded"
        lines.append(f"- {terms[h].name} {verb} in this disease ({prov}).")
    if not lines:
        lines = [f"- The ontology records nothing about {terms[p].name.lower()} or related findings in this disease."]
    return f"Facts from the ontology ({label}):\n" + "\n".join(lines)


def ask(question: str, context: str | None) -> tuple[str, float]:
    prompt = f"Question: {question}\nAnswer:" if context is None else (
        f"{context}\n\nUsing the information above, answer the question. If the information does not contain the answer, "
        f"say \"I don't know\".\nQuestion: {question}\nAnswer:")
    t0 = time.perf_counter()
    r = ollama.chat(model=ANSWER_MODEL, messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                    options=OPTIONS)
    return r["message"]["content"].strip(), time.perf_counter() - t0


def parse(ans: str) -> bool | None:
    import re
    t = ans.lower()
    if re.search(r"i don.?t know|not (contain|mention)|no information|unknown", t):
        return None
    m = re.search(r"\b(yes|no)\b", t)
    return None if not m else m.group(1) == "yes"


def facts_from_hpoa(tag: str, diseases: set[str]) -> dict:
    import pandas as pd
    raw = pd.read_csv(ROOT / "data" / "raw" / tag / "phenotype.hpoa", sep="\t", comment="#", dtype=str)
    raw = raw[(raw.aspect == "P") & raw.database_id.isin(diseases)]
    out = {}
    for d, p, q in zip(raw.database_id, raw.hpo_id, raw.qualifier):
        out.setdefault(d, []).append((p, q != "NOT", f"curated, HPO {tag}"))
    return out


def facts_from_run(run: str, base: dict) -> dict:
    out = {d: list(v) for d, v in base.items()}
    for l in open(ROOT / "results" / "runs" / run / "assertions.jsonl", encoding="utf-8"):
        a = json.loads(l)
        if a["status"] == "accepted" and a["relation"] == "phenotype":
            src = ", ".join(a["docs"][:2])
            out.setdefault(a["disease"], []).append((a["object"], a["positive"], f"extracted from {src}"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="t0")
    ap.add_argument("--n", type=int, default=300)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    terms = read_obo(TAGS[-1])
    qs = build_questions(args.n)
    ds = {q["disease"] for q in qs}
    static = facts_from_hpoa(TAGS[0], ds)
    oracle = facts_from_hpoa(TAGS[-1], ds)
    evolved = facts_from_run(args.run, static)

    from rag import abstracts_rag
    rag = abstracts_rag(args.run)

    arms = {
        "A_closed_book": lambda q: None,
        "B_vector_rag": lambda q: rag(q["disease"], q["question"]),
        "C_static_T0": lambda q: ontology_context(static, terms, q["disease"], q["hpo"], "HPO release 2023-06-06"),
        "D_self_updating": lambda q: ontology_context(evolved, terms, q["disease"], q["hpo"], "HPO 2023-06-06 + OntoEvolve updates"),
        "F_oracle_final": lambda q: ontology_context(oracle, terms, q["disease"], q["hpo"], "HPO release 2026-09-01"),
    }
    out = OUT / f"{args.run}.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for i, q in enumerate(qs, 1):
            for arm, ctx_fn in arms.items():
                ctx = ctx_fn(q)
                ans, secs = ask(q["question"], ctx)
                said = parse(ans)
                fh.write(json.dumps({**q, "arm": arm, "context": ctx, "answer": ans, "said": said,
                                     "correct": said is q["gold"], "secs": secs}) + "\n")
            if i % 25 == 0:
                print(f"[{i}/{len(qs)}]", flush=True)
    import pandas as pd
    df = pd.read_json(out, lines=True)
    print(df.pivot_table(index="kind", columns="arm", values="correct", aggfunc="mean").round(3).to_string())
    print(df.groupby("arm").correct.mean().round(3).to_string())


if __name__ == "__main__":
    main()
