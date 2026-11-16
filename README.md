# OntologyLlama

Research on putting an ontology layer between a small LLM (TinyLlama 1.1B) and its answers, using a rare genetic diseases OWL ontology.

## Contents
- **[`onto-vs-rag/`](onto-vs-rag/)** — controlled benchmark: closed-book vs vector RAG vs ontology layer vs ontology + verification, 336 questions, same knowledge source for every arm. Results: [`onto-vs-rag/results/report.md`](onto-vs-rag/results/report.md). How to run: [`onto-vs-rag/README.md`](onto-vs-rag/README.md).

## Headline result (onto-vs-rag)
| Arm | Accuracy (95% CI) |
|---|---|
| Closed-book | 14.9% (11.3–18.8) |
| Vector RAG | 36.3% (31.2–41.4) |
| Ontology layer | 81.5% (77.1–85.7) |
| Ontology layer + verification | 99.7% (99.1–100) |

Grades are automatic and audited by Claude, not yet by human annotators; see the report's "Threats to validity".

## In progress
- **[`onto-evolve/`](onto-evolve/)**: OntoEvolve, an ontology that updates itself from a selected source (PubMed first), with schema-certified gaps and reasoner-gated updates, back-tested against real HPO curator releases (2023 to 2026). See [`onto-evolve/README.md`](onto-evolve/README.md).
