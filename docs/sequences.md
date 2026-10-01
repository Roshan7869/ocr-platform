# Sequence diagrams — ocr-platform

Companion to `docs/architecture.md`. Lifelines map to modules in `docs/files/`.

---

## 1. R0 happy path (classified fixture, scanned 2-page)

```text
CLI extract.py    loader    renderer   manifest/reg   boundaries   engine/marks   normalize+vocab   rules+cross   policy    prov.validator   exports
     │              │          │            │             │             │               │               │           │              │             │
     │ --fixture    │          │            │             │             │               │               │           │              │             │
     │─────────────►│ verify   │            │             │             │               │               │           │              │             │
     │              │ hash+class            │             │             │               │               │           │              │             │
     │              │─────────►│ render     │             │             │               │               │           │              │             │
     │              │          │ DPI fixed  │             │             │               │               │           │              │             │
     │              │          │───────────►│ load+verify │             │               │               │           │              │             │
     │              │          │            │ child hashes│             │               │               │           │              │             │
     │              │          │            │ identity+   │             │               │               │           │              │             │
     │              │          │            │ normalize   │             │               │               │           │              │             │
     │              │          │            │────────────►│ regions+    │               │               │           │              │             │
     │              │          │            │             │ INTERSECT   │               │               │           │              │             │
     │              │          │            │             │────────────►│ det+rec +     │               │           │              │             │
     │              │          │            │             │             │ marks → evidence               │           │              │             │
     │              │          │            │             │             │──────────────►│ profiles+codes│           │              │             │
     │              │          │            │             │             │               │──────────────►│ checks    │              │             │
     │              │          │            │             │             │               │               │──────────►│ disposition  │              │
     │              │          │            │             │             │               │               │           │─────────────►│ pass?        │
     │              │          │            │             │             │               │               │           │              │──► accepted  │
     │              │          │            │             │             │               │               │           │              │    + review  │
     │◄─────────────┴──────────┴────────────┴─────────────┴─────────────┴───────────────┴───────────────┴───────────┴──────────────┴──────────────┘
     │ writes result.json + review_candidates.json; prints run_id, counts
```

Notes:
- Order fixed in `pipeline.py`; no stage skips provenance attachment.
- R0: `ocr_auto_accept_enabled=false` → OCR-only present fields typically **review** until spike+calibration (`docs/accuracy-plan.md`).

---

## 2. Encrypted / corrupt / empty PDF

```text
CLI → loader(hash ok) → renderer/classifier
                              │
                              ├─ encrypted ─► DocumentRun.disposition=errored reason=ENCRYPTED_PDF
                              ├─ corrupt   ─► errored reason=CORRUPT_PDF
                              └─ empty     ─► page errored/review; zero field decisions
CLI ◄── exit code per extract.py contract (usage/provenance/spike codes)
```

Invariant: terminal document error **before** any FieldDecision exists (`schemas/job.py`, `state_machine.py`).

---

## 3. Registration invalid → no accepted fields

```text
renderer → registration
              │
              ├─ mode=identity (R0)
              │    sanity (LEGEND/ANCHOR) fail OR residual > threshold [R0.5 affine]
              │         │
              │         ▼
              │    RegistrationTransform recorded invalid
              │    state_machine: page review (e.g. REGISTRATION_RESIDUAL_HIGH)
              │    boundaries: signals only; policy: block field accept on page
              │
              ├─ mode=affine (R0.5, ADR-002)
              │    structure anchors → residual > threshold OR ambiguous anchors
              │         │
              │         ▼
              │    RegistrationTransform recorded invalid → page review
              │    (never silently accepts; R0 has no affine — identity only)
              │
              └─ (R3+ reserved: further enhanced registration)
```

Measured need: layout-ref pixel correlation across series is weak (≈0.14–0.79); corpus vs base often <0.45 — identity alone will thrash outside aligned refs (`docs/accuracy-plan.md`).

---

## 4. Provenance violation blocks export

```text
policy marks field accepted
       │
       ▼
provenance.validator walk: decision → EvidenceSet → page → manifest hash → render/reg
       │
       ├─ ok ─► export allowed
       │
       └─ violation (missing node, bad hash, wrong evidence type for value_state)
                │
                ▼
         demote disposition → review/exception (NOT accepted)
         export must NOT emit value as accepted
         test gate: zero accepted with incomplete provenance
```

---

## 5. Handwriting-suspected text field (R0 posture)

```text
engine OCR crop in FIELD region
   → normalizer profile
   → handwriting signal? (ink/stroke heuristic or low print-model conf) [R0.5+]
        │
        ├─ no  → policy as usual (still gated by ocr_auto_accept flag)
        └─ yes → force review-only until dedicated rec path (R2+) or human
                 reason codes include handwriting/low-trust path
                 never print-model auto-accept on pen strokes
```

---

## 6. R1 async API (thin slice — designed, not built in R0)

```text
Client          API                 ObjectStore     Queue          GPU Worker              DB/Files
  │ POST /v1/extractions             │               │               │                      │
  │────────────────►│ store PDF       │               │               │                      │
  │                 │────────────────►│               │               │                      │
  │                 │ enqueue job(run_id)             │               │                      │
  │                 │────────────────────────────────►│               │                      │
  │◄── 202 job_id   │               │               │               │                      │
  │ GET status      │               │               │ pull          │                      │
  │────────────────►│               │               │──────────────►│ extract (R0 pipeline)│
  │                 │               │               │               │──────────────────────►│ JSON+crops+prov
  │◄── running/done │◄────────────────────────────── status webhook/poll                     │
  │ GET result      │               │               │               │                      │
  │────────────────►│───────────────┴───────────────┴───────────────┴──────────────────────►│
```

- `run_id = (document_content_hash, configuration_fingerprint)` — idempotent retries.
- Review payload URL points at R2 console or downloadable review JSON (R1).

---

## 7. R2 human correction (designed ahead)

```text
review candidate (crop + reasons)
   → reviewer action
   → HumanCorrectionEvidence + DecisionRevision (never overwrite raw OCR)
   → provenance validator accepts HumanCorrectionEvidence for corrected values
   → re-export; audit trail retains original OcrObservation
```

---

## 8. Spike gate (before model pins)

```text
run_spike.py
  → resolve Python/paddle/CUDA/rasterizer versions
  → load classified 2-page fixture via loader
  → det+rec (real, not mock) on CPU (and GPU if present)
  → repeated-run compare under canonical JSON policy
  → write matrix JSON+MD; exit 0 go / 1 no-go
  → on go: fill models.py pins + optional Dockerfile pin block
  → on no-go: design result (documented), no silent unpinned fallback
```
