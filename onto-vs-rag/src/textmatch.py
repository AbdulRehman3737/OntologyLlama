"""Shared text normalisation and KB-entity mention detection.

Used by the grader (which entities does an answer mention?), the ontology layer's
entity linker (which entities does a question mention?) and the arm-D verifier.
Matching is longest-first with span masking, so "Carnitine Supplementation with
Lysine Restriction" is not also counted as "Carnitine Supplementation", and
"Glycogen Storage Disease Type V" is not counted as the metabolite "Glycogen".
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from kg import KG, ROOT, get_kg, local

ALIASES_PATH = ROOT / "data" / "aliases.json"

_ROMAN = {"1": "i", "2": "ii", "3": "iii", "4": "iv", "5": "v"}
# Phrases that are not KB entities but would otherwise produce false mentions.
BLOCKERS = [
    "glycogen storage disease", "glycogen storage disorder", "glycogen storage diseases",
    "lysosomal storage disease", "lysosomal storage disorder", "storage disease",
    "urea cycle disorder", "urea cycle", "organic acidemia", "organic aciduria",
    "fatty acid oxidation disorder", "fatty acid oxidation", "amino acid metabolism disorder",
    "peroxisomal disorder", "inborn error of metabolism", "inborn errors of metabolism",
    "knowledge base", "copper metabolism", "iron overload disorder",
]
TREATMENT_SUFFIXES = (" therapy", " supplementation", " injections", " dietary therapy")


def normalize(text: str) -> str:
    t = text.lower()
    t = t.replace("β", "beta").replace("α", "alpha").replace("γ", "gamma")
    t = re.sub(r"[‐-―]", "-", t)
    # Clause punctuation becomes a "|" boundary so a name never matches across a list separator
    # ("Cerebellar Ataxia, Telangiectasia" must not read as "Ataxia-Telangiectasia").
    # A comma between digits ("1,2-dioxygenase") is part of a name, not a separator.
    t = re.sub(r"(?<=\d),(?=\d)", " ", t)
    t = re.sub(r"[,;:.!?()\[\]\n]+", " | ", t)
    t = re.sub(r"[^a-z0-9|]+", " ", t)
    t = re.sub(r"\btype (\d)\b", lambda m: "type " + _ROMAN.get(m.group(1), m.group(1)), t)
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"(\| )+\|", "|", t).strip(" |")


@dataclass(frozen=True)
class Mention:
    iri: str          # local name, or "" for blockers
    etype: str
    start: int
    end: int
    form: str


class Matcher:
    def __init__(self, kg: KG | None = None):
        self.kg = kg or get_kg()
        aliases = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
        # form -> {etype: local name}; one entity per (form, type), first writer wins
        forms: dict[str, dict[str, str]] = {}

        def add(form: str, name: str, etype: str):
            f = normalize(form)
            if len(f) < 2:
                return
            forms.setdefault(f, {}).setdefault(etype, name)

        for iri, etype in self.kg.entity_type.items():
            name = local(iri)
            for a in aliases.get(name, []):
                add(a, name, etype)
        for iri, etype in self.kg.entity_type.items():
            name = local(iri)
            label = self.kg.label(iri)
            add(label, name, etype)
            m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", label)
            if m and etype != "Metabolite":
                add(m.group(1), name, etype)
                add(m.group(2), name, etype)
            if etype == "Treatment":
                for suf in TREATMENT_SUFFIXES:
                    if label.lower().endswith(suf):
                        add(label[: -len(suf)], name, etype)
            if etype == "Gene":
                add(name, name, etype)
        for b in BLOCKERS:
            forms.setdefault(normalize(b), {"Blocker": ""})

        self.forms = forms
        ordered = sorted(forms.items(), key=lambda kv: -len(kv[0]))
        self._patterns = [
            (re.compile(r"(?<![a-z0-9])" + re.escape(f) + r"(?:s|es)?(?![a-z0-9])"), f, by_type)
            for f, by_type in ordered
        ]

    def mentions(self, text: str) -> list[Mention]:
        t = normalize(text)
        taken: list[tuple[int, int]] = []
        out: list[Mention] = []
        for pat, f, by_type in self._patterns:
            if f not in t:
                continue
            for m in pat.finditer(t):
                s, e = m.span()
                if any(s < te and ts < e for ts, te in taken):
                    continue
                taken.append((s, e))
                for et, name in by_type.items():
                    if et != "Blocker":
                        out.append(Mention(name, et, s, e, f))
        return sorted(out, key=lambda m: m.start)

    def entities(self, text: str, etype: str | None = None) -> list[str]:
        seen: list[str] = []
        for m in self.mentions(text):
            if (etype is None or m.etype == etype) and m.iri not in seen:
                seen.append(m.iri)
        return seen

    def phrase_in(self, phrase: str, text: str) -> bool:
        p = normalize(phrase)
        return bool(re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?:s|es)?(?![a-z0-9])", normalize(text)))

    def forms_of(self, name: str, etype: str) -> list[str]:
        return [f for f, by_type in self.forms.items() if by_type.get(etype) == name]

    def fuzzy_in(self, forms: list[str], text: str, question: str = "", threshold: float = 90) -> bool:
        """Typo-tolerant match ("Low-Faat Diet", "Hexosaaminidase A") for forms >= 6 chars, against
        word n-grams of the same length. Before matching, two kinds of span are masked so they
        cannot earn credit: exact mentions of any KB entity (e.g. the disease name "Biotinidase
        Deficiency" must not count as the enzyme "Biotinidase"), and spans that echo the question."""
        from rapidfuzz import fuzz
        t = normalize(text)
        tok_spans = [(mm.start(), mm.end()) for mm in re.finditer(r"\S+", t)]
        toks = [t[s:e] for s, e in tok_spans]
        masked = [tok == "|" for tok in toks]
        for mt in self.mentions(text):
            for i, (s, e) in enumerate(tok_spans):
                if s < mt.end and mt.start < e:
                    masked[i] = True
        qtoks = normalize(question).split()
        qgrams = {" ".join(qtoks[i:i + n]) for n in range(1, 9) for i in range(len(qtoks) - n + 1)}
        for n in range(1, 9):
            for i in range(len(toks) - n + 1):
                gram = " ".join(toks[i:i + n])
                if len(gram) >= 5 and "|" not in gram and any(
                        len(qg.split()) == n and fuzz.ratio(gram, qg) >= 85 for qg in qgrams):
                    for k in range(i, i + n):
                        masked[k] = True
        for f in forms:
            if len(f) < 6:
                continue
            n = len(f.split())
            for i in range(len(toks) - n + 1):
                if any(masked[i:i + n]):
                    continue
                if fuzz.ratio(" ".join(toks[i:i + n]), f) >= threshold:
                    return True
        return False


@lru_cache(maxsize=1)
def get_matcher() -> Matcher:
    return Matcher()
