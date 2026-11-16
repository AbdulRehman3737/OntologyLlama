"""Build results/report.md + PNG charts from results/responses.jsonl."""
from __future__ import annotations

import json
import random
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import binomtest  # noqa: E402

from kg import ROOT  # noqa: E402

RES = ROOT / "results"
ARMS = ["A_closed_book", "B_vector_rag", "C_ontology", "D_ontology_verified", "C0_ontology_facts_only"]
ARM_LABEL = {"A_closed_book": "A  Closed-book", "B_vector_rag": "B  Vector RAG", "C_ontology": "C  Ontology layer",
             "D_ontology_verified": "D  Ontology + verify", "C0_ontology_facts_only": "C0 Ontology, facts only (ablation)"}
SHORT = {"A_closed_book": "A", "B_vector_rag": "B", "C_ontology": "C", "D_ontology_verified": "D", "C0_ontology_facts_only": "C0"}
COLORS = {"A_closed_book": "#2a78d6", "B_vector_rag": "#eb6834", "C_ontology": "#1baf7a",
          "D_ontology_verified": "#eda100", "C0_ontology_facts_only": "#e87ba4"}
CATS = ["single_hop", "inverse", "multi_hop", "list", "yes_no", "inferred", "unanswerable"]
CAT_LABEL = {"single_hop": "Single-hop", "inverse": "Inverse", "multi_hop": "Multi-hop", "list": "List",
             "yes_no": "Yes/no", "inferred": "Reasoner-inferred", "unanswerable": "Unanswerable"}
INK, MUTED, GRID, SURFACE = "#1f1f1e", "#6b6a64", "#e6e5e0", "#fcfcfb"


def load(path) -> pd.DataFrame:
    from grade import grade
    from questions import load as load_q
    qmap = {q["id"]: q for q in load_q()}
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    for r in rows:  # re-grade with the current grader so grader fixes need no re-run
        r["grade"] = grade(qmap[r["id"]], r["answer"])
    df = pd.DataFrame(rows)
    for k in ["correct", "strict", "score", "abstained", "hallucinated"]:
        df[k] = df["grade"].map(lambda g: g[k])
    df["correct"] = df["correct"].astype(int)
    return df


