# src/ocr_platform/document/loader.py

## Role
Loads images, directories, ZIP archives, and rendered PDF pages.

## Contracts
Returns immutable pages with normalized PNG bytes, dimensions, metadata, and SHA-256 hashes.

## Infrastructure
Pillow, pypdfium2, and ZIP support.

## Depends on
pypdfium2 for PDF inputs.

## Tests
`tests/test_document_loader.py`.

## Milestone
M01 document loading.

## Status
IMPLEMENTED

## Owner
OCR Platform team
