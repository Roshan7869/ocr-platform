## Role

WARD-42 survey form template — fixed-grid alignment config for PDF-to-cell mapping.

## Contracts

- `page_size`: [width, height] at 200 DPI
- `global_anchors`: four corners [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
- `column_dividers_top` / `column_dividers_bottom`: x-coordinates of vertical grid lines (page 1 / page 2)
- `row_dividers`: y-coordinates of horizontal grid lines
- `header_rows`: number of non-member rows at top
- `members_start_row`: first row index containing member data
- `member_table_cols`: ordered list of column names for page 2 member table
- `fields`: header field → {page, row, col, col_span}
- `page2_fields`: member field name → column index

## Infrastructure

- Standard library only (JSON)

## Depends on

- SurveyPipeline `__init__` loads this JSON to set up grid slicing

## Tests

- `tests/test_docs_contract.py`

## Milestone

M02 — Template alignment

## Status

IMPLEMENTED

## Owner

OCR Platform team
