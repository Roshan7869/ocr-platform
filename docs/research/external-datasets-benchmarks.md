# External datasets, benchmarks, and evaluation harnesses for OCR engine selection

Research for benchmarking OCR engines on handwritten Devanagari survey forms (WARD-42 fax corpus).
Maps candidate resources onto the existing crop/transcription CER/WER protocol in `docs/benchmark.md`.
Benchmark-fit score is relative to "isolated handwritten answer-crop recognition" (our pilot's core task): 5 = drop-in, 1 = context only.

---

## 1. Handwritten Devanagari word datasets (drop-in for crop-level CER/WER)

### IIIT-INDIC-HW-WORDS — Hindi subset
- URL (canonical): https://cvit.iiit.ac.in/research/projects/cvit-projects/iiit-indic-hw-words
- URL (HF, parquet, easiest): https://huggingface.co/datasets/c3rl/IIIT-INDIC-HW-WORDS-Hindi
- URL (ILOCR platform, official zips + license): https://ilocr.iiit.ac.in/dataset/18/
- Size: 95,431 word images — train 69,853 / val 12,708 / test 12,870; 11,030 unique train words; 12 writers.
- Coverage: Devanagari (Hindi). Includes Devanagari digits, hyphenated words, English-transliterated words.
- License: CC BY 4.0 (per ILOCR dataset page `data_license.doc`). HF mirror is a community repackage — cite original.
- Download: HF `datasets` library / `huggingface-cli download c3rl/IIIT-INDIC-HW-WORDS-Hindi`; or per-split `train.zip/val.zip/test.zip` from CVIT/ILOCR with tab-separated `*_gt.txt` ground truth.
- Fit to our task: **5/5.** Ground-truth transcripts of isolated handwritten words = exactly the answer-crop task. Writers use boxes + pens at 600 DPI (fax forms are lower DPI but same domain). Establishes a public reference CER/WER baseline for Tesseract `hin` vs Doc AI vs local VLM.
- Note: this Hindi subset was originally released as **IIIT-HW-Dev** (1.8 GB, 95K words). The full IIIT-INDIC-HW-WORDS is ~868K–1.08M word instances across 10 scripts (Bengali, Gujarati, Gurmukhi, Kannada, Odia, Malayalam, Tamil, Urdu + Devanagari, Telugu).

### IIIT-INDIC-HW-WORDS — other scripts (HF mirror, c3rl)
- URL: https://huggingface.co/datasets/c3rl/IIIT-INDIC-HW-WORDS-Tamil (and sibling per-script repos)
- Use: only relevant if WARD-42 corpus expands beyond Hindi. Same protocol.

### DohaScript
- URL: https://huggingface.co/datasets/SIR-Lab/DohaScript (200-page public sample); full 531 pages via Google Drive (arxiv 2602.18089).
- Size: 531 handwritten pages, 531 unique writers, 47,259 word instances; 89 words/page controlled corpus.
- Coverage: Hindi (Devanagari), page-level continuous text.
- License: research/educational; consent-collected.
- Fit: **3/5.** Page-level and controlled lexicon — less like a free-form survey answer. Useful as a writer-diversity stress set and for fine-tuning, not as a direct crop benchmark.

### PLATTER / page-level Indic HTR (arxiv 2502.06172)
- URL: https://arxiv.org/html/2502.06172v1
- Use: builds page-level benchmark *from* IIIT-INDIC-HW-WORDS; gives CRNN/MASTER/ViTSTR/PARSeq isolated CRR/WRR numbers to compare our engines against published SOTA.

### AnciDev
- URL: https://aclanthology.org/2025.bhasha-1.8.pdf
- Size: 3,000 transcribed lines / 500 manuscript pages. Historical Sanskrit/Hindi manuscripts.
- Fit: **2/5.** Domain mismatch (ancient manuscripts). Only for robustness/transfer studies.

---

## 2. MNIST-style character/digit equivalents (numeric-field sanity checks)

### UCI Devanagari Handwritten Character Dataset (DHCD)
- URL: https://archive.ics.uci.edu/dataset/314/Devanagari+Handwritten+Character+Dataset
- Size: 92,000 images, 46 classes (36 consonants + 10 digits), 32×32 grayscale, ~2,000/class, 85/15 split.
- License: CC BY 4.0 (UCI).
- Fit: **3/5.** Directly relevant to the numeric-heavy census fields (age, counts). Isolated centered chars are easier than form digits; good for validating the digit-recognition slice.

### Hindi/Devanagari MNIST (Kaggle mirror of UCI digits)
- URL: https://www.kaggle.com/datasets/anurags397/hindi-mnist-data
- Size: digits only (0–9), ~1,700/class train, ~300/class test, 32×32.
- Fit: **3/5.** MNIST-shaped Devanagari digit split; quick smoke test for the numeric fields.

### CPAR-2012
- URLs: https://figshare.com/articles/dataset/Devanagari_Handwritten_Digit_and_Character_Dataset/25835629 ; pip `cpar` (https://github.com/gaganmanku96/CPAR)
- Size: ~35,000 isolated digits (11 classes — digit 9 has two forms), ~83,300 characters, 2,000 constrained + 2,000 unconstrained pangram pages; 2,000 writers with demographic metadata.
- License: public domain (Integrated Research Environment for Devanagari OCR).
- Fit: **3/5.** Writer-diverse digits + pangram text; the demographic metadata is useful for understanding which writer populations drive errors.

### CALAM Devanagari database
- URL: https://github.com/CalamDataset/Calam-Devanagari-database
- Size: 23,000+ chars w/ matras; 1,600 text pages, 8,800 lines, 120,000 words.
- Fit: **2/5.** Character-with-modifier focus; harder linguistic material (conjuncts/matras) than typical survey fields.

---

## 3. Scene-text / print Devanagari (context + robustness, not the core task)

### IIIT-IndicSTR-Word (Indic Scene Text on the Roadside)
- URL: https://cvit.iiit.ac.in/usodi/istr.php
- Size: 250K word images, 10 languages (incl. Hindi); GoPro roadside captures (blur, perspective, low-res, illumination).
- Fit: **3/5.** Not handwriting, but a strong degraded-print robustness benchmark; models that fail here will fail on poor fax scans.

### IndicSTR12
- URL: https://cvit.iiit.ac.in/research/projects/cvit-projects/indic-str12 (paper PDF)
- Size: ~27K real word images, ≥1,000/language, 12 languages + a synthetic 13-language set.
- Fit: **2/5.** Scene text; use the synthetic split only as augmentation source.

### Bharat Scene Text Dataset (BSTD) / IndicPhotoOCR
- URL: https://github.com/Bhashini-IITJ/IndicPhotoOCR (BSTD README)
- Size: 6,582 images, 126,292 words, 11 Indic langs + English, polygon boxes + script labels. `detection.zip` ~17 GB.
- Fit: **2/5.** End-to-end pipeline toolkit; detection/script-ID relevant if we ever move beyond answer-crops.

---

## 4. Synthetic Devanagari data (training augmentation / cheap regression sets)

### devanagari-ocr-synthetic-80k
- URL: https://huggingface.co/datasets/iamkushagratomar/devanagari-ocr-synthetic-80k
- Size: 80,000 rendered lines (76k train / 4k val), 900×64 PNG, 8 fonts, font_size/word_count metadata. Parquet.
- License: check repo card (community synthetic; typically permissive).
- Fit: **2/5.** Printed, not handwritten — cannot measure handwriting accuracy. Good for regression testing the recognition pipeline cheaply and as augmentation.

### PP-OCRv5 Devanagari recognition dataset (reference eval set)
- URL: https://github.com/PaddlePaddle/PaddleOCR (PP-OCRv5 multi-language doc)
- Size: 3,611 text images; backs `devanagari_PP-OCRv5_mobile_rec` (84.96% acc).
- Fit: **2/5.** Printed Devanagari. Shows PaddleOCR's own Devanagari baseline to compare our PaddleOCR run against.

---

## 5. Evaluation harnesses / metrics tooling (reuse directly)

### jiwer
- URL: https://github.com/jitsi/jiwer (pip: `jiwer`)
- CER/WER/MER/WIL via RapidFuzz; composable normalization transforms.
- Critical for Devanagari: apply Unicode NFC + whitespace collapse identically to reference and hypothesis before scoring (matras compose/decompose). Report CER, not WER, as primary — Devanagari is an abugida where one matra error changes word meaning; also report median CER and a "catastrophic rate" (fraction with CER > 50%) since a single visual Devanagari char can span multiple code points.
- Fit: **5/5.** This is the standard; our `benchmark.md` CER should be backed by jiwer with an explicit normalization transform.

### docTR (mindee)
- URL: https://github.com/mindee/doctr ; benchmark models page https://mindee.github.io/doctr/
- Published detection/recognition benchmarks on FUNSD & CORD (db_resnet50+parseq, etc.) and OCR-metric definitions. Recognizers: CRNN, MASTER, PARSeq, ViTSTR.
- Fit: **4/5.** Adds two more open engine candidates and a ready-made internal eval harness to plug our crop dataset into.

### PaddleOCR eval
- URL: https://www.paddleocr.ai/ ; PaddleX model benchmark tables https://paddlepaddle.github.io/PaddleX/
- Devanagari recognizers: `devanagari_PP-OCRv5_mobile_rec` (84.96%), `devanagari_PP-OCRv3_mobile_rec` (96.44% on its print eval set). Ships CER/recognition eval tooling.
- Fit: **4/5.** `devanagari_PP-OCRv3_mobile_rec` at 96.44% on print is a strong local candidate to benchmark against Tesseract `hin`.

### Indic-HTR-CVIP-2024 (PARSeq Indic HTR harness)
- URL: https://github.com/LalithaEvani/Indic-HTR-CVIP-2024
- Trains/evaluates PARSeq on IIIT-INDIC-HW-WORDS; reports CER+WER per language; pretraining + SWA recipes; Hindi WER substantially below prior SOTA.
- Fit: **4/5.** Reference implementation + published Hindi CER/WER numbers to sanity-check our engine comparison; reusable fine-tuning path (see `docs/fine-tuning.md`).

### indic-htr (sanny26)
- URL: https://github.com/sanny26/indic-htr
- TPS-ResNet-BiLSTM-CTC baselines + LMDB dataset builder + `tools/score.py` (WER/CER, incl. OOV-word CER against train vocab).
- Fit: **3/5.** The OOV CER split is directly useful: our census lexicon is small, so OOV handling matters.

---

## 6. Form-understanding / Document-VQA benchmarks and Indic equivalents

### FUNSD
- URL: https://guillaumejaume.github.io/FUNSD/
- Size: 199 scanned forms (149 train / 50 test), 9,707 entities, 31,485 words; classes question/answer/header/other; entity-linking. English.
- License: research use.
- Fit: **3/5.** The canonical form-KIE benchmark — directly analogous to our question-box/answer-box structure. English only, and print not handwriting, but the entity model and evaluation (field F1) map cleanly onto "answer-box assignment" for WARD-42. Use as a template for our own field-mapping eval once we go beyond crop recognition.

### DocVQA / InfographicVQA
- URLs: https://www.docvqa.org/ ; https://www.docvqa.org/datasets/infographicvqa
- Size: DocVQA ~50k Q&A on 12k document images (English, UCSF industry docs); InfoVQA ~30k Q&A on 5.3k images.
- Metric: ANLS.
- Fit: **1–2/5.** English, page-QA not crop recognition. Only a reference for whole-form reasoning once crops are solved.

### IndicVisionBench
- URL: https://arxiv.org/html/2511.04727v1 ; HF https://huggingface.co/datasets/krutrim-ai-labs/IndicVisionBench
- Size: 5K images, 37K+ QA, 11 languages (incl. Hindi); OCR track = 876 document images across 10 Indic scripts; human-verified.
- Fit: **2/5.** Printed Indic docs, VQA-centric; useful to compare local VLMs on Hindi document OCR and cultural/script robustness.

### Patram-Bench
- URL: https://link.springer.com/chapter/10.1007/978-3-032-36033-5_37
- Size: 52,607 docs, 23 languages, 13 domains, 71 classes, 52 tasks, 2.4M+ QA. Governance/education/finance/archival domains; metrics DUCLI + Script Robustness Score.
- Fit: **2/5.** Broadest Indic document-understanding benchmark; relevant to VLM comparison and script-robustness scoring, not handwriting CER.

---

## 7. Full-page handwritten Indic recognition benchmarks (beyond crops)

### ICDAR 2025 IHDR (Indic Handwritten Document Recognition competition)
- URL: https://ilocr.iiit.ac.in/icdar_2025_Indic_HDR/ ; dataset page .../dataset.html
- Size: 10,000 document images, ~400,000 words, ~1,000 writers, 10 Indic languages (incl. Hindi); mobile-camera capture (blur, perspective, illumination, low-res, shadow).
- Tasks: (A) word bounding-box detection, (B) page recognition/reading. Val/test splits downloadable per language; free for academic use.
- Fit: **4/5 for future whole-page work.** Closest public analogue to a scanned survey page under real conditions. Use to evaluate whole-form registration/reading once crop recognition is adequate (per `docs/benchmark.md` "next evaluate whole-form registration"). The camera-degradation profile is a good stress model for fax artifacts.

### ICDAR 2024 HWD / IHWWR-1.0 / PLHWTR-1.0
- URL: https://ilocr.iiit.ac.in/icdar_2024_hwd/dataset.html
- IHWWR-1.0: isolated word recognition, 4 langs (English, Hindi, Bengali, Telugu). PLHWTR-1.0: page-level recognition. GT = bboxes + reading order + transcription.
- Fit: **4/5.** IHWWR-1.0 is a direct word-image HTR benchmark; all usable as pretrain/eval.

### ICDAR 2023 IHTR
- Reference: https://dl.acm.org/doi/10.1007/978-3-031-41679-8_25 — winner 95.94% CRR / 88.31% WRR over 10 languages. Published SOTA numbers to benchmark against.

---

## Recommended reuse plan for `docs/benchmark.md`

1. **Primary public reference set:** IIIT-INDIC-HW-WORDS Hindi test split (CC BY 4.0) — 12,870 isolated handwritten word crops with transcripts. Compute CER/WER for Tesseract `hin`, Doc AI, local VLM, PaddleOCR `devanagari_PP-OCRv3_mobile_rec`, and docTR recognizers. This gives a public, comparable number before touching WARD-42.
2. **Metric tooling:** adopt `jiwer` with an explicit NFC + whitespace-collapse transform applied to both sides; report CER (primary), WER, median CER, and catastrophic rate (CER > 50%). Document the transform in `docs/benchmark.md`.
3. **Numeric-field smoke test:** UCI DHCD digits + Hindi-MNIST digits to validate the numeric slice (age/counts) cheaply.
4. **Degraded-print robustness:** IIIT-IndicSTR-Word Hindi subset to gauge fax-degradation tolerance.
5. **Whole-page next step (already in our plan):** ICDAR 2025 IHDR Hindi split for whole-form registration/reading once crop CER is acceptable.
6. **Fine-tuning reference:** Indic-HTR-CVIP-2024 + indic-htr provide published Hindi CER/WER baselines and OOV-aware scoring to align with `docs/fine-tuning.md`.

### Gaps (no good public equivalent found)
- **Handwritten Devanagari census/survey forms with field-level ground truth:** none public. WARD-42 labeling (`docs/benchmark.md`, `docs/annotation-workflow.md`) remains the only source for true field-assignment / form-structure accuracy. FUNSD is the structural template, not a data substitute.
- **Handwritten Indic form-KIE benchmark:** absent; FUNSD (English, print) is the closest structural analogue.
