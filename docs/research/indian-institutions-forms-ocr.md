# Indian Research Landscape for Large-Scale Hindi Document & Form OCR (PDF image reading)

Aggressive research sweep for reading scanned fax/form PDF images (WARD-42 corpus: 1,446 CCITT raster PDFs, no text layer).
Focus: Indian institutions, journals, papers, government projects, datasets, and runnable GitHub/HuggingFace code that directly apply to
**Hindi handwritten/printed forms at scale**.

Compiled from live sources (CVIT/ILOCR, AI4Bharat, Bhashini/MeitY, IIT Delhi, journals) — October 2026.

---

## TIER 1 — DIRECTLY ON TASK (Hindi forms + scanned PDFs)

### 1. FormLens + Form6000 — CVIT, IIIT Hyderabad (ILOCR) ★ BEST MATCH
- **What:** End-to-end handwritten *form* digitization. Image in → structured key-value pairs out. No region detection, no rule-based post-processing needed.
- **Perf:** WRR 95.44% / CRR 98.33% / F1 **94.71%** — beats Google Form Parser (F1 89.67) and Azure Form Recognizer (F1 91.85).
- **Base:** GOT-OCR 2.0 adapted via MS-SWIFT LoRA. Multilingual (Hindi supported).
- **Dataset Form6000:** 6,000 images — 50 form templates, 650 writers, 650 scanned + 5,350 mobile captures (7-10 per form).
- **Code:** https://github.com/shaoncvit/FormLens  ·  Project: https://formlens.github.io/
- **Preprocessing included:** rotation, Gaussian/salt-pepper noise, perspective transform, motion blur, brightness/contrast — exactly the augmentation your degraded fax images need.
- **Paper:** "From Ink to Insight" ICVGIP 2025 (Bhattacharya, Mondal, Jawahar).
- **Fit to WARD-42:** 5/5. This is the closest published system to your task. Template-based structured extraction, Hindi handwriting, mobile/degraded robustness.

### 2. Towards Digitizing Filled Indic Handwritten Forms — CVIT (the template-alignment paper)
- **What:** Pipeline that aligns a *filled* form to an empty *template*, extracts printed vs handwritten ROIs, OCRs each region, field-specific post-processing.
- **Method:** align filled form to annotated empty template → detect handwritten regions → Bhashini OCR on ROIs → post-OCR for name/state/gender fields.
- **Dataset IIIT-Indic-Form-Test:** 3,700 forms (1,200 Hindi from 40 writers, 2,500 Bengali), each duplicated with rotations → structural + rotational variations. Manually annotated.
- **Code:** https://github.com/shaoncvit/Indic_Handwritten_Form_dataset
- **Paper:** CVIP 2024 (Bhattacharyya, Mondal, Jawahar).
- **Fit:** 5/5. WARD-42 is template-fixed fax forms — this exact "align to template" strategy is proven for the same use case.

### 3. MCP Card OCR — IIT Delhi (Chetan Arora, Aaditeshwar Seth) ★ PRODUCTION-PROVEN
- **What:** Automated digitization of Mother & Child Protection vaccination cards from smartphone photos — **standardized template forms**, real field deployment (Gram Vaani / Tika Vaani, Gates Foundation).
- **Method:** register card to standard template → **global-then-local homography** alignment (fixes curvature/torn edges) → ROI extraction → attention-based seq2seq date recognizer → confidence-scored selection.
- **Perf:** **98.73% character accuracy** vs Google Cloud Vision 75.02% and Azure OCR 79.26%. End-to-end 93% → 98% with low-confidence human review.
- **Paper:** ACM J. Computing & Sustainable Societies (JCSS) 2023. PDF: https://www.cse.iitd.ac.in/~aseth/ocr-mcp.pdf
- **Fit:** 5/5 for structured government forms. The global-local homography + template registration is directly reusable for skewed/fax-distorted WARD-42 forms. Confirms human-in-the-loop on low-confidence crops only.

