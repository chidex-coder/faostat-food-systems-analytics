# Security and data-handling notes

This project processes only public statistics. These notes record what is
protected, how, and what remains a residual risk, so that anyone reusing the
pattern on other data knows where the edges are.

## Supply chain

| Concern | Control | Residual |
|---|---|---|
| Tampered Plotly.js from the CDN | One pinned build (`src/web.py`) loaded with a Subresource Integrity hash and `crossorigin="anonymous"` in every emitted HTML; `tests/test_web.py` fails if any file drifts | A browser without SRI support (none current) would not verify |
| Tampered or replaced FAO archive | Size + zip-integrity checks; SHA-256 recorded in the manifest and pinned in `data/reference/archive_pins.json`; a hash that differs from the reviewed pin aborts the build unless `--update-pins` is passed after review | FAO publishes no signatures, so the first pin is trust-on-first-use over HTTPS |
| Python dependency drift | `requirements.lock` (exact versions); `requirements.txt` states minimums for development | No hash-pinning of wheels (`pip --require-hashes`); add if the build must be bit-for-bit reproducible |

## Credentials

The build needs none. The optional REST client reads `FAOSTAT_TOKEN` from the
environment, sends it only as a bearer header, and its `repr` masks it so it
cannot leak into tracebacks or logs. Never commit a token; `.env` files are not
read by this project on purpose.

## Being a good client of FAO's bucket

* Identifying `User-Agent` with a link to this repository.
* Conditional requests (`If-None-Match`): an unchanged archive is never re-downloaded.
* Resumable downloads, at most one request per second, exponential back-off with jitter.
* Guidance: FAO updates domains monthly at most. Do not schedule the extract stage more often than weekly.

## Publication boundary of the dashboard

`docs/index.html` inlines its data as JSON, so **everything on the page is
visible through view-source**. That is acceptable here because every input is
FAO open data or an aggregate derived from it, and the page says so
(`meta.data_classification = "public"`). The builder enforces an explicit
allowlist of blocks and fields (`PUBLISHABLE` in `src/dashboard.py`) and refuses
to build if an unreviewed field appears or the classification is not public.
If you reuse this pattern on restricted data: do not inline, serve data behind
authentication, and remove the allowlist bypass rather than widening it.

## Models

The models are descriptive screening aids trained on FAO's *modelled* series;
see `models/MODEL_CARD.md` for intended use, exclusions and known failure
modes. The dashboard's *Predictions* tab carries the same warning.

## Reporting

Open an issue on the repository. There is no bug bounty.
