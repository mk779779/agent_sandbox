## SLM AI Powered Search — Implementation-Ready High-Level Overview (Public Data)

### What we’re building

A lightweight **Query Understanding + Rewrite Service** for retail search that improves retrieval by:

- **Spell correction & normalization** (typos, spacing, casing, dash rules)
- **Model-number / product-ID understanding** (recognize and enrich “bare” model queries)
- **Query reification** (expand intent with safe, constrained additions like brand/model/category)
- **Conversational/NLU parsing** (extract constraints like size, voltage, color, category)

The system is designed to run **low-latency** with safe fallbacks, measurable relevance gains, and production-style monitoring—using **public datasets**.

---

# 1) System goals and non-goals

### Goals

- **Low latency** rewrite (target: p95 < 50ms CPU for gating + rules; p95 < 150ms for SLM path, adjustable to your hardware)
- **High precision on “rewrite needed”** decisions (avoid over-rewriting)
- **Constrained enrichment** (no hallucinated brand/model/category)
- **Search impact measured** with offline ranking metrics + rewrite harm metrics
- Full reproducibility: dataset build scripts + model configs + eval harness + serving benchmarks

### Non-goals (for v1)

- Full end-to-end ranking model replacement
- Perfect conversational agent (we only parse and rewrite queries)
- Reliance on proprietary click logs

---

# 2) Architecture (services and flow)

### 2.1 Online request flow (single API)

**Endpoint**: `POST /rewrite`

**Input**

```json
{
  "query": "xe50t06st45u1",
  "locale": "en-US",
  "context": { "category_hint": null }
}
```

**Output**

```json
{
  "original": "xe50t06st45u1",
  "rewrite": "rheem xe50t06st45u1",
  "rewrite_type": "BRAND_MODEL_ENRICH",
  "confidence": 0.93,
  "signals": {
    "model_number_detected": true,
    "brand_source": "catalog_lookup",
    "constraints": { "capacity_gal": null, "voltage": null }
  }
}
```

### 2.2 Internal pipeline stages

1. **Fast Normalizer** (always-on)
   - lowercasing, unicode normalization, whitespace/dash normalization

2. **Pattern Detectors** (fast rules)
   - model-number / SKU-like patterns (regex + heuristics)

3. **Catalog Resolver** (public “catalog table”)
   - maps model-like tokens → candidate products/brands (top-N)

4. **Gating Classifier (tiny)**
   - decides: `NONE | SPELL_ONLY | BRAND_MODEL_ENRICH | NLU_REWRITE`
   - provides calibrated confidence

5. **Rewrite Engine**
   - Route A: **Rules/Baseline** for simple spell-only (optional)
   - Route B: **SLM Generator** for rewrite

6. **Safety & Constraints**
   - enrichment allowed only if brand/model exists in catalog candidates
   - block category drift

7. **Response**

### Why this reads “Staff”

- Explicit routing, calibration, safety constraints, fallbacks, and measurable system outcomes.

---

# 3) Data plan (public-only)

### 3.1 Datasets (choose 1 primary + 1 optional)

**Primary (recommended for retail search relevance):**

- “Home Depot Product Search Relevance” style dataset: query ↔ product text ↔ relevance label.

**Optional scale/coverage:**

- Large public e-commerce metadata corpus (titles/brands/categories) for more model-number variety.

### 3.2 Build a unified “catalog table”

Create a denormalized product table:

- `product_id`
- `title`
- `brand`
- `model_number` (where available; if missing, infer from title patterns)
- `category`
- `attributes` (color, size, voltage, capacity, etc. if present)
- `description/bullets`

This replaces internal BigQuery joins with a reproducible script that outputs Parquet/JSONL.

---

# 4) Training data construction (public supervision + synthetic pairs)

We will train a rewrite model using **(noisy_query → canonical_query)** pairs.

### 4.1 Canonical target generation (“clean_text”)

For each product:

- canonical model query: `"brand model_number"` when model exists
- canonical semantic query: `"brand + key title tokens + key attributes"`
- canonical normalized query: standardized spacing/dash rules

### 4.2 Synthetic noise generation (“noisy_text”)

Generate variants that mimic real retail search:

- keyboard typos (insert/delete/substitute)
- OCR-like swaps
- missing delimiters: `xe50t06st45u1` vs `xe 50 t06 st45 u1`
- model-only queries (drop brand)
- partial queries (truncate prefixes/suffixes)

### 4.3 Label schema

Each example stores:

- `noisy_query`
- `target_rewrite`
- `rewrite_type`
- `catalog_candidates` (optional for constrained enrichment)
- `locale` (optional)

This enables both:

- **Gating classifier training** (type + confidence)
- **Seq2seq generator training** (rewrite text)

