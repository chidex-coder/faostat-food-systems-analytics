"""Delivery-surface checks: every emitted HTML loads the one pinned, integrity-checked Plotly.js,
and the archive pins file is well-formed."""
import json
import re
from pathlib import Path

import pytest

from src.config import DOCS_DIR, FIGURES_DIR, REFERENCE_DIR, DOMAINS
from src.web import PLOTLY_JS_SRI, PLOTLY_JS_URL

SCRIPT_RE = re.compile(r'<script[^>]+src="(https?://[^"]+)"[^>]*>')


def _emitted_html():
    files = sorted(FIGURES_DIR.glob("*.html")) + sorted((DOCS_DIR / "figures").glob("*.html"))
    index = DOCS_DIR / "index.html"
    if index.exists():
        files.append(index)
    return files


@pytest.mark.skipif(not (DOCS_DIR / "index.html").exists(), reason="dashboard not built")
def test_every_external_script_is_the_pinned_plotly_with_sri():
    for f in _emitted_html():
        text = f.read_text()
        for m in SCRIPT_RE.finditer(text):
            tag, src = m.group(0), m.group(1)
            assert src == PLOTLY_JS_URL, f"{f.name} loads an unpinned script: {src}"
            assert f'integrity="{PLOTLY_JS_SRI}"' in tag and 'crossorigin="anonymous"' in tag, f"{f.name} lacks SRI on {src}"


@pytest.mark.skipif(not (DOCS_DIR / "index.html").exists(), reason="dashboard not built")
def test_dashboard_declares_public_classification_and_no_external_data():
    text = (DOCS_DIR / "index.html").read_text()
    assert '"data_classification":"public"' in text
    assert "fetch(" not in text and "XMLHttpRequest" not in text


def test_sri_hash_is_well_formed():
    assert re.fullmatch(r"sha384-[A-Za-z0-9+/]{64}", PLOTLY_JS_SRI)


def test_archive_pins_cover_every_domain():
    pins = json.loads((REFERENCE_DIR / "archive_pins.json").read_text())
    assert set(pins) == set(DOMAINS)
    for code, pin in pins.items():
        assert re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]), code
        assert pin["bytes"] > 0
