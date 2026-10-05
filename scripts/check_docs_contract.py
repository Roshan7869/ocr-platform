"""Check responsibility contracts for implemented repository files."""

from pathlib import Path

SECTIONS = (
    "Role",
    "Contracts",
    "Infrastructure",
    "Depends on",
    "Tests",
    "Milestone",
    "Status",
    "Owner",
)


def check(root: Path) -> list[str]:
    paths = []
    for folder, pattern in [
        ("src", "*.py"),
        ("tests", "test_*.py"),
        ("scripts", "*.py"),
        ("configs", "*"),
        ("templates", "*"),
        (".github/workflows", "*.yml"),
    ]:
        paths.extend(
            p
            for p in (root / folder).rglob(pattern)
            if p.is_file() and p.name != "__init__.py" and p.stat().st_size
        )
    paths.append(root / "pyproject.toml")
    errors = []
    for path in paths:
        relative = path.relative_to(root)
        contract = root / "docs/files" / (relative.as_posix() + ".md")
        if not contract.is_file():
            errors.append(f"Missing docs contract: {relative}")
            continue
        text = contract.read_text(encoding="utf-8")
        for section in SECTIONS:
            if f"## {section}" not in text:
                errors.append(f"Missing {section} section: {relative}")
        if "IMPLEMENTED" not in text and "VERIFIED" not in text:
            errors.append(f"Implemented file still marked SPEC: {relative}")
    return errors


def main() -> int:
    errors = check(Path(__file__).resolve().parents[1])
    for error in errors:
        print(error)
    if not errors:
        print("Implemented-file docs contracts passed")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