---

# 5) Models (v1 + v2)

### 5.1 Gating model (mandatory)

A small, fast classifier:

- Inputs: normalized query + simple features (length, digit ratio, dash pattern, candidate match scores)
- Outputs: rewrite_type + confidence
- Priority: very high precision (don’t rewrite unless confident)

**Deliverable:** calibrated model + threshold policy.

### 5.2 Rewrite generator (SLM)

**v1 (simpler, stable):** small seq2seq model (T5-class)

- Input: `query` (+ optional candidate brand/model tokens)
- Output: rewritten query

**v2 (optional upgrade):** Qwen2.5-small SFT + distillation

- Use teacher → student for quality + low latency

### 5.3 Constraint enforcement (required)

Even if the generator “wants” to add a brand:

- only allow additions that appear in **catalog candidate set**
- if no confident match → spell-only or no-rewrite

---

# 6) Evaluation plan (what “good” means)

### 6.1 Task metrics (rewrite correctness)

- rewrite decision: Precision/Recall/F1 for “should rewrite”
- type accuracy: correct route classification
- text similarity: exact match + edit distance / chrF
- **harm metrics**:
  - wrong-brand enrichment rate
  - category drift rate
  - over-rewrite rate (rewrote when canonical equals original)

### 6.2 Search relevance metrics (resume-critical)

Offline simulation using relevance labels:

- nDCG@K / MRR before vs after rewrite
- zero-results proxy (if you build a simple BM25/embedding retrieval)

### 6.3 Slice-based reporting

Report metrics separately for:

- model-number-heavy queries
- short vs long queries
- high digit ratio vs low
- head vs tail products (by frequency)

---

# 7) Serving & performance

### 7.1 Serving implementation

- Single containerized service (FastAPI or similar)
- Loads:
  - normalizer + rules
  - gating model
  - catalog index (in-memory hashmap / trie / embedding optional)
  - rewrite model (PyTorch or ONNX)

### 7.2 Latency strategy

- Cache hot queries (LRU)
- Route most traffic through fast path (NONE/SPELL_ONLY rules)
- Only invoke SLM on gated cases
- Export to ONNX and optionally quantize (INT8) for CPU efficiency

### 7.3 Reliability and fallback

- timeout on SLM path → return original query + `rewrite_type=NONE`
- model version pinning and rollback support in config

---

# 8) Observability and “production readiness”

Log structured events (no sensitive data in public project):

- rewrite rate by type
- confidence distributions
- top tokens causing enrich
- error buckets (timeouts, missing catalog match, safety blocks)

Monitoring outputs:

- dashboard charts (even simple notebook + JSON logs is fine)
- golden query regression tests (runs in CI)
- drift checks: token distribution, new/unknown model patterns

---

# 9) Phased delivery plan (implementation sequence)

### Phase 1 — Foundations (Catalog + Baselines)

- Build catalog table + query normalizer
- Implement model-number detector + brand/model dictionary lookup
- Establish baseline rewrite (rule-based)
- Deliver: dataset builder + baseline metrics + service skeleton

### Phase 2 — Gating model + Safety constraints

- Train gating classifier
- Implement calibration + thresholds
- Add constrained enrichment policy
- Deliver: gating model report + safety metrics

### Phase 3 — SLM v1 rewrite model

- Train small seq2seq rewrite model on synthetic pairs
- Integrate into service behind gating
- Deliver: before/after search metrics (offline)

### Phase 4 — Performance + ONNX + benchmarking

- ONNX export, quantization experiments
- Cache + batching (if needed)
- Deliver: latency table + cost/throughput estimates

### Phase 5 — Optional v2 (Qwen + distillation)

- Teacher rewrite generation and student distillation
- Compare vs v1 on quality/latency
- Deliver: final model selection doc

### Phase 6 — Ops polish + Resume packaging

- CI tests (golden queries), drift checks, dashboards
- Final design doc + model card + demo UI

---

# 10) Repo layout (ready for implementation handoff)

```
slm-search/
  data_pipeline/
    build_catalog.py
    build_training_pairs.py
  augmentation/
    noise_generators.py
  models/
    gating/
    train.py
    calibrate.py
    export_onnx.py
    rewrite/
    train_seq2seq.py
    distill.py
    export_onnx.py
  eval/
    task_metrics.py
    search_metrics.py
    slice_reports.py
  serving/
    app.py
    routing.py
    safety.py
    catalog_index.py
    benchmark.py
  docs/
    design.md
    model_card.md
    eval_report.md
```

---

If you tell me your target runtime (CPU-only laptop vs GPU), I’ll pick a concrete v1 model choice and set realistic latency targets + which phases to cut or expand—without changing the core design.
