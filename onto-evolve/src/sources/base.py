"""Pluggable source interface: the 'selected base' the ontology updates itself from."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Protocol


@dataclass
class Doc:
    id: str                 # e.g. "PMID:12345" or a file path
    available: date         # when the system could first have seen it (PubMed entrez date)
    title: str
    text: str               # abstract or document text
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["available"] = self.available.isoformat()
        return d

    @staticmethod
    def from_dict(d: dict) -> "Doc":
        return Doc(d["id"], date.fromisoformat(d["available"]), d["title"], d["text"], d.get("meta", {}))


class Source(Protocol):
    name: str

    def search(self, query: str, date_from: date, date_to: date, limit: int = 20) -> list[str]:
        """Return document ids available in [date_from, date_to)."""

    def fetch(self, ids: list[str]) -> list[Doc]:
        """Return documents for ids (cached)."""
