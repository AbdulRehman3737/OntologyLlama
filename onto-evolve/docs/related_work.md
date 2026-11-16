# OntoEvolve: Prior-Work Matrix

Compiled 2026-11-17. Scope: 2023–2026 work on LLM ontology learning and evolution, self-updating KGs and GraphRAG, reasoner- or SHACL-validated population, temporal holdout on ontology/KG releases and lead time, gap-triggered acquisition, and biomedical curation automation. A few pre-2023 papers are included where they set the baseline for a contribution (marked).

Contributions are scored as follows.

- **C1**: schema-certified gaps (TBox existential / min-cardinality axioms define completeness; missing fillers drive acquisition, both sweep and lazy).
- **C2**: reasoner-gated, provenance-weighted updates (grounding to HGNC/HPO, HermiT check, evidence-weighted minimal-conflict-set repair).
- **C3**: back-testing against real curator releases, with a lead-time metric.
- **C4**: drift QA (static vs self-updating ontology RAG on questions whose answers changed between releases).

**Read depth** says how much of each paper was read. *Abstract* means the arXiv or publisher abstract page. *Full text* means the HTML or PDF was fetched and the relevant sections were queried. *Snippet* means only search-engine excerpts were seen. Scores based only on an abstract or snippet may miss details in the body of the paper.

---