### 4. IndicOCR — AI4Bharat (IIT Madras) + Bodhan AI ★ PRODUCTION / DOWNLOADABLE
- **What:** State-of-the-art document parser built specifically for *messy Indian documents* — handwritten notebooks, degraded 1905 newspaper clippings, hand-drawn tables, cursive. 22 Indian languages, printed + handwritten.
- **Arch:** two-stage — **IndicDocLayout** (PP-DocLayoutV3/RT-DETR, 33M) detects + orders blocks; **IndicBlockOCR** (Qwen3.5-0.8B, Sarvam-30B tokenizer) transcribes. Page in → reading-ordered Markdown out, tables as HTML/Markdown.
- **Scale:** 0.8B params, trained on 15M+ documents; competitive with 4-5x larger models on OmniDocBench + olmOCR-bench.
- **Handwriting:** English + 12 Indic langs incl. Hindi (still improving across styles).
- **Code/weights:** https://huggingface.co/bodhan-ai/indic-ocr  ·  Bhashini API: `bhashini/bodhan/indic-doc/ocr`
- **Fit:** 5/5 as a drop-in full-page engine to benchmark against your pipeline. Handles layout + tables + reading order out of the box.

---

## TIER 2 — CORE MODELS & CODE (reusable components)

### 5. IndicPage-OCR — CVIT, DAS 2026 (Springer LNCS)
- **What:** Parameter-efficient *page-level* handwritten recognition for Hindi, Bengali, Tamil, Telugu. Freezes vision encoder, adapts only Qwen-0.5B decoder with LoRA. Progressive word→line→page training.
- **Code/page:** https://indicpageocr.github.io/
- **Fit:** 4/5 — page-level HTR if you move beyond isolated crops.

### 6. HindiOCR-VLM — CVIT (GOT-OCR 2.0 + LoRA)
- **What:** VLM for Hindi OCR, LoRA on a Chinese/English-pretrained GOT-OCR 2.0. Single-stage (printed page-level) + two-stage (printed/handwritten/scene) modes. CRAFT detection for print/scene, YOLO for handwritten.
- **Perf:** outperforms domain-specific + industry models on printed & handwritten.
- **Repo:** https://github.com/HindiOCR-VLM/HindiOCR-VLM.github.io (local clone exists at ~/HindiOCR-VLM.github.io)
- **Fit:** 4/5.

### 7. Indic-HTR-CVIP-2024 — PARSeq (Lalitha Evani) ★ SOTA Hindi handwriting
- **What:** Permuted Autoregressive Sequence Model for 10 Indic languages incl. Hindi. **SOTA per-language.** Studies printed→handwritten transfer learning.
- **Code/models:** https://github.com/LalithaEvani/Indic-HTR-CVIP-2024
- **Fit:** 5/5 for the recognition core — SOTA Hindi handwritten word recognizer to benchmark/swap into your engine.

### 8. RoundTripOCR — post-OCR error correction (harshvivek14)
- **What:** Synthetically generates OCR-noise correction data via render-and-OCR round trip, then treats correction as MT. Releases **3.1M Hindi** sentence pairs (also Marathi/Bodo/Nepali/Konkani/Sanskrit).
- **Code/data:** https://github.com/harshvivek14/RoundTripOCR
- **Fit:** 5/5 for a post-OCR cleanup layer on noisy fax output.

### 9. Devanagari OCR-VLM Benchmark — Aditya-PS-05
- **What:** Benchmarks 10 systems (EasyOCR, Qwen2.5-VL-3B, Qwen3-VL-8B, olmOCR-7B, DeepSeek-OCR, Gemini 2.5 Flash, Claude, GPT-5.5, Mistral) on Hindi across 4 synthetic degradations + 300 real scans. Script-aware eval (NFC, CER/WER/chrF++). Byte-level ByT5 post-corrector (+1.2 to +1.5 chrF++ on matched engine; does NOT transfer across engines).
- **Code:** https://github.com/Aditya-PS-05/devanagari-ocr-benchmark
- **Key finding:** OCR strength on English does NOT predict Indic quality (76-point spread on real scans). Post-correction must be distribution-matched to your engine.
- **Fit:** 4/5 — use its degradation protocol + eval harness directly.

