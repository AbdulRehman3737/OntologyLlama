"""Readers for HPO release files: hp.obo, phenotype.hpoa, genes_to_disease.txt."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
TAGS = ["v2023-06-06", "v2024-01-16", "v2024-07-01", "v2025-01-16", "v2025-08-11", "v2026-02-16", "v2026-09-01"]
PHENOTYPIC_ABNORMALITY = "HP:0000118"
MODE_OF_INHERITANCE = "HP:0000005"


@dataclass
class Term:
    id: str
    name: str = ""
    synonyms: list[str] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    obsolete: bool = False
    replaced_by: str | None = None


@lru_cache(maxsize=None)
def read_obo(tag: str) -> dict[str, Term]:
    terms: dict[str, Term] = {}
    cur: Term | None = None
    in_term = False
    for line in (RAW / tag / "hp.obo").read_text(encoding="utf-8").splitlines():
        if line.startswith("["):
            in_term = line == "[Term]"
            cur = None
            continue
        if not in_term or not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        val = val.strip()
        if key == "id":
            cur = terms.setdefault(val, Term(val))
        elif cur is None:
            continue
        elif key == "name":
            cur.name = val
        elif key == "synonym" and val.startswith('"'):
            cur.synonyms.append(val[1:val.index('"', 1)])
        elif key == "is_a":
            cur.parents.append(val.split("!")[0].strip())
        elif key == "is_obsolete" and val == "true":
            cur.obsolete = True
        elif key == "replaced_by":
            cur.replaced_by = val
    return terms


def ancestors(terms: dict[str, Term], hp: str) -> set[str]:
    out, stack = set(), [hp]
    while stack:
        t = terms.get(stack.pop())
        if not t:
            continue
        for p in t.parents:
            if p not in out:
                out.add(p)
                stack.append(p)
    return out


def organ_systems(terms: dict[str, Term]) -> dict[str, str]:
    """Top-level phenotype branches (children of 'Phenotypic abnormality')."""
    return {t.id: t.name for t in terms.values() if PHENOTYPIC_ABNORMALITY in t.parents and not t.obsolete}


@lru_cache(maxsize=None)
def read_hpoa(tag: str) -> pd.DataFrame:
    df = pd.read_csv(RAW / tag / "phenotype.hpoa", sep="\t", comment="#", low_memory=False, dtype=str)
    df = df[df.qualifier.isna() | (df.qualifier != "NOT")]  # positive annotations only
    return df


@lru_cache(maxsize=None)
def read_g2d(tag: str) -> pd.DataFrame:
    df = pd.read_csv(RAW / tag / "genes_to_disease.txt", sep="\t", dtype=str)
    return df[df.association_type == "MENDELIAN"]


def pmids(ref: str) -> list[str]:
    return [r.split(":", 1)[1] for r in str(ref).split(";") if r.strip().startswith("PMID:")]
