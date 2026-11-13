"""Retrieval evaluation: a fixed set of questions with the source each should find.

Re-run on every change (CI). Fails if any expected source drops out of the top 3."""
import json

from runbookqa.index import search

from .conftest import ROOT


def test_expected_source_in_top_3(db):
    cases = json.loads((ROOT / "examples" / "eval" / "questions.json").read_text())
    misses = []
    for case in cases:
        paths = [c.path for c in search(db, case["question"], k=3, access=case.get("access"))]
        if case["expected"] not in paths:
            misses.append((case["question"], paths))
    assert not misses, misses
