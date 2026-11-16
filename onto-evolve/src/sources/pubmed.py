"""PubMed connector via NCBI E-utilities.

- Time windows use the Entrez date (when the record entered PubMed), i.e. when an automatic
  system could first have seen it. This is what prevents leakage in the back-test.
- Everything is cached on disk; requests are rate-limited (3/s, 10/s with NCBI_API_KEY).
- Queries contain only disease names / gene symbols. No user information is sent; the tool
  name is generic and no contact email is attached.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import requests

from sources.base import Doc

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CACHE = Path(__file__).resolve().parents[2] / "data" / "cache" / "pubmed"
_MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _date(node) -> date | None:
    if node is None:
        return None
    y = node.findtext("Year")
    if not y:
        md = node.findtext("MedlineDate")
        return date(int(md[:4]), 1, 1) if md and md[:4].isdigit() else None
    m = node.findtext("Month") or "1"
    m = int(m) if m.isdigit() else _MONTHS.get(m[:3], 1)
    d = node.findtext("Day") or "1"
    return date(int(y), m, int(d) if d.isdigit() else 1)


def parse_efetch(xml_text: str) -> list[Doc]:
    docs = []
    root = ET.fromstring(xml_text)
    for art in root.iter("PubmedArticle"):
        pmid = art.findtext("MedlineCitation/PMID")
        a = art.find("MedlineCitation/Article")
        title = "".join(a.find("ArticleTitle").itertext()) if a is not None and a.find("ArticleTitle") is not None else ""
        parts = []
        for at in art.iter("AbstractText"):
            label = at.get("Label")
            txt = "".join(at.itertext()).strip()
            parts.append(f"{label}: {txt}" if label else txt)
        entrez = None
        for pd_ in art.iter("PubMedPubDate"):
            if pd_.get("PubStatus") in ("entrez", "pubmed"):
                entrez = _date(pd_)
                if pd_.get("PubStatus") == "entrez":
                    break
        pub = _date(a.find("Journal/JournalIssue/PubDate")) if a is not None else None
        avail = entrez or pub or date(1900, 1, 1)
        docs.append(Doc(f"PMID:{pmid}", avail, title, "\n".join(parts),
                        {"pubdate": pub.isoformat() if pub else None}))
    return docs


class PubMed:
    name = "pubmed"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("NCBI_API_KEY")
        self.min_interval = 0.11 if self.api_key else 0.34
        self._last = 0.0
        (CACHE / "docs").mkdir(parents=True, exist_ok=True)
        (CACHE / "search").mkdir(parents=True, exist_ok=True)

    def _get(self, endpoint: str, params: dict) -> requests.Response:
        params = {**params, "tool": "onto-evolve"}
        if self.api_key:
            params["api_key"] = self.api_key
        for attempt in range(5):
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            r = requests.get(f"{EUTILS}/{endpoint}", params=params, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r
        r.raise_for_status()
        return r

    def search(self, query: str, date_from: date, date_to: date, limit: int = 20) -> list[str]:
        key = hashlib.sha1(f"{query}|{date_from}|{date_to}|{limit}".encode()).hexdigest()
        f = CACHE / "search" / f"{key}.json"
        if f.exists():
            return json.loads(f.read_text())["ids"]
        r = self._get("esearch.fcgi", {"db": "pubmed", "term": query, "retmode": "json", "retmax": limit,
                                       "sort": "relevance", "datetype": "edat",
                                       "mindate": date_from.strftime("%Y/%m/%d"),
                                       "maxdate": date_to.strftime("%Y/%m/%d")})
        ids = [f"PMID:{i}" for i in r.json()["esearchresult"].get("idlist", [])]
        f.write_text(json.dumps({"query": query, "from": str(date_from), "to": str(date_to), "ids": ids}))
        return ids

    def fetch(self, ids: list[str]) -> list[Doc]:
        out, missing = {}, []
        for i in ids:
            f = CACHE / "docs" / f"{i.split(':')[1]}.json"
            if f.exists():
                out[i] = Doc.from_dict(json.loads(f.read_text(encoding="utf-8")))
            else:
                missing.append(i)
        for k in range(0, len(missing), 100):
            batch = [m.split(":")[1] for m in missing[k:k + 100]]
            r = self._get("efetch.fcgi", {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"})
            for d in parse_efetch(r.text):
                (CACHE / "docs" / f"{d.id.split(':')[1]}.json").write_text(json.dumps(d.to_dict()), encoding="utf-8")
                out[d.id] = d
        return [out[i] for i in ids if i in out]
