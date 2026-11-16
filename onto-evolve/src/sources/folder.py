"""Local folder connector (stub for later): .txt/.md files; availability date = file mtime."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from sources.base import Doc


class Folder:
    name = "folder"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _docs(self) -> list[Doc]:
        docs = []
        for f in sorted(self.path.rglob("*")):
            if f.suffix.lower() in (".txt", ".md") and f.is_file():
                text = f.read_text(encoding="utf-8", errors="replace")
                docs.append(Doc(str(f), date.fromtimestamp(f.stat().st_mtime), f.stem, text))
        return docs

    def search(self, query: str, date_from: date, date_to: date, limit: int = 20) -> list[str]:
        terms = [t.lower() for t in query.replace('"', " ").split() if len(t) > 2 and t.upper() not in ("AND", "OR")]
        scored = []
        for d in self._docs():
            if date_from <= d.available < date_to:
                score = sum(d.text.lower().count(t) for t in terms)
                if score:
                    scored.append((score, d.id))
        return [i for _, i in sorted(scored, reverse=True)[:limit]]

    def fetch(self, ids: list[str]) -> list[Doc]:
        by_id = {d.id: d for d in self._docs()}
        return [by_id[i] for i in ids if i in by_id]
