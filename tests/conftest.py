from pathlib import Path

import pytest

from runbookqa.index import build_index

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "examples" / "docs"
RECORDED = ROOT / "examples" / "recorded"


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "index.db"
    build_index([DOCS], path)
    return path
