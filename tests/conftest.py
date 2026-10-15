"""Pytest configuration — src layout plus integration fixture selector."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def pytest_addoption(parser):
    """Accept ``--fixture <name>`` for integration runs (ci-spec §6)."""
    parser.addoption(
        "--fixture",
        action="store",
        default=None,
        help="Fixture label for integration runs (e.g. smoke-001).",
    )
