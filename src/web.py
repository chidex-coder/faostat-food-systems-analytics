"""Shared web-delivery settings: the single pinned Plotly.js build and its SRI hash.

Every HTML this project emits (35 question figures, 4 model figures, the
dashboard) loads Plotly.js from the same URL with the same Subresource
Integrity hash, so a tampered CDN response is refused by the browser rather
than executed. Bump the version and hash together; tests/test_web.py checks
that no emitted file drifts from this pin.
"""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

PLOTLY_JS_VERSION = "4.1.1"
PLOTLY_JS_URL = f"https://cdn.plot.ly/plotly-{PLOTLY_JS_VERSION}.min.js"
# sha384 of the file at PLOTLY_JS_URL; recompute with:
#   curl -sS $URL | openssl dgst -sha384 -binary | openssl base64 -A
PLOTLY_JS_SRI = "sha384-AFNp2MtSm5/oZbEs/J19F/Ah57MEiVsoed8nE3fq2Wnccdl1u/EkyJ9XKKU8rt7+"
PLOTLY_SCRIPT_TAG = (f'<script src="{PLOTLY_JS_URL}" integrity="{PLOTLY_JS_SRI}" '
                     f'crossorigin="anonymous" charset="utf-8"></script>')

FIGURE_CONFIG = {"displaylogo": False, "responsive": True}


def write_figure(fig: go.Figure, path: Path, title: str | None = None) -> None:
    """Write a standalone figure page that loads the pinned, integrity-checked Plotly.js."""
    body = fig.to_html(include_plotlyjs=False, full_html=False, config=FIGURE_CONFIG)
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>{title or path.stem}</title>
{PLOTLY_SCRIPT_TAG}
<style>html,body{{margin:0;height:100%;background:#fcfcfb}}</style>
</head>
<body>
{body}
</body>
</html>
"""
    path.write_text(doc)
