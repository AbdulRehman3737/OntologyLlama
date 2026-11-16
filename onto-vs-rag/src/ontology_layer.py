"""The ontology layer: question -> entities -> target relation -> SPARQL plan -> facts.

Deterministic by design (no LLM in the loop), because a 1.1B model cannot write
reliable SPARQL. The LLM only reads the returned facts and phrases the answer.
`verify` implements arm D: check the LLM's answer against the graph result and
correct or abstain when they disagree.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from kg import DISEASE_SUBCLASSES, KG, NS, get_kg, local
from textmatch import Matcher, get_matcher, normalize

# ---------------------------------------------------------------- target detection
HEAD_WORDS = {
    "gene": "Gene", "genes": "Gene",
    "enzyme": "Enzyme", "enzymes": "Enzyme", "protein": "Enzyme", "proteins": "Enzyme",
    "metabolite": "Metabolite", "metabolites": "Metabolite", "substance": "Metabolite", "compound": "Metabolite",
    "disease": "Disease", "diseases": "Disease", "disorder": "Disease", "disorders": "Disease",
    "condition": "Disease", "conditions": "Disease", "illness": "Disease", "syndrome": "Disease",
    "treatment": "Treatment", "treatments": "Treatment", "therapy": "Treatment", "therapies": "Treatment",
    "medication": "Treatment", "drug": "Treatment", "management": "Treatment",
    "cofactor": "Cofactor", "cofactors": "Cofactor", "vitamin": "Cofactor",
    "organ": "OrganSystem", "organs": "OrganSystem", "systems": "OrganSystem",
    "symptom": "Phenotype", "symptoms": "Phenotype", "clinical": "Phenotype", "sign": "Phenotype", "feature": "Phenotype",
    "inheritance": "InheritancePattern", "mode": "InheritancePattern",
}
TRIGGERS = r"\b(which|what|name|list|give|tell)\b"
VERB_HINTS = [
    (r"\btreat(ed|ment)?\b|\bmanage(d|ment)?\b|\bgive patients\b|\bmedication\b", "Treatment"),
    (r"\binherit(ed|ance)?\b|\bpassed down\b|\bx chromosome\b", "InheritancePattern"),
    (r"\baccumulat\w*|\bbuilds? up\b|\bpiles? up\b", "Metabolite"),
    (r"\bcofactor", "Cofactor"),
    (r"\bgene\b", "Gene"),
    (r"\benzyme\b|\bprotein\b", "Enzyme"),
    (r"\bsymptom", "Phenotype"),
]
YESNO_START = ("is ", "are ", "do ", "does ", "can ", "would ", "could ", "should ", "has ", "have ")

CLASS_PATTERNS = {sc: None for sc in DISEASE_SUBCLASSES}
CLASS_EXTRA = {
    "CofactorResponsiveDisorder": [r"cofactor responsive", r"respond\w* to cofactors?"],
    "UreaCycleDisorder": [r"urea cycle disorders?"],
    "OrganicAcidemia": [r"organic acidemias?", r"organic acidurias?"],
}

# Disease -> X paths and X -> Disease paths (SPARQL property-path syntax, ':' prefix)
TO_TARGET = {
    "Gene": [":hasCausativeGene"], "Enzyme": [":hasDeficientEnzyme"], "Metabolite": [":accumulatesMetabolite"],
    "Treatment": [":treatedWith"], "InheritancePattern": [":hasInheritancePattern"], "Phenotype": [":hasSymptom"],
    "OrganSystem": [":hasSymptom", ":affectsOrganSystem"], "Cofactor": [":hasDeficientEnzyme", ":requiresCofactor"],
    "Disease": [],
}
TO_DISEASE = {
    "Disease": [], "Gene": [":causesDisease"], "Enzyme": [":isDeficientEnzymeOf"], "Metabolite": [":isAccumulatedIn"],
    "Phenotype": [":isSymptomOf"], "Treatment": [":isTreatmentFor"], "InheritancePattern": ["^:hasInheritancePattern"],
    "OrganSystem": ["^:affectsOrganSystem", ":isSymptomOf"], "Cofactor": ["^:requiresCofactor", ":isDeficientEnzymeOf"],
}
DIRECT = {("Gene", "Enzyme"): [":encodes"], ("Enzyme", "Gene"): [":encodedBy"], ("Enzyme", "Cofactor"): [":requiresCofactor"]}
ANCHOR_PRIORITY = ["Disease", "Gene", "Enzyme", "Treatment", "Metabolite", "Phenotype", "OrganSystem", "Cofactor", "InheritancePattern"]
# Facts are rendered in the same sentence style as the RAG passages (verbalize.py), so the
# ontology and RAG arms differ in WHICH facts reach the LLM, not in how they are worded.
FACT_TEMPLATE = {
    "hasCausativeGene": "{S} is caused by mutations in the {O} gene.",
    "causesDisease": "Mutations in the {S} gene cause {O}.",
    "hasDeficientEnzyme": "The deficient enzyme or protein in {S} is {O}.",
    "isDeficientEnzymeOf": "Deficiency of {S} causes {O}.",
    "accumulatesMetabolite": "The metabolite that accumulates in {S} is {O}.",
    "isAccumulatedIn": "{S} accumulates in {O}.",
    "hasSymptom": "{O} is a symptom of {S}.",
    "isSymptomOf": "{S} is a symptom of {O}.",
    "affectsOrganSystem": "{S} affects the {O}.",
    "treatedWith": "{S} is treated with {O}.",
    "isTreatmentFor": "{S} is a treatment for {O}.",
    "hasInheritancePattern": "Inheritance of {S} is {o}.",
    "requiresCofactor": "{S} requires the cofactor {O}.",
    "encodes": "The {S} gene encodes {O}.",
    "encodedBy": "{S} is encoded by the {O} gene.",
}


def _a(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


TYPE_NOUN = {
    "Gene": "causative gene", "Enzyme": "deficient enzyme or protein", "Metabolite": "accumulated metabolite",
    "Treatment": "treatment", "InheritancePattern": "inheritance pattern", "Phenotype": "symptom",
    "OrganSystem": "affected organ system", "Cofactor": "cofactor", "Disease": "disease",
}


@dataclass
class Plan:
    kind: str                          # lookup | list | yesno_class | yesno_same_inheritance | none | empty
    target_type: str | None = None
    anchors: list[str] = field(default_factory=list)
    class_name: str | None = None
    path: list[str] = field(default_factory=list)
    sparql: str = ""
    results: list[str] = field(default_factory=list)
    truth: bool | None = None
    facts: list[str] = field(default_factory=list)
    linked: dict = field(default_factory=dict)
    fuzzy: bool = False

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class OntologyLayer:
    def __init__(self, kg: KG | None = None, matcher: Matcher | None = None):
        self.kg = kg or get_kg()
        self.m = matcher or get_matcher()
        self._class_res = {}
        for sc in DISEASE_SUBCLASSES + ["CofactorResponsiveDisorder"]:
            base = normalize(self.kg.class_label(sc))
            pats = [re.escape(base) + r"s?"] + CLASS_EXTRA.get(sc, [])
            self._class_res[sc] = re.compile(r"(?<![a-z0-9])(" + "|".join(pats) + r")(?![a-z0-9])")
        self._fuzzy_forms = [(f, d["Disease"]) for f, d in self.m.forms.items() if "Disease" in d and len(f) >= 8]

    # ------------------------------------------------------------ linking
    def link(self, question: str) -> tuple[dict[str, list[str]], list[str], str, bool]:
        mentions = self.m.mentions(question)
        nq = normalize(question)
        by_type: dict[str, list[str]] = {}
        for mt in mentions:
            by_type.setdefault(mt.etype, [])
            if mt.iri not in by_type[mt.etype]:
                by_type[mt.etype].append(mt.iri)
        spans = [(mt.start, mt.end) for mt in mentions]
        classes = []
        for sc, rx in self._class_res.items():
            for mm in rx.finditer(nq):
                s, e = mm.span()
                inside_entity = any(s >= a and e <= b and (b - a) > (e - s) for a, b in spans)
                if not inside_entity and sc not in classes:
                    classes.append(sc)
        # residual text with entity spans blanked (for keyword detection)
        chars = list(nq)
        for a, b in spans:
            for i in range(a, b):
                chars[i] = " "
        residual = re.sub(r"\s+", " ", "".join(chars)).strip()
        fuzzy = False
        if not ({"Disease", "Gene", "Enzyme", "Treatment", "Metabolite", "Phenotype", "OrganSystem"} & by_type.keys()) and not classes:
            best = self._fuzzy_disease(residual)
            if best:
                by_type["Disease"] = [best]
                fuzzy = True
        return by_type, classes, residual, fuzzy

    def _fuzzy_disease(self, text: str) -> str | None:
        toks = text.split()
        best, best_score = None, 0.0
        for n in range(2, 6):
            for i in range(len(toks) - n + 1):
                gram = " ".join(toks[i:i + n])
                for f, name in self._fuzzy_forms:
                    if abs(len(f) - len(gram)) > 4:
                        continue
                    s = fuzz.ratio(gram, f)
                    if s > best_score:
                        best, best_score = name, s
        return best if best_score >= 90 else None

    # ------------------------------------------------------------ target type
    @staticmethod
    def target_type(question: str, residual: str) -> str | None:
        nq = normalize(question)
        m = re.search(TRIGGERS, nq)
        if m:
            toks = nq[m.end():].split()[:6]
            for t in toks:
                if t in HEAD_WORDS:
                    return HEAD_WORDS[t]
        for rx, t in VERB_HINTS:
            if re.search(rx, residual):
                return t
        return None

    # ------------------------------------------------------------ planning
    def plan(self, question: str) -> Plan:
        kg = self.kg
        by_type, classes, residual, fuzzy = self.link(question)
        nq = normalize(question)
        p = Plan(kind="none", linked={"entities": by_type, "classes": classes}, fuzzy=fuzzy)
        is_yesno = nq.startswith(YESNO_START) and " or " not in nq

        if is_yesno:
            diseases = by_type.get("Disease", [])
            if len(diseases) >= 2 and re.search(r"inherit|same way|mode of inheritance", nq):
                a, b = diseases[:2]
                ia = kg.objects(NS[a], "hasInheritancePattern")
                ib = kg.objects(NS[b], "hasInheritancePattern")
                p.kind, p.anchors, p.target_type = "yesno_same_inheritance", [a, b], "InheritancePattern"
                p.sparql = (f"ASK {{ :{a} :hasInheritancePattern ?i . :{b} :hasInheritancePattern ?i }}")
                p.truth = bool(kg.sparql(p.sparql).askAnswer)
                p.facts = [self._fact(NS[a], "hasInheritancePattern", o) for o in ia] + \
                          [self._fact(NS[b], "hasInheritancePattern", o) for o in ib]
                return p
            if diseases and classes:
                d, sc = diseases[0], classes[0]
                p.kind, p.anchors, p.class_name, p.target_type = "yesno_class", [d], sc, "Disease"
                p.sparql = f"ASK {{ :{d} a :{sc} }}"
                p.truth = bool(kg.sparql(p.sparql).askAnswer)
                cls = kg.class_label(kg.disease_class(NS[d]))
                p.facts = [f"{kg.label(NS[d])} is classified as {_a(cls)} {cls.lower()}."]
                if sc == "CofactorResponsiveDisorder":
                    p.facts += self._cofactor_facts(d)
                elif not p.truth:
                    p.facts.append(f"{kg.label(NS[d])} is not classified as {_a(kg.class_label(sc))} {kg.class_label(sc).lower()}.")
                return p
            if not diseases:
                p.kind = "none"
                p.facts = ["No disease mentioned in the question was found in the ontology, so the answer is unknown."]
                return p

        target = self.target_type(question, residual)
        if target is None and classes:
            target = "Disease"
        if target is None:
            p.facts = ["The question could not be mapped to a relation in the ontology."]
            return p
        p.target_type = target

        # class-membership lists ("List all lysosomal storage disorders", "cofactor-responsive")
        anchors_present = [t for t in ANCHOR_PRIORITY if t != "Cofactor" and by_type.get(t)]
        if target == "Disease" and not anchors_present and (classes or re.search(r"cofactors?", residual)):
            sc = classes[0] if classes else "CofactorResponsiveDisorder"
            p.kind, p.class_name = "list", sc
            p.sparql = f"SELECT DISTINCT ?x WHERE {{ ?x a :{sc} }}"
            p.results = self._run(p.sparql)
            note = " (inferred by the reasoner: its deficient enzyme requires a cofactor)" if sc == "CofactorResponsiveDisorder" else ""
            p.facts = [f"{kg.label(NS[x])} is {_a(kg.class_label(sc))} {kg.class_label(sc).lower()}{note}." for x in p.results]
            return p

        anchor_type = next((t for t in ANCHOR_PRIORITY if t != target and by_type.get(t)), None)
        if anchor_type is None:
            p.kind = "none"
            p.facts = ["No entity mentioned in the question was found in the ontology, so the answer is unknown."]
            return p
        anchor = by_type[anchor_type][0]
        p.anchors = [anchor]
        path = DIRECT.get((anchor_type, target)) or (TO_DISEASE[anchor_type] + TO_TARGET[target])
        p.path = path
        p.sparql = f"SELECT DISTINCT ?x WHERE {{ :{anchor} {'/'.join(path)} ?x }}"
        p.results = self._run(p.sparql)
        p.kind = "list" if target in ("Disease", "OrganSystem") and anchor_type not in ("Gene", "Enzyme") else "lookup"
        p.facts = self._path_facts(NS[anchor], path)
        if not p.results:
            p.kind = "empty"
            p.facts.append(f"The ontology records no {TYPE_NOUN[target]} for {kg.label(NS[anchor])}.")
        return p

    # ------------------------------------------------------------ helpers
    def _run(self, sparql: str) -> list[str]:
        return sorted({local(r[0]) for r in self.kg.sparql(sparql)})

    def _fact(self, s, prop: str, o) -> str:
        return FACT_TEMPLATE[prop].format(S=self.kg.label(s), O=self.kg.label(o), o=self.kg.label(o).lower())

    def _path_facts(self, start, path: list[str]) -> list[str]:
        frontier, facts = [start], []
        for step in path:
            inverse = step.startswith("^")
            prop = step.lstrip("^").lstrip(":")
            nxt = []
            for node in frontier:
                if inverse:
                    for s in self.kg.subjects(prop, node):
                        facts.append(self._fact(s, prop, node))
                        nxt.append(s)
                else:
                    for o in self.kg.objects(node, prop):
                        facts.append(self._fact(node, prop, o))
                        nxt.append(o)
            frontier = sorted(set(nxt), key=str)
        seen, out = set(), []
        for f in facts:
            if f not in seen:
                seen.add(f)
                out.append(f)
        return out

    def _cofactor_facts(self, d: str) -> list[str]:
        kg, facts = self.kg, []
        for e in kg.objects(NS[d], "hasDeficientEnzyme"):
            facts.append(self._fact(NS[d], "hasDeficientEnzyme", e))
            cof = kg.objects(e, "requiresCofactor")
            facts += [self._fact(e, "requiresCofactor", c) for c in cof] or [f"{kg.label(e)} has no cofactor recorded."]
        if d in kg.cofactor_responsive:
            facts.append(f"{kg.label(NS[d])} is a cofactor-responsive disorder (inferred by the reasoner).")
        else:
            facts.append(f"{kg.label(NS[d])} is not a cofactor-responsive disorder.")
        return facts

    def result_line(self, p: Plan) -> str | None:
        if p.kind.startswith("yesno"):
            return f"Answer from the ontology query: {'Yes' if p.truth else 'No'}."
        if p.kind in ("lookup", "list") and p.results:
            return "Answer from the ontology query: " + ", ".join(self.kg.label(NS[r]) for r in p.results) + "."
        if p.kind in ("none", "empty"):
            return "Answer from the ontology query: unknown (not in the knowledge base)."
        return None

    def context(self, p: Plan, with_result: bool = True) -> str:
        lines = [f"- {f}" for f in p.facts]
        r = self.result_line(p) if with_result else None
        return "Facts from the ontology:\n" + "\n".join(lines) + (f"\n{r}" if r else "")

    # ------------------------------------------------------------ arm D verifier
    def verify(self, p: Plan, answer: str) -> tuple[str, str]:
        """Return (final_answer, action) where action is kept | corrected | abstained."""
        kg = self.kg
        if p.kind == "none":
            return "I don't know. The knowledge base has no information about this.", "abstained"
        if p.kind == "empty":
            return f"I don't know. {p.facts[-1]}", "abstained"
        from grade import is_abstention
        if p.kind.startswith("yesno"):
            said = None if is_abstention(answer) else parse_yes_no(answer)
            if said is p.truth:
                return answer, "kept"
            return ("Yes." if p.truth else "No.") + " " + "; ".join(p.facts) + ".", "corrected"
        mentioned = set(self.m.entities(answer, p.target_type))
        results = set(p.results)
        if p.kind == "list":
            ok = not is_abstention(answer) and mentioned == results
        else:
            ok = not is_abstention(answer) and bool(mentioned & results) and mentioned <= results
        if ok:
            return answer, "kept"
        labels = [kg.label(NS[r]) for r in p.results]
        return ", ".join(labels) + ".", "corrected"


def parse_yes_no(text: str) -> bool | None:
    t = normalize(text)
    m = re.search(r"\b(yes|no|not|correct|incorrect|true|false)\b", t)
    if not m:
        return None
    return m.group(1) in ("yes", "correct", "true")


_LAYER: OntologyLayer | None = None


def get_layer() -> OntologyLayer:
    global _LAYER
    if _LAYER is None:
        _LAYER = OntologyLayer()
    return _LAYER


if __name__ == "__main__":
    import sys
    layer = get_layer()
    for q in sys.argv[1:] or ["Which cofactor does the enzyme deficient in Propionic Acidemia require?"]:
        pl = layer.plan(q)
        print(q, "\n ", pl.kind, pl.target_type, pl.anchors, pl.class_name, pl.results, "\n ", pl.sparql)
        print("  " + layer.context(pl).replace("\n", "\n  "))