### 10. VeriBhoomi AI — enterprise Indian land-record digitization
- **What:** Production stack for scanned Indian govt records — RapidOCR (printed) + TrOCR (handwritten annotations) + Tesseract Devanagari, PostGIS analytics, confidence scoring, SHA-256 audit trails.
- **Code:** https://github.com/rajatsurana19/veribhoomi-ai
- **Fit:** 4/5 — reference architecture for a production OCR+validation pipeline on Indian forms.

---

## TIER 3 — GOVERNMENT / NATIONAL INFRASTRUCTURE

### 11. Bhashini / NLTM (MeitY) — National Language Translation Mission
- **What:** Government of India mission. 1000+ pre-trained models, OCR as a hosted service. Consortium: IIIT-H, IIT Delhi, IIT Jodhpur, IIT Bombay, CDAC Noida, Punjabi University Patiala.
- **OCR APIs:** `bhashini/iiith-bhasha-ocr` (printed, 20+ langs), OCR (handwritten), OCR (scene text), `bhashini/bodhan/indic-doc/ocr`.
- **Use-case precedent:** Hindi OCR for Lok Sabha Parliament debates — 10-15 lakh (1-1.5M) scanned pages. CDAC Noida front-end + IIIT-H Hindi OCR.
- **Hackathon:** AksharDrishti OCR Hackathon 2026 (document digitization, bhashini.gov.in).
- **Access:** developer portal — request API key (Udyat/Bhashini onboarding).
- **Fit:** 3/5 — hosted API option; consortium papers are gold for methodology.

### 12. AIKosh / IndiaAI — dataset repository
- Datasets + models from Bhashini partners, publicly downloadable. OCR training corpora (e.g. 14K labelled font/scan samples).
- https://aikosh.indiaai.gov.in

---

## TIER 4 — KEY DATASETS (Hindi, for benchmarking/fine-tuning)

| Dataset | Size | Type | Source | Fit |
|---|---|---|---|---|
| **Form6000** (FormLens) | 6,000 forms, 650 writers, 50 templates | Handwritten forms | github.com/shaoncvit/FormLens | 5/5 |
| **IIIT-Indic-Form-Test** | 3,700 forms (1,200 Hindi) | Filled forms + rotations | github.com/shaoncvit/Indic_Handwritten_Form_dataset | 5/5 |
| **IIIT-INDIC-HW-WORDS-Hindi** | 95,431 words (12 writers) | Handwritten words, 600 DPI | ilocr.iiit.ac.in/dataset/18/ · HF c3rl | 5/5 (crop benchmark) |
| **DohaScript** | 531 writers, 47,259 words | Page-level continuous Hindi HW | arXiv 2602.18089 · github.com/KAS4453/DohaScript | 3/5 |
| **AnciDev** | 3,000 lines / 500 pages | Historical manuscripts | aclanthology 2025.bhasha-1.8 · github.com/vriti2003/AnciDev | 2/5 |
| **Mozhi** | 1.2M words, 13 langs | Printed word/line | cvit.iiit.ac.in/usodi/tdocrmil.php | 3/5 |
| **IIIT-Indic-HW-UC** | Unconstrained camera-captured | Handwritten docs | ICPR 2024 (Mondal, Jawahar) | 3/5 |
| **Devanagari-OCR-ICL-Benchmark** | 20,000 sentences (Hindi+Marathi) | Post-OCR correction | HF AbhishekBhandari | 4/5 |
| **UCI DHCD** | 92,000 chars/digits | Character-level | UCI archive | 3/5 |
| **CPAR-2012** | ~35K digits + pangrams | Handwritten, demographics | figshare / pip cpar | 3/5 |

---

## TIER 5 — RESEARCH GROUPS TO FOLLOW / CONTACT

