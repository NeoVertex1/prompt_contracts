# Prompt Contracts



# Prompt Contract v4.0 — Algorithmic Reasoning Framework

A lightweight, model-agnostic framework that turns open-ended LLMs into **deterministic, auditable services**. It does this by (1) declaring the agent’s identity and rules, (2) enforcing a multi-stage reasoning pipeline, and (3) requiring a **typed JSON output** (“HOLODATA”) with evidence, scores, and verification telemetry.

---

#### See the full prompt contract here:

[link to full contract V4](https://github.com/NeoVertex1/prompt_contracts/blob/main/universal_v4_contract.xml)



## Why this exists

LLMs are powerful but fuzzy. This contract pins them down:

* **Deterministic procedure:** ANALYZE → GATHER → REASON → DRAFT → VERIFY → REFINE → OUTPUT
* **Typed output (ABI):** a strict JSON schema your code can parse, store, and inspect
* **Quality gates:** explicit checks for evidence coverage, scope alignment, number sourcing, and contradictions

Use it when you need **grounded answers, reproducibility, and logging** (e.g., “chat-to-PDF”, policy Q&A, specs, legal/finance summaries).

---

## Core concepts

### 1) `<prompt_metadata> … </prompt_metadata>`

A short header that sets the assistant’s **role, goals, constraints, and thinking style**.

* **Type** — who the model is (e.g., “Document Analysis Agent”).
* **Purpose** — what to optimize (evidence-based answers).
* **Paradigm** — reasoning style (multi-stage, algorithmic).
* **Constraints** — hard rules (accuracy, transparency, completeness, verifiability).
* **Objective** — the success metric (verified, comprehensive answers with confidence).
* **Processing_Philosophy** — the exact pipeline to follow.

> Think of this as the model’s `init()`—it reduces drift and anchors behavior.

### 2) The Prompt Contract

Everything after the metadata that **binds the model to a procedure and an output shape**:

* **Stages** with precise instructions (ANALYZE/GATHER/REASON/DRAFT/VERIFY/REFINE/OUTPUT)
* **Guardrails** (anti-parrot, scope control, ambiguity/contradiction checks)
* **Verification gate** that yields a `verification_score`
* **Refinement loop** with a hard iteration cap

### 3) HOLODATA: the Output ABI

A strict JSON schema the model must produce. It enables **structured logging, dashboards, and automated QA**.

Key fields:

* `answer` — human-readable result with inline indicators (certainty, completeness)
* `evidence[]` — page-anchored quotes with `quality`, `type`, and `relevance_score`
* `completeness` (0–1), `certainty` (high/medium/low), `certainty_score` (0–1), `status`
* `scope{…}` — how closely the answer matches the question (exact/broader/narrower/shifted)
* `contradictions[]`, `inference_chain[]`, `numerical_metadata[]`, `cross_references[]`, `ambiguity{…}`
* `processing_metadata{ mode, stages_executed, verification_score, refinement_iterations }`

> Treat HOLODATA like an API response contract (ABI). If it validates, you can trust and store it.

---

## The stage flow (at a glance)

1. **ANALYZE `<think>`** — classify the question, pick a processing mode (e.g., `quantitative_aggregate` vs `simple_factual`).
2. **GATHER `<expand>`** — scan pages, score relevance, extract quotes, label evidence quality/type, pre-flag contradictions/cross-refs/ambiguities.
3. **REASON `<think>`** — synthesize or compute; record steps in `inference_chain`.
4. **DRAFT** — produce an initial answer; compute completeness & certainty; show math if any.
5. **VERIFY `<verify>`** — hard checks (page validity, claim→evidence mapping, number sourcing, scope alignment, etc.) => `verification_score`.
6. **REFINE `<loop max_iterations="N">`** — fix only what failed; re-verify; stop when passing or when out of iterations.
7. **OUTPUT** — emit **HOLODATA-compliant JSON** (and nothing else).

---

## The angle-bracket tags

These are text delimiters that most LLMs treat as **phase boundaries**:

* `<prompt_metadata>…</prompt_metadata>` — identity + policy header
* `<think>…</think>` — internal reasoning protocol (not user-visible)
* `<expand>…</expand>` — evidence collection protocol
* `<verify>…</verify>` — QA rubric and scoring
* `<loop max_iterations="2">…</loop>` — bounded refinement

They don’t require a special parser; they’re reliable cues that reduce phase contamination.

---

## HOLODATA schema (excerpt)

```json
{
  "answer": "string",
  "evidence": [
    {
      "quote": "string",
      "page": "number",
      "quality": "direct|inferred|indirect",
      "type": "explicit_statement|numerical_data|contextual_interpretation|cross_reference",
      "relevance_score": "number 0-1"
    }
  ],
  "completeness": "number 0-1",
  "certainty": "high|medium|low",
  "certainty_score": "number 0-1",
  "status": "complete|partial|not_found",
  "reasoning": "string",
  "scope": {
    "question_asked": "string",
    "answer_provided": "string",
    "alignment": "exact|broader|narrower|shifted",
    "similarity_score": "number 0-1",
    "entity_overlap": "number 0-1",
    "note": "string"
  },
  "contradictions": [],
  "inference_chain": [],
  "numerical_metadata": [],
  "cross_references": [],
  "ambiguity": {},
  "suggestions": [],
  "processing_metadata": {
    "mode": "string",
    "stages_executed": [],
    "verification_score": "number 0-1",
    "refinement_iterations": "number"
  }
}
```

---

## Minimal usage pattern (pseudo-flow)

1. **Assemble prompt**

   * Insert `<prompt_metadata>` with your role/purpose/constraints.
   * Paste the full contract (stages, guardrails, verification, loop).
   * Provide the HOLODATA schema (as the required output).
   * Attach your question and the document slice (or retrieval results).

2. **Call your LLM**

   * Temperature/decoding are up to you; the contract is model-agnostic.

3. **Validate output**

   * Parse JSON.
   * Enforce required fields and types.
   * Reject/flag if it’s not valid HOLODATA.

4. **Log & display**

   * Show only `answer` (plus inline indicators) to end users.
   * Store the full HOLODATA for dev dashboards and audits.

---

## Guardrails that matter

* **Anti-Parrot:** never copy >30 consecutive words; prefer short quotes for numbers/terms.
* **Scope Control:** detect and label broader/narrower/shifted answers.
* **Numbers Must Source:** every number must be quoted or computed with a clear step.
* **Contradiction/Ambiguity:** detect, record, and lower certainty accordingly.
* **Verification Gate:** only “pass” when `verification_score` ≥ threshold.

---

## What this enables

* **Evidence-first UX:** page-anchored claims and visible calculations
* **Auditable decisions:** inference chains, contradictions, and verification telemetry
* **Ops visibility:** `processing_metadata` for performance, cost, and failure analysis
* **Easy integration:** HOLODATA is a clean, typed interface for any backend/store

---

## Notes & scope

* This README explains the framework; it **does not** prescribe a runtime, SDK, or deployment path.
* The contract is **domain-agnostic**; it works for budgets, legal, specs, research, and more.
* Tweak the metadata and stage prompts to match your use case (e.g., “Talk-to-PDF Concierge”).

---

## FAQ

**Q: Do the tags require special model support?**
A: No. They’re plain text delimiters that reliably prime most LLMs to treat sections differently.

**Q: Do I have to show chain-of-thought to users?**
A: No. The contract controls *how to think*, not *what to reveal*. You typically show only `answer` and keep HOLODATA for logs.

**Q: What if the model returns non-JSON text?**
A: Validate and reject. The contract expects strict HOLODATA. Send a short repair prompt or re-run with a “return only JSON” wrapper.

---

If you want, I can tailor a **mini version** of this contract for your repo (tightened wording, reduced fields, and a test fixture that validates HOLODATA objects).
