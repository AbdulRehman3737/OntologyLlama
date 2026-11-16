# OntoEvolve (work in progress)

A self-updating ontology RAG. A rare-disease slice of the Human Phenotype Ontology, frozen at release v2023-06-06 (T0), updates itself from PubMed. Updates are back-tested against what HPO curators actually added in six later releases (to v2026-09-01).

## Contributions
1. **Schema-certified gaps:** TBox existentials (e.g. `MendelianDisease ⊑ ∃hasCausativeGene.Gene`) are checked closed-world to find "known unknowns" that drive targeted acquisition (`src/gaps.py`).
2. **Reasoner-gated, provenance-weighted updates:** extracted facts are grounded to HPO and checked by HermiT on a per-disease module that uses the HPO class hierarchy. Conflicts with `NOT` annotations are repaired by a weighted maximal consistent subset; curated facts are flagged for review, never deleted (`src/gate.py`).
3. **Back-testing against curator releases:** precision (a lower bound), recall and lead time against stable curator additions (`src/backtest.py`).
4. **Drift QA:** a static vs a self-updating ontology RAG, with TinyLlama answering questions whose answers changed after T0 (`src/drift_qa.py`).

Prior work and novelty: [`docs/related_work.md`](docs/related_work.md).

## Findings so far (pilot slice)
- 98% of curator phenotype additions cite papers already in PubMed; the median paper-to-ontology lag is 8.8 years. For 88%, the paper predates T0.
- Curators filled only 34 of 1,944 certified gene gaps in three years.
- Release v2025-08-11 is anomalous (+2,188 then −2,073 gene links), so only additions still present in the final release count.
- The T0 release contains 6 direct positive/`NOT` contradictions; all 6 were resolved later.

## Run
```bash
# 1. raw data (≈300 MB, not in git)
for t in v2023-06-06 v2024-01-16 v2024-07-01 v2025-01-16 v2025-08-11 v2026-02-16 v2026-09-01; do
  gh release download $t --repo obophenotype/human-phenotype-ontology --dir data/raw/$t \
    --pattern genes_to_disease.txt --pattern phenotype.hpoa --pattern hp.obo; done
# 2. environment and models (extractor runs on GPU via Ollama)
uv sync
ollama pull qwen3:8b
ollama pull tinyllama
# 3. build, test, run
uv run python src/data_build.py
uv run pytest
uv run python src/bakeoff.py --n 50
uv run python src/evolve.py --run t0 --cutoff 2023-06-06 --docs 15
uv run python src/backtest.py t0
uv run python src/drift_qa.py --run t0
```
Use `PYTHONPATH=src` when running scripts directly, and `PYTHONIOENCODING=utf-8` on Windows.
