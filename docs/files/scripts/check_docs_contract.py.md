# scripts/check_docs_contract.py

## Role

Enforce mirrored contracts for implemented files in CI.

## Contracts

Every implemented non-init source/config/template/test/script plus packaging/workflow needs eight responsibility sections and IMPLEMENTED/VERIFIED status. Planned files may remain SPEC. This presence check does not imply GitNexus verification or functional conformity.

## Infrastructure

stdlib; repository filesystem; no external services.

## Depends on

CI workflow; docs/files; test_docs_contract.py.

## Tests

Missing contracts, SPEC status and complete repository contracts.

## Milestone

Experimental local training and documentation alignment; production gates remain open.

## Status

IMPLEMENTED (not GitNexus VERIFIED).

## Owner

engineering; survey owns independently verified gold labels and codebooks.
