"""Automatic grading of free-text answers against KB gold answers.

Definitions (per answer):
  correct       single/any: a gold entity (or accepted alternative) is mentioned
                list: F1 >= 0.5 over KB entities of the answer type
                yesno: parsed yes/no equals gold
                abstain: the answer abstains and names no entity of the asked type
  strict        single: correct AND no other KB entity of the answer type is mentioned
                list: exact set match; other modes: same as correct
  score         0/1, or F1 for list questions (used for mean-score charts)
  abstained     answer contains an abstention phrase ("I don't know", "not in the context", ...);
                an abstaining answer is never counted correct (except on unanswerable questions)
  hallucinated  answered (did not abstain) but not correct
"""
from __future__ import annotations

import re

from ontology_layer import parse_yes_no
from textmatch import get_matcher, normalize

ABSTAIN_RX = re.compile("|".join([
    r"\bi don ?t know\b", r"\bi do not know\b", r"\bnot sure\b", r"\bunknown\b",
    r"\bno information\b", r"\bdon ?t have (enough )?information\b", r"\bdo not have (enough )?information\b",
    r"\bnot (in|available in|found in|mentioned in|contained in|provided in|present in|listed in|included in) the "
    r"(knowledge base|context|information|passages|ontology|facts|text)\b",
    r"\b(does|do) not (contain|mention|provide|include|specify)\b",
    r"\b(cannot|can ?t|unable to) (determine|answer|find|identify|provide)\b",
    r"\bno (such|known|recognized) (disease|gene|condition|syndrome|enzyme)\b",
    r"\bnot a (known|recognized|real)\b", r"\brecords no\b", r"\bno (data|record)\b",
]))


# Typo tolerance: TinyLlama doubles letters in copied names ("Low-Faat Diet"). Found by the manual
# audit; gold names of >= 6 characters are also accepted at fuzz.ratio >= 90. Applies to every arm.
TYPO_TOLERANT = True


def is_abstention(text: str) -> bool:
    return bool(ABSTAIN_RX.search(normalize(text)))


def grade(q: dict, answer: str) -> dict:
    m = get_matcher()
    atype, mode = q["answer_type"], q["mode"]
    mentioned = m.entities(answer, atype)
    # Any abstention phrase counts as abstaining, even if entity names are echoed
    # ("X is not mentioned in the information, so I don't know").
    abst = is_abstention(answer)
    out = {"mentioned": mentioned, "abstained": False, "correct": False, "strict": False, "score": 0.0,
           "precision": None, "recall": None, "f1": None, "yesno_parsed": None}

    if mode == "abstain":
        named = bool(mentioned)
        out["abstained"] = abst and not named
        out["correct"] = out["strict"] = abst and not named
        out["score"] = float(out["correct"])
    elif mode == "yesno":
        said = None if abst else parse_yes_no(answer)
        out["yesno_parsed"] = said
        out["abstained"] = abst
        out["correct"] = out["strict"] = said is q["gold_bool"]
        out["score"] = float(out["correct"])
    elif mode == "list":
        gold, ment = set(q["gold"]), set(mentioned)
        if TYPO_TOLERANT:
            ment |= {g for g in gold - ment if m.fuzzy_in(m.forms_of(g, atype), answer, q.get("question", ""))}
        tp = len(gold & ment)
        p = tp / len(ment) if ment else 0.0
        r = tp / len(gold) if gold else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        # A list that names entities is graded as a list even if it ends with "I don't know".
        abst = abst and not ment
        out.update(precision=p, recall=r, f1=f1, score=f1, abstained=abst,
                   correct=f1 >= 0.5, strict=(ment == gold) and not abst)
    else:  # single / any
        alt_hit = any(m.phrase_in(a, answer) for a in q.get("alt", []))
        alt_entities = {e for a in q.get("alt", []) for e in m.entities(a, atype)}
        allowed = set(q["gold"]) | alt_entities
        hit = bool(set(mentioned) & set(q["gold"])) or alt_hit
        if not hit and TYPO_TOLERANT:
            gold_forms = [f for g in q["gold"] for f in m.forms_of(g, atype)]
            hit = m.fuzzy_in(gold_forms + [normalize(a) for a in q.get("alt", [])], answer, q.get("question", ""))
        out["abstained"] = abst
        out["correct"] = hit and not abst
        out["strict"] = out["correct"] and (mode == "any" or set(mentioned) <= allowed)
        out["score"] = float(out["correct"])
    out["hallucinated"] = not out["correct"] and not out["abstained"]
    return out
