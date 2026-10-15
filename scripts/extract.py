"""R0 single-process extractor CLI (Stream E entrypoint, Docker ENTRYPOINT).

Thin wrapper: resolve a classified fixture (via ``ocr_platform.fixtures.loader``)
or an explicit raw path, run :class:`SurveyPipeline`, write canonical
``result.json`` + ``review_candidates.json`` (+ ``provenance.json``) under
``--out``.

Exit codes: 0 success, 2 validation/provenance failure, 3 spike/pins missing,
4 usage. No hidden flags disable the provenance validator; no auto-accept
overrides (``allow_auto_accept`` stays ``False``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

EXIT_SUCCESS = 0
EXIT_VALIDATION = 2
EXIT_PINS_MISSING = 3
EXIT_USAGE = 4


class PinsMissingError(RuntimeError):
    """Pipeline imports unavailable: spike/pins environment not yet landed."""


_REPO_SRC = Path(__file__).resolve().parents[1] / "src"
if _REPO_SRC.is_dir() and str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

TEMPLATE_VERSION = "FAMILY_SURVEY_V1"
DEFAULT_TEMPLATE_HASH = "6a8b83bc3cb26b498454f018a78f2e78dce160dda49208d3dd423c589d2a7bdf"
DEFAULT_TEMPLATE_PATH = Path("templates/family_survey_v1/template.json")
DEFAULT_POLICY = "v1"


class UsageParser(argparse.ArgumentParser):
    """ArgumentParser that reports usage problems with exit code 4."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: error: {message}\n")


def build_parser() -> UsageParser:
    parser = UsageParser(
        prog="extract.py",
        description=(
            "R0 single-process extractor: run the survey pipeline on a classified "
            f"fixture (--fixture ID) or a raw path, using template {TEMPLATE_VERSION}."
        ),
    )
    parser.add_argument("input", nargs="?", help="Raw input PDF/ZIP/image-dir path.")
    parser.add_argument("--fixture", metavar="ID", help="Classified fixture id.")
    parser.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE_HASH,
        help=("Approved template hash (default: FAMILY_SURVEY_V1 sha256) or a template JSON path."),
    )
    parser.add_argument("--out", default="out", help="Output directory.")
    parser.add_argument("--policy", default=DEFAULT_POLICY, help="Policy version.")
    parser.add_argument(
        "--allow-unclassified",
        action="store_true",
        help="Permit raw-path mode (marks the run as user_input).",
    )
    return parser


def fail(code: int, message: str) -> int:
    print(f"extract: error: {message}", file=sys.stderr)
    return code