> **No WARNING: no paper found that does C1+C2 together, or C3, essentially as described.**
> Three things come close enough that some claims need to be narrowed.
> 1. **DRAGON-AI already uses a temporal holdout on HP, MONDO and GO.** Its test terms were "added to the ontology after November 2022" ([PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC11484368/)). OntoEvolve must not claim "first temporal evaluation on HPO releases". The claim should be "first back-test of literature-driven *annotation updates* against the curator *diff* of successive releases, with lead time".
> 2. **A lead-time metric already exists.** CKM reports that validated hypotheses preceded matching papers by a mean of 404 days ([arXiv 2604.12243](https://arxiv.org/abs/2604.12243)), though in machine learning, not biomedicine, and against papers rather than curated releases. Cite it as the closest analogue and do not claim the metric itself as new.
> 3. **Most of C2 already exists, in separate pieces.** HermiT diagnose-and-repair loops for LLM output exist (NeOn-GPT line, [snippet](https://www.researchgate.net/publication/408126702_Extended_NeOn-GPT_Advancing_LLM-Powered_Ontology_Learning_Through_Ontology_Reuse_and_Automated_Verification)). Confidence and timestamp conflict resolution over PubMed-extracted triples exists (MedKGent, [arXiv 2508.12393](https://arxiv.org/html/2508.12393v2)). The new part is the *combination* (reasoner gate plus evidence-weighted minimal-conflict-set repair), not either half alone.

---

## 1. Summary matrix

| # | Paper (short) | Year / venue | Status | C1 | C2 | C3 | C4 | Read depth |
|---|---|---|---|---|---|---|---|---|
| 1 | DRAGON-AI | 2024, J. Biomed. Semantics | peer-reviewed | no | partial | **partial** | no | full text (methods) |
| 2 | OntoExtend | 2026, Semantics (accepted) | preprint, accepted | partial | no* | no | no | abstract |
| 3 | Evo-DKD | 2026, IEEE ICMLA (accepted) | preprint, accepted | no | partial | no | no | abstract |
| 4 | Extended NeOn-GPT / LLMs4Life | 2024–2026, Semantic Web journal | peer-reviewed (SWJ) | no | partial | no | no | snippet |
| 5 | LLMs4OL challenges 2024–2026 | ISWC challenge | peer-reviewed proceedings | no | no | no | no | challenge pages |
| 6 | Structured Decomposition + SW integration | 2026 | preprint | no | partial | no | no | full text (partial) |
| 7 | Neuro-symbolic HermiT feedback (withdrawn) | 2025 | **withdrawn** preprint | no | partial | no | no | abstract |
| 8 | SPIRES / OntoGPT | 2024, Bioinformatics | peer-reviewed | no | partial | no | no | snippet + abstract |
| 9 | MedKGent | 2025 | preprint | no | **partial** | partial (anecdotal) | partial | full text |
| 10 | AMG-RAG | 2025, Findings of EMNLP | peer-reviewed | partial | partial | no | partial | abstract + snippet |
| 11 | PrimeKG-CL | 2026 | preprint | no | no | **partial** | partial | abstract |
| 12 | Continuous Knowledge Metabolism (CKM) | 2026, ICML AI4Research WS | workshop / preprint | no | no | **partial (lead time)** | no | abstract |
| 13 | ForeSCITE | 2026 | preprint | no | no | partial | no | abstract |
| 14 | HPOFiller / HPOLabeler (pre-2023 baseline) | 2020–2021, Bioinformatics | peer-reviewed | no | no | partial | no | snippet |
| 15 | GOFlowLLM | 2025–2026 | preprint (PMC copy) | no | partial | partial | no | snippet |
| 16 | FlyAOC | 2026, NeurIPS D&B (accepted) | accepted | no | no | partial | no | abstract |
| 17 | Generate-on-Graph (GoG) | 2024, EMNLP | peer-reviewed | partial | no | no | no | abstract + snippet |
| 18 | RFM-RAG (retrieval feedback memory) | 2025 | preprint | partial | no | no | no | abstract |
| 19 | KG-RAG under incompleteness | 2025, IRISAI'25 workshop | workshop | partial (motivation) | no | no | partial | abstract |
| 20 | CROWN-QA | 2026 | preprint | partial (concept) | no | no | no | abstract |
| 21 | Zep / Graphiti | 2025 | preprint (industry) | no | partial | no | partial | abstract + snippet |
| 22 | LightRAG | 2024 | preprint | no | no | no | no | abstract |
| 23 | HippoRAG 2 | 2025, ICML | peer-reviewed | no | no | no | partial | snippet |
| 24 | TG-RAG / ECT-QA | 2025 | preprint | no | no | no | **partial** | abstract |
| 25 | EvoWiki / HoH / EvolvingQA | 2024–2025 (EvolvingQA NAACL 2024) | mixed | no | no | no | **partial** | abstract |
| 26 | OG-RAG | 2025, EMNLP | peer-reviewed | no | no | no | partial (static baseline) | snippet |
| 27 | KG-RAG / SPOKE | 2024, Bioinformatics | peer-reviewed | no | no | no | partial (static baseline) | snippet |
| 28 | Entailed-negation repair (OWL 2 DL) | 2026, ICAIDE (accepted) | accepted | no | partial | no | partial | abstract |
| 29 | Ontology-grounded reasoner-verified benchmarks | 2026, NeurIPS AIDaR WS | workshop | no | no | no | partial | abstract |
| 30 | LLM knowledge of rare diseases | 2025, HGG Advances | peer-reviewed | no | no | partial | no | snippet |
| 31 | PubTator 3.0 | 2024, NAR | peer-reviewed | no | partial (substrate) | no | no | snippet |

\* "no" means "not mentioned in the abstract".

---

## 2. Per-paper entries

### A. LLM ontology learning, extension and evolution

**1. Dynamic Retrieval Augmented Generation of Ontologies using AI (DRAGON-AI)**
Toro et al., *Journal of Biomedical Semantics* 15:19, 2024 (peer-reviewed). [arXiv 2312.10904](https://arxiv.org/abs/2312.10904) · [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC11484368/)
*Summary:* RAG over existing OBO ontologies and text to generate new terms (definitions, relationships, logical definitions), evaluated by experts across 10 ontologies including HP, MONDO and GO.
- **C1 no.** It generates terms on request (including from GitHub issues). It does not certify gaps from TBox axioms.
- **C2 partial.** Generation is grounded in ontology vocabulary through retrieval. There is no reasoner gate: ELK is used only as a SubClassOf baseline, and "couple DRAGON-AI with an OWL reasoner" is listed as future work ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11484368/)).
- **C3 partial, the closest temporal design.** Test terms were "added to the ontology after November 2022" to limit leakage ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11484368/)). However, it reconstructs held-out *classes* given their labels. It does not discover *annotations* from dated literature, it does not diff releases, and it has no lead time.
- **C4 no.**

**2. OntoExtend: Requirement-driven and Scalable Ontology Extension with LLMs**
Lippolis et al., 2026, accepted to the Semantics 2026 research track. [arXiv 2607.17963](https://arxiv.org/abs/2607.17963)
*Summary:* RAG-based extension of existing ontologies driven by competency questions (CQs). Evaluated on 39 CQs from two ontologies with functional tests and expert ratings.
- **C1 partial.** Extension is requirement-driven, but the requirements are CQs supplied by humans, not gaps derived from the TBox.
- **C2 no (abstract only).** The abstract reports structural issues and functional tests. It does not mention a reasoner gate or evidence weighting.
- **C3 no.** Evaluation is by experts and CQs.
- **C4 no.**

**3. Evo-DKD: Dual-Knowledge Decoding for Autonomous Ontology Evolution**
Raman et al., 2025, v2 2026, accepted at IEEE ICMLA 2026. [arXiv 2507.21438](https://arxiv.org/abs/2507.21438)
*Summary:* Prompt-simulated dual decoding. One stream proposes ontology edits and the other writes natural-language justifications. Edits are gated by consistency checks and cross-verification against the justifications. Use cases include healthcare ontology refinement.
- **C1 no.**
- **C2 partial.** It has "consistency checks" but no named OWL reasoner, no provenance weighting and no conflict-set repair (abstract).
- **C3 no.** Precision and recall are measured against reference edits, not real releases ([HTML snippet](https://arxiv.org/html/2507.21438v1)).
- **C4 no.** Downstream tasks are not drift QA.

**4. Extended NeOn-GPT / LLMs4Life**
Fathallah et al. LLMs4Life: [arXiv 2412.02035](https://arxiv.org/pdf/2412.02035). Extended NeOn-GPT: *Semantic Web* journal, 2026 ([record](https://www.citedrive.com/en/discovery/extended-neon-gpt-advancing-llm-powered-ontology-learning-through-ontology-reuse-and-automated-verification/), [ResearchGate](https://www.researchgate.net/publication/408126702_Extended_NeOn-GPT_Advancing_LLM-Powered_Ontology_Learning_Through_Ontology_Reuse_and_Automated_Verification)). Peer-reviewed.
*Summary:* An LLM pipeline following the NeOn methodology, ending in verification with HermiT, Pellet and OOPS!. Errors are fed back to the LLM for repair, up to 25 iterations (per snippet).
- **C1 no.**
- **C2 partial, the closest reasoner-repair loop.** HermiT diagnosis feeds LLM repair. But it targets TBox ontology learning, not ABox population from literature. Repair is done by the LLM, with no minimal conflict sets and no evidence or recency weighting.
- **C3 no.**
- **C4 no.**
- *Read depth:* search snippets only. Verify the repair details in the full text.

**5. LLMs4OL Challenges (2024, 2025, 2026)**
ISWC challenge with proceedings in TIB Open Conference Proceedings. [2025 overview](https://sites.google.com/view/llms4ol2025/challenge-overview) · [2025 overview paper](https://oa.tib.eu/renate/items/7a045b0b-c347-4003-803d-1a9e63007209) · [2026 site](https://sites.google.com/view/llms4ol2026/challenge-overview)
*Summary:* Shared tasks for term typing, taxonomy discovery, and non-taxonomic relation extraction. 2026 adds "Reuse" (extend a partial ontology from text) and "Flagship" (text to ontology).
- **C1 no.**
- **C2 no.** Scoring is precision, recall and F1, or graph similarity. There is no reasoner gate.
- **C3 no.** Gold standards are static.
- **C4 no.**
- *Positioning:* the 2026 Reuse task is the nearest benchmark for the extraction step, but it has no temporal axis.

**6. Structured Decomposition for LLM Reasoning: Cross-Domain Validation and Semantic Web Integration**
Sadowski and Chudziak, 2026, preprint. [arXiv 2601.01609](https://arxiv.org/abs/2601.01609) · [HTML](https://arxiv.org/html/2601.01609)
*Summary:* The LLM extracts entities and assertions into an OWL 2 ontology. A SWRL/OWL reasoner then performs consistency checking, classification and rule execution. Tested on legal, scientific-method and clinical-trial-eligibility tasks with 11 LLMs.
- **C1 no.**
- **C2 partial.** It does LLM population plus reasoner verification. It has no repair procedure (not described) and no provenance weighting. Its §2.5.2 states that frameworks integrating LLMs as ontology population components with formal verification "remain underexplored" (full text). This is citable support for the C2 gap.
- **C3 no.**
- **C4 no.**

**7. Enhancing LLMs through Neuro-Symbolic Integration and Ontological Reasoning**
Magana Vsevolodovna and Monti, 2025, **withdrawn** ("inaccuracies in references and architecture description"). [arXiv 2504.07640](https://arxiv.org/abs/2504.07640)
*Summary:* HermiT checks LLM statements mapped to OWL. Inconsistencies trigger explanatory feedback and LLM regeneration.
- **C1 no.**
- **C2 partial.** It gates *answers*, not KB updates. There is no weighting. Cite it only with the withdrawal caveat.
- **C3 no.**
- **C4 no.**

**8. SPIRES (OntoGPT)**
Caufield et al., *Bioinformatics* 40(3), 2024 (peer-reviewed). [arXiv 2304.02711](https://arxiv.org/abs/2304.02711)
*Summary:* Zero-shot, schema-conforming LLM extraction with deterministic grounding of entities to ontology and vocabulary IDs. Used by the Monarch Initiative.
- **C1 no.** The schema drives the extraction template, but missing slots are not treated as certified gaps that trigger acquisition.
- **C2 partial.** This is the grounding half of C2, to be cited for HGNC and HPO grounding. It has no reasoner and no weighting.
- **C3 no.**
- **C4 no.**

### B. Self-updating, continual and temporal KGs / GraphRAG

**9. MedKGent: LLM Agent Framework for Constructing a Temporally Evolving Medical KG**
Zhang et al., 2025, preprint. [arXiv 2508.12393](https://arxiv.org/abs/2508.12393v2) · [HTML full text](https://arxiv.org/html/2508.12393v2)
*Summary:* Builds a KG day by day from more than 10M PubMed abstracts (1975–2023). It has an extractor agent and a constructor agent. Entities are grounded with PubTator3. It reports RAG gains on 7 medical QA benchmarks.
- **C1 no.** It ingests everything chronologically and has no notion of what is missing.
- **C2 partial, the closest to provenance weighting.** Repeated triples raise confidence through a noisy-OR update. PMIDs are accumulated and timestamps refreshed. When two relations link the same pair, an LLM picks one using confidence and timestamps (full text). There is no OWL reasoner, no formal axioms and no minimal conflict set, and the choice is made by the LLM, not by a principled repair.
- **C3 partial, anecdotal only.** One tocilizumab–COVID-19 case was later corroborated. There is no back-test against curated releases (full text).
- **C4 partial.** Static QA benchmarks only, with no changed-answer questions.

**10. AMG-RAG: Agentic Medical Knowledge Graphs Enhance Medical QA**
Rezaei et al., *Findings of EMNLP 2025* (peer-reviewed). [ACL Anthology](https://aclanthology.org/2025.findings-emnlp.679/) · [arXiv 2502.13010](https://arxiv.org/abs/2502.13010)
*Summary:* An LLM agent continuously builds and updates a medical KG from PubMed and search, with confidence-scored edges, and answers MedQA and MedMCQA.
- **C1 partial.** Per a search snippet, the agent searches the KG and triggers expansion for missing coverage. The gaps are judged by the LLM, not certified by a schema.
- **C2 partial.** It has edge confidence scores but no reasoner and no conflict repair (abstract).
- **C3 no.**
- **C4 partial.** It is motivated by "evolving medical knowledge" but evaluated on static QA.

**11. PrimeKG-CL: Continual Graph Learning Benchmark on Evolving Biomedical KGs**
Radwan et al., 2026, preprint (the repository name suggests a NeurIPS 2026 submission). [arXiv 2605.10529](https://arxiv.org/abs/2605.10529)
*Summary:* Two real PrimeKG snapshots (June 2021 and July 2023). Test facts are stratified as persistent, added or removed. It covers continual KGE, entity classification and KGQA.
- **C1 no.**
- **C2 no.**
- **C3 partial.** It evaluates on *real* release diffs of biomedical KGs, which is the closest data design. The predictor is KG embedding, not literature extraction, and there is no lead time.
- **C4 partial.** It has a KGQA task over the evolving KG. Its finding that "standard metrics conflate retaining valid facts with failing to forget deprecated ones" directly supports C4's framing.

**12. Zep: A Temporal Knowledge Graph Architecture for Agent Memory (Graphiti)**
Rasmussen et al., 2025, industry preprint. [arXiv 2501.13956](https://arxiv.org/abs/2501.13956) · [Neo4j blog](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/)
*Summary:* Bi-temporal KG memory. Contradicted edges are invalidated rather than deleted. It is evaluated on DMR and LongMemEval.
- **C1 no.**
- **C2 partial.** Temporal invalidation on contradiction is a recency-based resolution, but contradictions are LLM-judged, with no ontology or reasoner (blog and snippets; the abstract does not describe it).
- **C3 no.**
- **C4 partial.** It covers temporal memory QA, not ontology drift.

**13. LightRAG**
Guo et al., 2024, preprint (no venue listed on arXiv). [arXiv 2410.05779](https://arxiv.org/abs/2410.05779)
*Summary:* Graph-based RAG with an "incremental update algorithm" for new data.
- **C1 no.**
- **C2 no.** It merges without validation.
- **C3 no.**
- **C4 no.**
- *Positioning:* a natural engineering baseline for "self-updating RAG without a schema".

**14. HippoRAG 2: From RAG to Memory, Non-Parametric Continual Learning for LLMs**
Gutiérrez et al., ICML 2025 (PMLR 267). [PMLR](https://proceedings.mlr.press/v267/gutierrez25a.html) · [arXiv 2502.14802](https://arxiv.org/abs/2502.14802)
*Summary:* A Personalized-PageRank KG memory framed as non-parametric continual learning.
- **C1 no.**
- **C2 no.**
- **C3 no.**
- **C4 partial.** It is framed as continual learning but measures associativity and factual recall, not changed answers.

**15. RAG Meets Temporal Graphs (TG-RAG, ECT-QA)**
Han et al., 2025, preprint. [arXiv 2510.13590](https://arxiv.org/abs/2510.13590)
*Summary:* Temporal KG plus a time hierarchy, with incremental updates. The ECT-QA benchmark comes with an incremental-update protocol (base 2020–2023 corpus, then 2024 updates).
- **C1 no.**
- **C2 no.**
- **C3 no.**
- **C4 partial, the closest protocol.** It has a base-then-update evaluation, but in the earnings-call domain and with no ontology or curator truth.

**16. Drift and outdated-knowledge QA: EvoWiki, HoH, EvolvingQA**
- EvoWiki: [arXiv 2412.13582](https://arxiv.org/abs/2412.13582), preprint.
- HoH: [arXiv 2503.04800](https://arxiv.org/abs/2503.04800), preprint.
- EvolvingQA ("Carpe Diem"): [arXiv 2311.08106](https://arxiv.org/pdf/2311.08106), NAACL 2024.

*Summary:* Benchmarks of stable vs evolved knowledge, built from Wikipedia snapshot diffs. HoH shows that outdated passages in the corpus mislead RAG even when current ones are present.
- **C1 no.**
- **C2 no.**
- **C3 no.**
- **C4 partial.** This is the general-domain version of C4. None uses ontology releases or biomedical curator diffs.

### C. Gap-aware and query-time acquisition; incompleteness

**17. Generate-on-Graph (GoG)**
Xu et al., EMNLP 2024 (peer-reviewed). [ACL Anthology](https://aclanthology.org/2024.emnlp-main.1023) · [arXiv 2404.14741](https://arxiv.org/abs/2404.14741)
*Summary:* Incomplete-KGQA setting. The LLM explores the KG and *generates* missing triples from its own parametric knowledge.
- **C1 partial.** It reacts lazily, at query time, to missing triples. The gaps are not schema-certified, the facts come from LLM memory rather than literature, and nothing is persisted or verified.
- **C2 no.**
- **C3 no.**
- **C4 no.**

**18. RFM-RAG: Retrieval Feedback and Memory RAG**
Li et al., 2025, preprint. [arXiv 2508.17862](https://arxiv.org/abs/2508.17862)
*Summary:* A dynamic evidence pool. Queries describing the knowledge gaps are generated from question triples, and a feedback model judges completeness.
- **C1 partial.** Gaps are described in natural language and judged by a model, not defined by a TBox. They live per query and do not update the KB.
- **C2 no.**
- **C3 no.**
- **C4 no.**

**19. Evaluating KG-RAG Methods under Knowledge Incompleteness**
Zhou et al., 2025, IRISAI'25 workshop. [arXiv 2504.05163](https://arxiv.org/abs/2504.05163)
*Summary:* Removes triples from KGs and shows that KG-RAG accuracy is sensitive to incompleteness.
- **C1 partial, as motivation only.** It has no gap detection or acquisition.
- **C2 no.**
- **C3 no.**
- **C4 partial.** The incompleteness is synthetic deletion, not real drift.

**20. When Absence Is Evidence (CROWN-QA)**
Min et al., 2026, preprint. [arXiv 2608.04591](https://arxiv.org/abs/2608.04591)
*Summary:* LLMs over-close, answering "no" when evidence only partially covers the query and "unknown" would be correct.
- **C1 partial, conceptual.** This is the empirical case for why an *explicit* known-unknown certificate matters. It uses no ontology.
- **C2 no.**
- **C3 no.**
- **C4 no.**
- *Use:* cite it to justify having TinyLlama answer "unknown" on certified gaps.

### D. Reasoner-verified QA and repair of answers

**21. When Corrective Hints Hurt: Reasoner-Guided Repair of LLM Overcaution on Entailed Negations under OWL 2 DL**
Qi et al., 2026, accepted at ICAIDE 2026. [arXiv 2604.23398](https://arxiv.org/abs/2604.23398)
*Summary:* Reasoner verdicts used to repair LLM "unknown" answers on queries where the ontology entails "no".
- **C1 no.**
- **C2 partial.** It repairs *answers*, not KB assertions. It has no conflict sets and no weighting (abstract).
- **C3 no.**
- **C4 partial.** It is relevant to evaluating QA faithfulness against a reasoner.

**22. Ontology-Grounded, Reasoner-Verified Benchmarks for Evaluating LLM Reasoning in Scientific AI**
Vaidya et al., 2026, NeurIPS 2026 AIDaR workshop. [arXiv 2610.00682](https://arxiv.org/abs/2610.00682)
*Summary:* Generates multiple-choice questions from OWL 2 ontologies (including DOID). Distractors are verified to be wrong by reasoner entailment.
- **C1 no.**
- **C2 no.**
- **C3 no.**
- **C4 partial.** This is a method usable for *generating* verified QA, but over a single static release. It could be applied to a release diff to build the drift-QA set.

### E. Static ontology/KG RAG baselines

**23. OG-RAG: Ontology-Grounded RAG for LLMs**
Sharma, Kumar and Li, EMNLP 2025 (peer-reviewed). [ACL Anthology](https://aclanthology.org/2025.emnlp-main.1674/)
*Summary:* Ontology-anchored hypergraph retrieval that selects a minimal set of hyperedges as context.
- **C1 no.**
- **C2 no.**
- **C3 no.**
- **C4 partial.** It is a strong *static* ontology-RAG baseline for the drift-QA comparison.

**24. KG-RAG over SPOKE (Biomedical KG-optimized prompt generation)**
Soman et al., *Bioinformatics* 40(9), 2024 (peer-reviewed). [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11441322) · [ADS abstract](https://ui.adsabs.harvard.edu/abs/2024Bioin..40E.560S/abstract)
*Summary:* Biomedical KG-RAG with token-efficient context from SPOKE. Reports large gains for Llama-2.
- **C1 no.**
- **C2 no.**
- **C3 no.**
- **C4 partial.** It is the static biomedical KG-RAG baseline.

### F. Temporal holdout, lead time and curation benchmarks

**25. Continuous Knowledge Metabolism (CKM)**
Tao et al., 2026, ICML 2026 AI4Research workshop / preprint. [arXiv 2604.12243](https://arxiv.org/abs/2604.12243)
*Summary:* Sliding-window incremental knowledge state over the literature. Hypotheses are validated against papers published after the window.
- **C1 no.**
- **C2 no.**
- **C3 partial, the closest lead-time metric.** Validated hypotheses preceded their matching papers by a mean of 404 days (median 399). It covers machine learning only (50 topics), the targets are papers rather than curated releases, and the outputs are hypotheses, not ontology facts (abstract).
- **C4 no.**

**26. ForeSCITE: Learning Scientific Trajectories to Predict Future Biomedical Discoveries**
Chang et al., 2026, preprint. [arXiv 2610.38719](https://arxiv.org/abs/2610.38719)
*Summary:* Embedding-trajectory hypothesis generation over about 3M biomedical conclusions, with retrospective time-sliced evaluation.
- **C1 no.**
- **C2 no.**
- **C3 partial.** It is biomedical and time-sliced and measures "re-observation of entity pairs after the cutoff". It does not use a curated resource as truth, and the abstract reports no lead time.
- **C4 no.**

**27. HPOFiller and HPOLabeler (pre-2023 baseline)**
- HPOFiller: Liu et al., *Bioinformatics* 2021 ([repository PDF](https://repository.kulib.kyoto-u.ac.jp/dspace/bitstream/2433/275588/1/bioinformatics_btab224.pdf)).
- HPOLabeler: Liu et al., 2020 ([PDF](https://acris.aalto.fi/ws/portalfiles/portal/44930160/SCI_Liu_HPOLabeler_1_3_.pdf)).

*Summary:* Non-LLM prediction of protein–HPO associations, evaluated with **temporal validation on HPO annotation releases** in the style of CAFA.
- **C1 no.**
- **C2 no.**
- **C3 partial.** This establishes that release-based temporal validation on HPO is standard practice for *predictors*. It uses no literature extraction and no lead time.
- **C4 no.**
- *Read depth:* snippets only.

**28. GOFlowLLM: Curating miRNA literature with LLMs and flowcharts**
2025 bioRxiv, with a later PMC copy. [bioRxiv](https://www.biorxiv.org/content/10.1101/2025.10.07.680945.full.pdf) · [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12790822/)
*Summary:* LLM GO curation following curator flowcharts. It reproduces the existing curator GO term in 34 of 42 papers annotated from 2022 onward (snippet).
- **C1 no.**
- **C2 partial.** Constrained, flowchart-guided term selection, without a reasoner.
- **C3 partial.** It is scored against real curator annotations, but by comparison with existing annotations rather than forward in time, and with no lead time.
- **C4 no.**
- *Read depth:* snippets only.

**29. FlyAOC: Evaluating Agentic Ontology Curation of Drosophila Knowledge Bases**
Zhang et al., 2026, accepted at NeurIPS 2026 Datasets and Benchmarks. [arXiv 2602.09163](https://arxiv.org/abs/2602.09163)
*Summary:* Agents search a corpus of 16,898 papers to produce FlyBase-style GO, expression and synonym annotations, scored against 7,397 expert annotations.
- **C1 no.**
- **C2 no.**
- **C3 partial.** It is scored against curator truth, with no temporal split stated in the abstract.
- **C4 no.**
- *Positioning:* the closest *benchmark* framing for "agent vs curator".

**30. A systematic assessment of LLMs' knowledge of rare diseases**
*HGG Advances* 2025 (peer-reviewed). [Cell](https://www.cell.com/hgg-advances/fulltext/S2666-2477(25)00161-7) · [PubMed](https://pubmed.ncbi.nlm.nih.gov/41383021/)
*Summary:* LLM recall of HPOA and Orphanet gene and phenotype knowledge is low. It is better for genes than for phenotypes. Candidate novel disease–phenotype links are checked against PubMed.
- **C1 no.**
- **C2 no.**
- **C3 partial.** It uses HPOA as truth but from a single release (snippet). Release comparison could not be verified.
- **C4 no.**
- *Use:* motivation for why a small LLM needs an external, updated ontology.

**31. PubTator 3.0**
Wei et al., *NAR* 52(W1), 2024 (peer-reviewed). [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11223843) · [arXiv 2401.11048](https://arxiv.org/abs/2401.11048)
*Summary:* Weekly-updated entity and relation annotations (12 relation types, including gene–disease) over PubMed.
- **C1 no.**
- **C2 partial, as substrate.** It is a grounding and relation source, and a strong *non-LLM extraction baseline* for C3.
- **C3 no.**
- **C4 no.**

### Also seen (not scored; abstract or snippet only)
- **OntoLogX.** Ontology-guided KG extraction from logs with iterative correction. [arXiv 2510.01409](https://arxiv.org/abs/2510.01409)
- **LLM-driven SHACL violation repair.** [arXiv 2507.22419](https://arxiv.org/abs/2507.22419v1)
- **xpSHACL.** [arXiv 2507.08432](https://arxiv.org/abs/2507.08432v1)
- **OaK, dynamic ontology for agents.** [arXiv 2608.22974](https://arxiv.org/abs/2608.22974)
- **EvoOntology.** [arXiv 2609.15779](https://arxiv.org/abs/2609.15779)
- **OL-KGC.** [arXiv 2507.20643](https://arxiv.org/html/2507.20643v1)
- **PubMind.** LLM variant extraction normalized to MONDO and HPO. [Nat. Commun. 2026](https://www.nature.com/articles/s41467-026-76834-4)
- **AutoRD.** Rare-disease KG extraction. [JMIR Med Inform 2024](https://medinform.jmir.org/2024/1/e60665)
- **MAKES-QA.** User-guided KG enrichment from literature. [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0957417426010699)
- **LLMs in bio-ontology research, a review.** [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12649945/)
- **Belief-change survey linking AGM revision and DL ontology repair.** [arXiv 2608.14567](https://arxiv.org/pdf/2608.14567)

None of these changes the scoring above.

Not verified here, and worth a targeted check before submission:
- **LitVar 2.0.**
- **The Monarch/HPO curation tooling papers.** The 2024 HPO and Monarch NAR updates.
- **Pre-2023 "completeness statements" work for RDF/Wikidata.** This is the classic formal treatment of known unknowns and could be cited against C1.

---

## 3. Novelty statement

### Status of each contribution

**C1, schema-certified gaps: unclaimed in the form described.**
- No paper found uses the ontology's own TBox existential or min-cardinality axioms as completeness certificates that drive *both* a proactive sweep and lazy, query-triggered literature acquisition.
- Neighbours define gaps in other ways:
  - human competency questions (OntoExtend, [2607.17963](https://arxiv.org/abs/2607.17963));
  - per-query, LLM-judged gaps (GoG, [EMNLP 2024](https://aclanthology.org/2024.emnlp-main.1023); RFM-RAG, [2508.17862](https://arxiv.org/abs/2508.17862); AMG-RAG, [Findings EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.679/));
  - synthetic deletion only ([2504.05163](https://arxiv.org/abs/2504.05163)).

*Expected reviewer objection:* under OWL's open-world semantics, a missing filler for `Disease ⊑ ∃hasCausativeGene.Gene` is *not* an inconsistency, because the reasoner simply infers an anonymous gene. "Certified gap" is therefore an epistemic, closed-world reading of the axiom, essentially SHACL `sh:minCount` or a DL-K style query. Address this up front:
- State the semantics explicitly. The axiom entails that a filler exists, and the ABox lacks a *named* one. This makes the gap provably a known unknown, which is stronger than a missing triple.
- Cite the SHACL repair line ([2507.22419](https://arxiv.org/abs/2507.22419v1)).
- Argue that the novelty is using the entailed-but-unnamed filler as an acquisition target, plus the sweep/lazy policy. The detection mechanism itself is not the novelty.

**C2, reasoner-gated provenance-weighted updates: overlaps in parts, so claim the combination.**
- Existing pieces:
  - reasoner gating and repair loops on LLM output (Extended NeOn-GPT / [LLMs4Life](https://arxiv.org/pdf/2412.02035); [2601.01609](https://arxiv.org/abs/2601.01609); withdrawn [2504.07640](https://arxiv.org/abs/2504.07640));
  - ontology grounding (SPIRES, [2304.02711](https://arxiv.org/abs/2304.02711));
  - evidence-count and recency-based conflict handling without a reasoner (MedKGent, [2508.12393](https://arxiv.org/html/2508.12393v2); Graphiti, [2501.13956](https://arxiv.org/abs/2501.13956)).
- Not found anywhere:
  - minimal-conflict-set (kernel/MIS) repair whose removal choice is weighted by independent-PMID count, recency, and curated-vs-extracted provenance;
  - applied to LLM-extracted ABox facts.
- Position C2 as "belief-revision-style repair with evidence weights, replacing LLM-arbitrated conflict resolution (MedKGent) and LLM-generated repairs (NeOn-GPT)". [2601.01609 §2.5.2](https://arxiv.org/html/2601.01609) supplies a quotable "underexplored" statement.

*Practical risk:* plain HPO annotations carry few disjointness axioms. Show that HermiT actually fires on real conflicts, for example contradictory inheritance modes or HPOA `NOT` annotations. Otherwise reviewers will say the gate is vacuous.

**C3, back-testing against curator releases with lead time: the most novel, but qualify it.**
- Prior temporal designs, none of which matches C3:
  - DRAGON-AI uses post-Nov-2022 HP, MONDO and GO terms as a leakage-safe test set ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11484368/)).
  - The HPO annotation-prediction lineage uses temporal validation across HPO releases (HPOFiller, HPOLabeler).
  - PrimeKG-CL scores on real 2021→2023 snapshot diffs ([2605.10529](https://arxiv.org/abs/2605.10529)).
  - CKM defines a 404-day lead time against later papers ([2604.12243](https://arxiv.org/abs/2604.12243)).
- None does the following together:
  1. *literature-extraction-driven* ontology updates;
  2. restricted to PubMed publication dates before each release;
  3. scored against the *actual curator diff* of successive releases of a curated biomedical resource (adds, and ideally removals);
  4. with per-fact lead time computed from PMID dates against the release in which curators added the fact.
- Claim exactly this conjunction. Cite DRAGON-AI and HPOFiller as the temporal-holdout precedents, and CKM as the lead-time precedent.

*Validity risk to pre-empt (DRAGON-AI raises the same leakage concern):* Qwen3-8B's pretraining corpus very likely postdates T0 = 2023-06-06. Its extractions for 2023–2025 releases could therefore reflect memorised curator content rather than reading the abstract. Verify the cutoff in the Qwen3 technical report. Report a "no-abstract / parametric-only" control, and stratify results by release before vs after the model cutoff.

**C4, drift QA: partially claimed in the general domain, open for biomedical ontologies.**
- General-domain drift QA exists: EvoWiki ([2412.13582](https://arxiv.org/abs/2412.13582)), HoH ([2503.04800](https://arxiv.org/abs/2503.04800)), EvolvingQA ([2311.08106](https://arxiv.org/pdf/2311.08106)) and ECT-QA's base-then-update protocol ([2510.13590](https://arxiv.org/abs/2510.13590)).
- PrimeKG-CL has KGQA over biomedical snapshots, but for embedding models.
- No paper found compares static ontology-RAG with self-updating ontology-RAG on questions derived from the *release diff of a curated biomedical ontology*.
- C4 is the least novel on its own. Present it as the downstream consequence of C3, not a standalone claim.
- Use OG-RAG and KG-RAG/SPOKE as the static baselines. Consider the reasoner-verified generation of [2610.00682](https://arxiv.org/abs/2610.00682) to build diff-derived questions with verified distractors.

### Strongest single framing

> **"Can a self-updating ontology keep pace with its curators? Back-testing schema-driven, reasoner-gated literature updates against six real HPO releases."**

Lead with **C3** as the headline evaluation contribution. It is the one no neighbour has done, and it turns a crowded "LLM updates a KG" space into a falsifiable, curator-anchored measurement, including how many days before curators the system found each fact.

Present **C1** as the mechanism that makes acquisition *targeted* (and thus cheap enough for an 8B model). Present **C2** as the safety layer that keeps precision against curator truth high. Present **C4** as the user-facing payoff.

This framing makes DRAGON-AI, MedKGent, PrimeKG-CL and CKM explicit foils:
- DRAGON-AI: temporal holdout, but no literature updates or release diff.
- MedKGent: literature updates, but no curator back-test and no reasoner.
- PrimeKG-CL: release diffs, but no extraction.
- CKM: lead time, but not biomedical and not curated.
