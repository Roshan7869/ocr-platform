"""Read all PDFs in a directory using PaddleOCR and save extracted text."""

import json
import os
import sys
import time
from pathlib import Path

# Disable MKLDNN to avoid PIR attribute conversion bug in paddlepaddle 3.x
os.environ["FLAGS_use_mkldnn"] = "0"

import pypdfium2 as pdfium
from paddleocr import PaddleOCR


def find_pdfs(root: Path) -> list[Path]:
    return sorted(root.rglob("*.pdf"))


def ocr_pdf(pdf_path: Path, ocr: PaddleOCR, dpi: int = 200) -> dict:
    scale = dpi / 72
    pages = []
    with pdfium.PdfDocument(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(pdf):
            bitmap = page.render(scale=int(scale))
            pil_image = bitmap.to_pil()
            bitmap.close()
            page.close()

            # PaddleOCR expects numpy array (BGR)
            import numpy as np

            img_array = np.array(pil_image)[:, :, ::-1].copy()

            result = ocr.ocr(img_array)

            page_text = []
            if result and len(result) > 0:
                res = result[0]
                if res and isinstance(res, list):
                    for line in res:
                        if isinstance(line, list) and len(line) >= 2:
                            _bbox, (text, score) = line[0], line[1]
                            page_text.append({"text": text, "confidence": round(float(score), 4)})
                elif isinstance(res, dict):
                    res = res.get("res", res)
                    if res and "rec_texts" in res:
                        for text, score in zip(res["rec_texts"], res["rec_scores"]):
                            page_text.append({"text": text, "confidence": round(float(score), 4)})
                    elif res and "rec_text" in res:
                        page_text.append(
                            {
                                "text": res["rec_text"],
                                "confidence": round(float(res.get("rec_score", 0)), 4),
                            }
                        )

            pages.append(
                {
                    "page": page_idx,
                    "regions": page_text,
                    "text": " ".join(r["text"] for r in page_text),
                }
            )
            print(f"  Page {page_idx}: {len(page_text)} regions", flush=True)

    return {
        "pdf_path": str(pdf_path),
        "pdf_name": pdf_path.name,
        "page_count": len(pages),
        "pages": pages,
        "full_text": "\n\n".join(p["text"] for p in pages),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python ocr_read_pdfs.py <directory> [output.json]")
        sys.exit(1)

    root = Path(sys.argv[1])
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "ocr_results.json"

    pdfs = find_pdfs(root)
    print(f"Found {len(pdfs)} PDFs in {root}")

    print("Initializing PaddleOCR...")
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=True,
        lang="en",
        device="cpu",
    )

    results = []
    for i, pdf_path in enumerate(pdfs):
        print(f"\n[{i + 1}/{len(pdfs)}] Processing: {pdf_path.name}")
        start = time.time()
        try:
            result = ocr_pdf(pdf_path, ocr)
            elapsed = time.time() - start
            result["elapsed_seconds"] = round(elapsed, 2)
            results.append(result)
            print(f"  Done in {elapsed:.1f}s — {len(result['full_text'])} chars")
        except Exception as e:  # noqa: BLE001 - per-PDF failures must not abort batch; error recorded per file
            print(f"  ERROR: {e}")
            results.append(
                {
                    "pdf_path": str(pdf_path),
                    "pdf_name": pdf_path.name,
                    "error": str(e),
                    "page_count": 0,
                    "pages": [],
                    "full_text": "",
                }
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(
            {"source": str(root), "pdf_count": len(pdfs), "results": results},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n{'=' * 60}")
    print(f"Processed {len(pdfs)} PDFs")
    print(f"Results saved to: {output}")
    total_chars = sum(len(r.get("full_text", "")) for r in results)
    print(f"Total characters extracted: {total_chars}")
    errors = [r for r in results if "error" in r]
    if errors:
        print(f"Errors: {len(errors)}")
        for e in errors:
            print(f"  - {e['pdf_name']}: {e['error']}")


if __name__ == "__main__":
    main()