def boot_ci(x: np.ndarray, n: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(n, len(x)), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def mcnemar(df: pd.DataFrame, a: str, b: str) -> tuple[int, int, float]:
    pa = df[df.arm == a].set_index("id")["correct"]
    pb = df[df.arm == b].set_index("id")["correct"]
    j = pd.concat([pa, pb], axis=1, join="inner")
    j.columns = ["a", "b"]
    a_only = int(((j.a == 1) & (j.b == 0)).sum())
    b_only = int(((j.a == 0) & (j.b == 1)).sum())
    p = binomtest(a_only, a_only + b_only, 0.5).pvalue if a_only + b_only else 1.0
    return a_only, b_only, p


def style(ax):
    ax.set_facecolor(SURFACE)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def chart_overall(summary: pd.DataFrame, path):
    fig, ax = plt.subplots(figsize=(8, 3.4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    arms = list(summary.index)[::-1]
    y = np.arange(len(arms))
    acc = summary.loc[arms, "accuracy"].values * 100
    lo = summary.loc[arms, "ci_lo"].values * 100
    hi = summary.loc[arms, "ci_hi"].values * 100
    ax.barh(y, acc, height=0.55, color=[COLORS[a] for a in arms], edgecolor=SURFACE, linewidth=2)
    ax.errorbar(acc, y, xerr=[acc - lo, hi - acc], fmt="none", ecolor=INK, elinewidth=1, capsize=3)
    for yi, v, h in zip(y, acc, hi):
        ax.text(h + 1.5, yi, f"{v:.1f}%", va="center", color=INK, fontsize=9)
    ax.set_yticks(y, [ARM_LABEL[a] for a in arms], color=INK, fontsize=9)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Questions answered correctly (%), 95% bootstrap CI", color=MUTED, fontsize=9)
    style(ax)
    ax.set_title("Overall accuracy, TinyLlama 1.1B", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def chart_by_category(bycat: pd.DataFrame, path):
    arms = [a for a in ARMS if a in bycat.columns]
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    x = np.arange(len(CATS))
    w = 0.8 / len(arms)
    for i, a in enumerate(arms):
        vals = bycat.loc[CATS, a].values * 100
        ax.bar(x - 0.4 + w * (i + 0.5), vals, width=w, color=COLORS[a], edgecolor=SURFACE, linewidth=1.5, label=ARM_LABEL[a])
    ax.set_xticks(x, [CAT_LABEL[c] for c in CATS], color=INK, fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Mean score (%)  [list = F1]", color=MUTED, fontsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.grid(axis="x", visible=False)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)
    ax.set_axisbelow(True)
    ax.set_facecolor(SURFACE)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.1), labelcolor=INK)
    ax.set_title("Score by question category", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def chart_outcomes(out: pd.DataFrame, path, n: int):
    fig, ax = plt.subplots(figsize=(8, 3.4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    arms = list(out.index)[::-1]
    y = np.arange(len(arms))
    left = np.zeros(len(arms))
    parts = [("correct", "Correct", "#2a78d6"), ("abstained", "Said \"I don't know\"", "#b4b3ab"),
             ("hallucinated", "Wrong answer given (hallucination)", "#e34948")]
    for key, lab, col in parts:
        vals = out.loc[arms, key].values * 100
        ax.barh(y, vals, left=left, height=0.55, color=col, edgecolor=SURFACE, linewidth=2, label=lab)
        for yi, l, v in zip(y, left, vals):
            if v >= 7:
                ax.text(l + v / 2, yi, f"{v:.0f}%", va="center", ha="center", color="white" if key != "abstained" else INK, fontsize=8)
        left += vals
    ax.set_yticks(y, [ARM_LABEL[a] for a in arms], color=INK, fontsize=9)
    ax.set_xlim(0, 100)
    style(ax)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.08), labelcolor=INK)
    ax.set_title(f"What happens on answerable questions (n={n})", loc="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def pct(x) -> str:
    return f"{100 * x:.1f}%"


def main(path=RES / "responses.jsonl"):
    df = load(path)
    arms = [a for a in ARMS if a in set(df.arm)]
    n_q = df.id.nunique()

    summary = pd.DataFrame(index=arms)
    for a in arms:
        d = df[df.arm == a]
        lo, hi = boot_ci(d.correct.values)
        summary.loc[a, "accuracy"] = d.correct.mean()
        summary.loc[a, "ci_lo"], summary.loc[a, "ci_hi"] = lo, hi
        summary.loc[a, "strict"] = d.strict.mean()
        summary.loc[a, "mean_score"] = d.score.mean()
        ans = d[d.category != "unanswerable"]
        summary.loc[a, "halluc_answerable"] = ans.hallucinated.mean()
        summary.loc[a, "abstain_answerable"] = ans.abstained.mean()
        summary.loc[a, "abstain_unanswerable"] = d[d.category == "unanswerable"].correct.mean()
        summary.loc[a, "paraphrase_acc"] = d[d.paraphrase].correct.mean()
        summary.loc[a, "latency_s"] = d.latency_s.mean()
        summary.loc[a, "prompt_tokens"] = d.prompt_tokens.mean()

    bycat = df.pivot_table(index="category", columns="arm", values="score", aggfunc="mean")
    bycat_n = df[df.arm == arms[0]].groupby("category").size()
    out = pd.DataFrame(index=arms)
    ans = df[df.category != "unanswerable"]
    for a in arms:
        d = ans[ans.arm == a]
        out.loc[a, "correct"] = d.correct.mean()
        out.loc[a, "abstained"] = d.abstained.mean()
        out.loc[a, "hallucinated"] = d.hallucinated.mean()

    chart_overall(summary, RES / "chart_overall.png")
    chart_by_category(bycat, RES / "chart_by_category.png")
    chart_outcomes(out, RES / "chart_outcomes.png", ans.id.nunique())

    tests = []
    for a, b in [("C_ontology", "B_vector_rag"), ("D_ontology_verified", "B_vector_rag"),
                 ("C0_ontology_facts_only", "B_vector_rag"), ("B_vector_rag", "A_closed_book"),
                 ("C_ontology", "A_closed_book"), ("D_ontology_verified", "C_ontology")]:
        if a in arms and b in arms:
            ao, bo, p = mcnemar(df, a, b)
            tests.append((a, b, ao, bo, p))

    d_arm = df[df.arm == "D_ontology_verified"]
    actions = d_arm.verify_action.value_counts().to_dict() if "verify_action" in d_arm else {}

    # retrieval diagnostics (no LLM involved)
    from textmatch import get_matcher
    from questions import load as load_q
    m = get_matcher()
    qmap = {q["id"]: q for q in load_q()}
    rag_hit, onto_hit, n_entity_q = 0, 0, 0
    for _, r in df[df.arm == "C_ontology"].iterrows():
        q = qmap[r.id]
        p = r.plan
        if q["mode"] == "yesno":
            onto_hit += p["truth"] is q["gold_bool"]
        elif q["mode"] == "abstain":
            onto_hit += p["kind"] in ("none", "empty")
        elif q["mode"] == "list":
            onto_hit += set(p["results"]) == set(q["gold"])
        else:
            onto_hit += bool(set(p["results"]) & set(q["gold"])) and set(p["results"]) <= set(q["gold"])
    for _, r in df[df.arm == "B_vector_rag"].iterrows():
        q = qmap[r.id]
        if q["mode"] in ("single", "any", "list"):
            n_entity_q += 1
            ents = set(m.entities(r.context or "", q["answer_type"]))
            rag_hit += (set(q["gold"]) <= ents) if q["mode"] == "list" else bool(ents & set(q["gold"]))
    rag_by_cat = {}
    for c in CATS:
        rows = df[(df.arm == "B_vector_rag") & (df.category == c)]
        hits, n = 0, 0
        for _, r in rows.iterrows():
            q = qmap[r.id]
            if q["mode"] not in ("single", "any", "list"):
                continue
            n += 1
            ents = set(m.entities(r.context or "", q["answer_type"]))
            hits += (set(q["gold"]) <= ents) if q["mode"] == "list" else bool(ents & set(q["gold"]))
        rag_by_cat[c] = (hits, n)

    # audit sample for manual checking
    rng = random.Random(11)
    sample_ids = rng.sample(range(len(df)), 60)
    aud = df.iloc[sample_ids][["id", "arm", "category", "question", "gold", "answer", "correct", "abstained"]]
    aud.to_csv(RES / "audit_sample.csv", index=False, encoding="utf-8")

    # ------------------------------------------------------------ markdown
    L = []
    L.append("# Ontology layer vs vector RAG vs closed-book: TinyLlama 1.1B on rare genetic diseases\n")
    L.append(f"Questions: **{n_q}** · Arms: **{len(arms)}** · Model: `tinyllama` (1.1B, Ollama, temperature 0, seed 42, "
             "repeat_penalty 1.0) · Knowledge source for every retrieval arm: the same OWL file (50 diseases, "
             "1,632 asserted triples + inverses + HermiT-inferred class membership).\n")
    L.append("## Headline\n")
    L.append("| Arm | Accuracy (95% CI) | Strict | Mean score | Hallucination (answerable) | Abstains when answer is unknowable | Paraphrase subset | Avg prompt tokens | Avg LLM latency |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for a in arms:
        s = summary.loc[a]
        L.append(f"| {ARM_LABEL[a]} | {pct(s.accuracy)} ({pct(s.ci_lo)}–{pct(s.ci_hi)}) | {pct(s.strict)} | {pct(s.mean_score)} | "
                 f"{pct(s.halluc_answerable)} | {pct(s.abstain_unanswerable)} | {pct(s.paraphrase_acc)} | {s.prompt_tokens:.0f} | {s.latency_s:.2f}s |")
    L.append("\n![Overall accuracy](chart_overall.png)\n")
    L.append("![Outcomes on answerable questions](chart_outcomes.png)\n")
    L.append("## By question category (mean score; list questions use F1)\n")
    L.append("| Category | n | " + " | ".join(SHORT[a] for a in arms) + " |")
    L.append("|---|---|" + "---|" * len(arms))
    for c in CATS:
        L.append(f"| {CAT_LABEL[c]} | {bycat_n.get(c, 0)} | " + " | ".join(pct(bycat.loc[c, a]) for a in arms) + " |")
    L.append("\n![By category](chart_by_category.png)\n")
    L.append("## Significance (paired, exact McNemar on per-question correctness)\n")
    L.append("| Comparison | Only first correct | Only second correct | p-value |")
    L.append("|---|---|---|---|")
    for a, b, ao, bo, p in tests:
        L.append(f"| {SHORT[a]} vs {SHORT[b]} | {ao} | {bo} | {p:.2g} |")
    L.append("\n## Retrieval diagnostics (no LLM involved)\n")
    L.append(f"- Ontology layer plan returns exactly the gold answer: **{onto_hit}/{n_q}** questions.")
    L.append(f"- Vector RAG top-4 passages contain the gold answer: **{rag_hit}/{n_entity_q}** entity-answer questions. By category: "
             + ", ".join(f"{CAT_LABEL[c]} {h}/{n}" for c, (h, n) in rag_by_cat.items() if n) + ".")
    if actions:
        L.append(f"- Arm D verifier actions: " + ", ".join(f"{k} {v}" for k, v in actions.items()) +
                 " (\"corrected\" = the LLM's answer disagreed with the graph and was replaced by the graph result).")
    L.append("\n## How to read this\n")
    L.append("- **Same knowledge, different representation.** RAG passages are generated from the same triples (including "
             "inverses and the reasoner's inferences), in the same sentence style as the ontology facts. The difference between "
             "B and C is which facts reach the model and whether the graph has already done the join.")
    L.append("- **C gives the model the query result line** (\"Answer from the ontology query: ...\"). **C0** removes that line "
             "and keeps only the retrieved facts, to separate the value of graph *retrieval* from graph *computation*.")
    L.append("- **D** = C plus a deterministic check: abstain when the question's entity is not in the ontology, and replace "
             "answers that contradict the graph. D's accuracy is largely the planner's accuracy; the LLM contributes fluency.")
    L.append("- **Grading is automatic string matching** against KB labels plus aliases and accepted alternatives "
             "(`data/aliases.json`, `data/accepted_alternatives.json`). An answer containing an abstention phrase is never "
             "counted correct. Names are matched across punctuation boundaries only, and gold names of 6+ characters are "
             "also accepted with small misspellings (fuzzy ratio >= 90), after masking exact entity mentions and spans that "
             "echo the question, applied identically to every arm.")
    L.append("- **Grader audit.** A 60-answer random sample (`audit_sample.csv`) was checked by reading each answer "
             "(by Claude, not a human annotator - redo this with two people before publishing). The exact-match grader agreed on "
             "57/60; all 3 disagreements were TinyLlama misspelling a correct name it copied from the context (\"Low-Faat Diet\"), "
             "which motivated typo tolerance. Every answer whose grade changed because of typo tolerance (67, all in arms B/C/C0) "
             "is listed by `src/audit_typos.py` and was read; all were misspellings of the gold answer.")
    L.append("\n## Threats to validity\n")
    L.append("- The ontology layer and the question templates were written by the same author. The hand-written paraphrase "
             "subset (30 questions) is a partial check, not a blind test; a colleague-written question set would be stronger.")
    L.append("- Gold answers come from the OWL file, so arms using the file are evaluated on their home turf. The closed-book "
             "arm can be medically right but disagree with the file; accepted alternatives cover the known cases only.")
    L.append("- 46/50 diseases are autosomal recessive; inheritance questions were stratified so guessing 'recessive' is not enough.")
    L.append("- Some enzyme questions are trivial because the enzyme is in the disease name (e.g. Biotinidase Deficiency).")
    L.append("- One deliberate trap question (a fictional variant of PKU) fools the ontology layer's entity linker.")
    L.append("\n## Ontology issues found (source file not modified)\n")
    L.append("- Citrullinemia Type I and Argininosuccinic Aciduria are typed `AminoAcidMetabolismDisorder`; clinically they are urea cycle disorders (excluded from class questions).")
    L.append("- `CofactorResponsiveDisorder` had no equivalentClass axiom; it is added in memory before running HermiT.")
    L.append("- Only Biotin and Vitamin B12 cofactors are modelled; homocystinuria's B6 (PLP) responsiveness is missing.")
    L.append("- `hasCausativeGene` is functional, so multi-gene diseases record one gene (MSUD, propionic acidemia, Zellweger).")
    L.append("- The IRI `GlycogenStorageDiseaseTypeIVonGierke` reads as \"Type IV\" though the label correctly says Type I.")
    L.append("- Non-enzymes (HFE, LDLR, CFTR, ATM) are under `hasDeficientEnzyme`; placeholder metabolites exist for 6 diseases.")
    (RES / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    summary.to_csv(RES / "summary.csv")
    bycat.to_csv(RES / "by_category.csv")
    print((RES / "report.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main(*(sys.argv[1:]))