| Group | Lead | Relevance |
|---|---|---|
| **CVIT / ILOCR, IIIT Hyderabad** | C.V. Jawahar, Ajoy Mondal | THE Indic-OCR + form-digitization hub. All Tier-1 papers originate here. ilocr.iiit.ac.in |
| **AI4Bharat, IIT Madras** | Mitesh Khapra (+ Bodhan AI) | IndicOCR production parser. ai4bharat.iitm.ac.in |
| **IIT Delhi (CSE)** | Chetan Arora, Aaditeshwar Seth | Field-deployed form/card OCR. web.iitd.ac.in/~chetan |
| **ISI Kolkata** | Umapada Pal, B.B. Chaudhuri | Devanagari OCR surveys, character recognition |
| **Punjabi University Patiala** | Gurpreet Singh Lehal | Devanagari OCR survey (IJRES 2025), Bhashini partner |
| **NIT Jaipur (CVIP)** | — | Devanagari handwritten datasets (CVIP 2019) |

---

## KEY JOURNALS / VENUES (where this work is published)
- **IJDAR** (Int'l J. Document Analysis & Recognition, Springer) — primary venue.
- **ICDAR** (Int'l Conf. Document Analysis & Recognition) — annual competitions + papers.
- **DAS** (Document Analysis Systems workshop, IAPR) — IndicPage-OCR 2026.
- **CVIP / ICVGIP** (Indian Conf. Vision, Graphics & Image Processing) — FormLens, SemiHastakshar.
- **ICFHR** (Int'l Conf. Frontiers in Handwriting Recognition).
- **ACM JCSS** (Computing & Sustainable Societies) — MCP card paper (social-impact OCR).
- **WACV, Nature Scientific Reports, Sadhana (IAS)** — recognition + augmentation studies.

---

## SYNTHESIS — RECOMMENDED STACK FOR WARD-42

Reading 1,446 template-fixed Hindi fax PDFs (raster, degraded):

1. **Baseline fast path:** rapidocr (~7.6s/pg CPU) to get a floor number.
2. **Best single model to try first:** **FormLens** (github.com/shaoncvit/FormLens) — end-to-end Hindi form KV extraction, F1 94.7, already tuned for degraded handwriting. Its augmentation recipe maps onto fax noise.
3. **Template-alignment boost:** adopt the **IIIT-Indic-Form-Test** "align to empty template" approach — WARD-42 is one fixed template, so annotate ROIs once and reuse across all 1,446 pages. This alone typically beats naive full-page OCR on structured forms.
4. **Full-page fallback / tables:** **IndicOCR** (HF bodhan-ai/indic-ocr) for layout + reading order + table structure.
5. **Recognition core benchmark:** compare **Indic-HTR-CVIP-2024** (PARSeq) vs **HindiOCR-VLM** vs **IndicPage-OCR** on the IIIT-INDIC-HW-WORDS-Hindi test split to pick the best crop recognizer.
6. **Post-OCR cleanup:** **RoundTripOCR** (3.1M Hindi pairs) or a ByT5 corrector — but per the Devanagari benchmark, match the corrector to your engine's error distribution or it won't help.
7. **Human-in-the-loop:** follow the MCP-card pattern — auto-accept high-confidence crops, route only low-confidence ones to review (98%+ achievable).
8. **Eval protocol:** jiwer with Unicode NFC normalization; report CER (primary, since Devanagari is an abugida — one matra error flips meaning), median CER, and catastrophic rate (CER>50%).

---

## IMMEDIATE ACTIONABLE LINKS (verified live)
- github.com/shaoncvit/FormLens — form digitization (CLONE THIS)
- github.com/shaoncvit/Indic_Handwritten_Form_dataset — template alignment + IIIT-Indic-Form-Test
- huggingface.co/bodhan-ai/indic-ocr — production Indic parser weights
- github.com/LalithaEvani/Indic-HTR-CVIP-2024 — SOTA Hindi HTR
- indicpageocr.github.io — page-level LoRA OCR
- github.com/harshvivek14/RoundTripOCR — post-OCR correction (3.1M Hindi)
- github.com/Aditya-PS-05/devanagari-ocr-benchmark — 10-system benchmark + eval protocol
- ilocr.iiit.ac.in/publication/ — full ILOCR paper index
- ilocr.iiit.ac.in/dataset/18/ — IIIT-INDIC-HW-WORDS-Hindi download
