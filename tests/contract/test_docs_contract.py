"""Verify CI checks implemented-file contracts, without requiring planned code."""

import tempfile
import unittest
from pathlib import Path

from scripts.check_docs_contract import SECTIONS, check


class DocsContractTests(unittest.TestCase):
    def test_repository_implemented_files_have_contracts(self):
        self.assertEqual(check(Path(__file__).resolve().parents[2]), [])

    def test_missing_contract_and_spec_only_status_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src/feature.py").write_text("value = 1\n")
            (root / "pyproject.toml").write_text("[project]\n")
            self.assertTrue(check(root))
            for relative in ["src/feature.py", "pyproject.toml"]:
                contract = root / "docs/files" / (relative + ".md")
                contract.parent.mkdir(parents=True, exist_ok=True)
                contract.write_text("\n".join(f"## {s}\n\nSPEC\n" for s in SECTIONS))
            self.assertTrue(any("still marked SPEC" in e for e in check(root)))
            for contract in (root / "docs/files").rglob("*.md"):
                contract.write_text(contract.read_text().replace("SPEC", "IMPLEMENTED"))
            self.assertEqual(check(root), [])


if __name__ == "__main__":
    unittest.main()
