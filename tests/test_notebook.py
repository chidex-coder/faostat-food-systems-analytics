"""The executed notebook must be clean: no errors, every question present, no local paths, no boilerplate."""
import json
from pathlib import Path

import pytest

from src.analysis import HANDLERS
from src.config import ROOT

NB = ROOT / "notebooks" / "food_systems_analysis.ipynb"
pytestmark = pytest.mark.skipif(not NB.exists(), reason="notebook not built")


def _nb():
    return json.loads(NB.read_text())


def test_notebook_executed_without_errors():
    outs = [o for c in _nb()["cells"] for o in c.get("outputs", [])]
    assert outs, "notebook has no outputs - was it executed?"
    assert not [o for o in outs if o["output_type"] == "error"]


def test_every_question_and_model_has_a_figure():
    src = "\n".join("".join(c["source"]) for c in _nb()["cells"])
    for slug in HANDLERS:
        assert f'answer("{slug}")' in src, slug
    pngs = sum(1 for c in _nb()["cells"] for o in c.get("outputs", []) if "image/png" in o.get("data", {}))
    assert pngs >= len(HANDLERS) + 4


def test_no_local_paths_or_generator_boilerplate():
    text = NB.read_text()
    assert "/Users/" not in text and "/home/" not in text
    assert "generated from" not in text.lower()
