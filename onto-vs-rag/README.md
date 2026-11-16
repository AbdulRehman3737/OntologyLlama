# onto-vs-rag

Does an ontology layer between the question and a small LLM beat vector RAG?
Benchmark on a 50-disease rare-genetic-disease OWL ontology with TinyLlama 1.1B.

## Arms
| Arm | What the LLM sees |
|---|---|
| A closed-book | the question only |
| B vector RAG | top-4 MiniLM-retrieved passages verbalised from the same OWL triples |
| C ontology layer | facts returned by a deterministic plan (entity linking → relation → SPARQL property path), plus the query result line |
| D ontology + verify | C, then the answer is checked against the graph: abstain if nothing links, replace contradicting answers |
| C0 (ablation) | C without the query result line (retrieved facts only) |

All arms use the same model, prompt frame and decoding (`src/llm.py`).

## Run
```bash
ollama pull tinyllama
uv sync
uv run pytest
uv run python src/questions.py          # regenerate data/questions.jsonl (fixed seed)
uv run python src/run.py --limit 10 --out results/smoke.jsonl
uv run python src/run.py                # full run, resumable -> results/responses.jsonl
uv run python src/report.py             # -> results/report.md + charts
```
Set `PYTHONIOENCODING=utf-8` on Windows consoles.

## Layout
- `src/kg.py` load OWL (rdflib), materialise inverses, run HermiT (owlready2, needs Java) for `CofactorResponsiveDisorder`
- `src/textmatch.py` entity mention detection shared by linker and grader
- `src/ontology_layer.py` planner, SPARQL, fact rendering, arm-D verifier
- `src/verbalize.py`, `src/rag.py` RAG corpus and retriever
- `src/questions.py` question generator (templated + hand-written paraphrases + fictional entities)
- `src/grade.py` automatic grader; `src/report.py` statistics (bootstrap CIs, exact McNemar) and charts
- `data/aliases.json`, `data/accepted_alternatives.json` synonyms and medically valid alternative answers

## Swapping the model
Change `MODEL` in `src/llm.py` to any Ollama model tag (e.g. `llama3.1:8b`) and write to a new results file with `--out`.