def template_hash_for(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_template(requested: str) -> tuple[Path, str]:
    """Resolve --template (hash or path) to (template_path, template_hash)."""
    candidate = Path(requested)
    if candidate.is_file():
        return candidate, template_hash_for(candidate)
    known = DEFAULT_TEMPLATE_PATH
    if not known.is_file():
        raise FileNotFoundError(f"template package missing: {known}")
    actual = template_hash_for(known)
    if requested != actual:
        raise ValueError(
            f"template hash mismatch: requested {requested!r} != "
            f"approved {TEMPLATE_VERSION} {actual!r}"
        )
    return known, actual


def resolve_fixture_input(fixture_id: str) -> Path:
    """Resolve a fixture id via the fixtures loader (fail-closed).

    Uses ``load_fixture`` (``FixtureRef.path``) when available and maps every
    loader gate rejection (``FixtureError`` subclasses: unknown id, hash
    mismatch, unclassified, expired, ...) to ``LookupError`` so callers exit 2.
    """
    try:
        from ocr_platform.fixtures import loader as fixture_loader
    except ImportError:
        fixture_loader = None
    if fixture_loader is None:
        raise LookupError(
            "fixture loader unavailable "
            "(src/ocr_platform/fixtures/loader.py not yet implemented); "
            f"cannot resolve fixture {fixture_id!r}. "
            "Classification is fail-closed: no fixture input is accepted "
            "until the loader lands."
        )
    try:
        load = fixture_loader.load_fixture
    except AttributeError:
        raise LookupError(
            f"fixture loader has no load_fixture entry point for {fixture_id!r}"
        ) from None
    fixture_error = getattr(fixture_loader, "FixtureError", Exception)
    if not isinstance(fixture_error, type):
        fixture_error = Exception
    try:
        ref = load(fixture_id)
    except fixture_error as exc:
        raise LookupError(str(exc)) from exc
    path = getattr(ref, "path", ref)
    return path if isinstance(path, Path) else Path(path)


def collect_review_candidates(documents: list[dict], page_errors: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for doc in documents:
        doc_id = doc.get("doc_id", "")
        page_index = doc.get("page_index", 0)
        for section in ("header",):
            fields = doc.get(section, {})
            if isinstance(fields, dict):
                for field_key, cell in fields.items():
                    if isinstance(cell, dict) and cell.get("disposition") != "accepted":
                        candidates.append(
                            {
                                "doc_id": doc_id,
                                "page_index": page_index,
                                "cell_id": cell.get("cell_id", ""),
                                "field_key": field_key,
                                "observed_value": cell.get("observed_value", ""),
                                "reason": cell.get("route", "review"),
                            }
                        )
        for member in doc.get("members", []):
            fields = member.get("fields", {})
            if isinstance(fields, dict):
                for field_key, cell in fields.items():
                    if isinstance(cell, dict) and cell.get("disposition") != "accepted":
                        candidates.append(
                            {
                                "doc_id": doc_id,
                                "page_index": page_index,
                                "cell_id": cell.get("cell_id", ""),
                                "field_key": field_key,
                                "observed_value": cell.get("observed_value", ""),
                                "reason": cell.get("route", "review"),
                            }
                        )
    for error in page_errors:
        candidates.append(
            {
                "doc_id": error.get("doc_id", ""),
                "page_index": error.get("page_index", 0),
                "cell_id": "",
                "field_key": "",
                "observed_value": "",
                "reason": error.get("reason", "page_error"),
            }
        )
    return candidates


def run_pipeline(source: Path, template_path: Path, out_dir: Path) -> dict:
    try:
        from ocr_platform.orchestrator.pipeline import SurveyPipeline
    except ImportError as exc:
        raise PinsMissingError(
            f"pipeline dependencies unavailable (spike/pins missing): {exc}"
        ) from exc
    pipeline = SurveyPipeline(
        template_path=template_path,
        db_path=out_dir / "evidence.db",
        output_dir=out_dir,
        allow_auto_accept=False,
    )
    return pipeline.run(source)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.input is None and args.fixture is None:
        parser.error("one of input path or --fixture <id> is required")
    if args.input is not None and args.fixture is not None:
        parser.error("pass either an input path or --fixture <id>, not both")

    try:
        template_path, template_hash = resolve_template(args.template)
    except (FileNotFoundError, ValueError) as exc:
        return fail(EXIT_VALIDATION, str(exc))

    out_dir = Path(args.out)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return fail(EXIT_VALIDATION, f"cannot create --out {out_dir}: {exc}")

    if args.fixture is not None:
        try:
            source = resolve_fixture_input(args.fixture)
        except (LookupError, FileNotFoundError, ValueError) as exc:
            return fail(EXIT_VALIDATION, str(exc))
        input_kind = "fixture"
        input_ref = args.fixture
        if not source.is_file():
            return fail(
                EXIT_VALIDATION,
                f"fixture {args.fixture!r} did not resolve to a file: {source}",
            )
    else:
        if not args.allow_unclassified:
            return fail(
                EXIT_VALIDATION,
                "raw-path mode requires explicit --allow-unclassified "
                "(R0 default deny; run is marked user_input)",
            )
        source = Path(args.input)
        if not source.exists():
            return fail(EXIT_VALIDATION, f"input path does not exist: {source}")
        input_kind = "user_input"
        input_ref = str(source)

    try:
        result = run_pipeline(source, template_path, out_dir)
    except PinsMissingError as exc:
        return fail(EXIT_PINS_MISSING, str(exc))
    except Exception as exc:  # noqa: BLE001 - CLI must report clean errors + codes
        return fail(EXIT_VALIDATION, f"validation/provenance failure: {exc}")
    if result.get("error"):
        return fail(EXIT_VALIDATION, f"extraction failed: {result['error']}")

    run_id = result.get("run_id") or f"run_{uuid.uuid4().hex[:8]}"
    stats = result.get("stats", {})
    page_errors = result.get("page_errors", [])
    accepted = int(stats.get("auto", 0))
    review = int(stats.get("low_conf", 0))
    errored = len(page_errors)
    documents = result.get("documents", [])
    review_candidates = collect_review_candidates(documents, page_errors)

    result_doc = {
        "run_id": run_id,
        "template_version": TEMPLATE_VERSION,
        "template_hash": template_hash,
        "policy_version": args.policy,
        "input": {"kind": input_kind, "ref": input_ref},
        "counts": {"accepted": accepted, "review": review, "errored": errored},
        "stats": stats,
        "output_files": ["result.json", "review_candidates.json", "provenance.json"],
    }
    (out_dir / "result.json").write_text(
        json.dumps(result_doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "review_candidates.json").write_text(
        json.dumps(review_candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    provenance_doc = {
        "run_id": run_id,
        "template_version": TEMPLATE_VERSION,
        "template_hash": template_hash,
        "policy_version": args.policy,
        "input": {"kind": input_kind, "ref": input_ref},
        "note": "FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE",
    }
    (out_dir / "provenance.json").write_text(
        json.dumps(provenance_doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"run_id: {run_id}")
    print(f"template: {TEMPLATE_VERSION} {template_hash}")
    print(f"policy: {args.policy}")
    print(f"accepted: {accepted}  review: {review}  errored: {errored}")
    print(f"wrote: {out_dir / 'result.json'} {out_dir / 'review_candidates.json'}")
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
