"""Extract stage: fetch FAOSTAT bulk archives (and optionally the REST API).

Design notes
------------
* Bulk zips are the primary source: they are public, versioned by FAO (each has
  a `last-modified` header and an ETag) and carry their own code lists.
* Downloads are resumable (`Range` header) because the bucket is slow from some
  networks and the largest domain is ~34 MB.
* Every archive is hashed (SHA-256) and recorded in a manifest so a rebuild can
  prove which release of each domain it was built from.
* FAO publishes no signatures, so the project pins the hashes it has reviewed in
  `data/reference/archive_pins.json` (trust-on-first-use). A download whose hash
  differs from the pin is rejected unless the caller explicitly accepts the new
  release (`accept_new_releases=True`, `run_pipeline.py --update-pins`), which
  turns "what was fetched" into "the same bytes that were reviewed".
* The client is deliberately polite: an identifying User-Agent, conditional
  requests (`If-None-Match`) so an unchanged archive is never re-downloaded, a
  minimum spacing between requests, and exponential back-off with jitter. Do not
  schedule this more often than FAO releases data (monthly at most).
* The REST API path exists for completeness (`FAOSTAT_TOKEN`); it returns the
  same schema in JSON, so downstream code is agnostic to where a domain came from.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import API_BASE_URL, BULK_BASE_URL, BULK_CATALOGUE_URL, DOMAINS, RAW_DIR, REFERENCE_DIR, Domain

MANIFEST_PATH = RAW_DIR / "manifest.json"
PINS_PATH = REFERENCE_DIR / "archive_pins.json"
CHUNK = 1 << 20
USER_AGENT = "faostat-food-systems-analytics/1.0 (+https://github.com/chidex-coder/faostat-food-systems-analytics)"
MIN_REQUEST_INTERVAL = 1.0   # seconds between requests to the FAO bucket
_last_request_at = 0.0


class ReleaseMismatch(RuntimeError):
    """A downloaded archive does not match the pinned, reviewed hash."""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def _throttle() -> None:
    global _last_request_at
    wait = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def _backoff(attempt: int) -> None:
    time.sleep(min(60, 2 ** attempt) + random.uniform(0, 1))


def _head(session: requests.Session, url: str) -> dict:
    _throttle()
    r = session.head(url, timeout=60, allow_redirects=True)
    r.raise_for_status()
    return {k.lower(): v for k, v in r.headers.items()}


def download(url: str, dest: Path, retries: int = 6, known_etag: str | None = None,
             session: requests.Session | None = None) -> tuple[Path, dict]:
    """Resumable, conditional download with retry; returns (dest, response headers).

    If `known_etag` matches the server's current ETag and the file is complete,
    nothing is transferred (HTTP 304 semantics via If-None-Match).
    """
    session = session or _session()
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = _head(session, url)
    total = int(headers.get("content-length", 0))
    complete = dest.exists() and total and dest.stat().st_size == total
    if complete and known_etag and headers.get("etag") == known_etag:
        return dest, headers
    for attempt in range(1, retries + 1):
        have = dest.stat().st_size if dest.exists() else 0
        if total and have >= total:
            break
        req_headers = {"Range": f"bytes={have}-"} if have else {}
        if not have and known_etag:
            req_headers["If-None-Match"] = known_etag
        try:
            _throttle()
            with session.get(url, headers=req_headers, stream=True, timeout=(30, 300)) as r:
                if r.status_code == 304:
                    break
                if r.status_code not in (200, 206):
                    r.raise_for_status()
                mode = "ab" if r.status_code == 206 else "wb"
                with dest.open(mode) as f:
                    for block in r.iter_content(CHUNK):
                        f.write(block)
        except (requests.RequestException, OSError) as exc:  # noqa: PERF203
            print(f"    retry {attempt}/{retries} after error: {exc}")
            _backoff(attempt)
    if total and dest.stat().st_size != total:
        raise RuntimeError(f"incomplete download for {url}: {dest.stat().st_size}/{total} bytes")
    with zipfile.ZipFile(dest) as zf:
        bad = zf.testzip()
        if bad:
            dest.unlink()
            raise RuntimeError(f"corrupt member {bad} in {dest.name}; deleted, re-run")
    return dest, headers


def fetch_catalogue(session: requests.Session | None = None) -> dict:
    session = session or _session()
    _throttle()
    r = session.get(BULK_CATALOGUE_URL, timeout=60)
    r.raise_for_status()
    return {d["DatasetCode"]: d for d in r.json()["Datasets"]["Dataset"]}


def load_pins() -> dict:
    return json.loads(PINS_PATH.read_text()) if PINS_PATH.exists() else {}


def verify_pin(code: str, sha256: str, pins: dict, accept_new_releases: bool) -> str:
    """Return 'pinned' | 'new' | 'updated'; raise ReleaseMismatch when a change is not accepted."""
    pin = pins.get(code)
    if pin is None:
        return "new"
    if pin["sha256"] == sha256:
        return "pinned"
    if not accept_new_releases:
        raise ReleaseMismatch(
            f"{code}: downloaded archive sha256 {sha256[:12]}… differs from the reviewed pin {pin['sha256'][:12]}… "
            f"(pinned release {pin.get('catalogue_date_update')}). FAO may have published a new release; "
            f"re-run with --update-pins after reviewing the change, or delete data/raw/ to retry the download.")
    return "updated"


def extract_bulk(domains: dict[str, Domain] = DOMAINS, force: bool = False, accept_new_releases: bool = False) -> dict:
    """Download every configured domain; verify against pins; return the manifest."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    session = _session()
    manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {}
    pins = load_pins()
    try:
        catalogue = fetch_catalogue(session)
    except requests.RequestException as exc:
        print(f"  catalogue unavailable ({exc}); continuing with file headers only")
        catalogue = {}
    for code, dom in domains.items():
        url = BULK_BASE_URL + dom.zip_name
        dest = RAW_DIR / dom.zip_name
        if force and dest.exists():
            dest.unlink()
        known_etag = (manifest.get(code) or {}).get("etag")
        dest, headers = download(url, dest, known_etag=known_etag, session=session)
        digest = sha256_of(dest)
        status = verify_pin(code, digest, pins, accept_new_releases)
        entry = {
            "domain": code,
            "name": dom.name,
            "file": dom.zip_name,
            "url": url,
            "bytes": dest.stat().st_size,
            "sha256": digest,
            "server_last_modified": headers.get("last-modified"),
            "etag": headers.get("etag"),
            "catalogue_date_update": (catalogue.get(code) or {}).get("DateUpdate"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pin_status": status,
        }
        manifest[code] = entry
        if status in ("new", "updated"):
            pins[code] = {"sha256": digest, "bytes": entry["bytes"], "server_last_modified": entry["server_last_modified"],
                          "catalogue_date_update": entry["catalogue_date_update"], "pinned_at": entry["downloaded_at"]}
        print(f"  [{code}] {dom.zip_name}  {digest[:12]}…  {status}")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    PINS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PINS_PATH.write_text(json.dumps(dict(sorted(pins.items())), indent=2) + "\n")
    return manifest


# ----------------------------------------------------------------------------
# Optional REST API client (token required by FAO since 2026)
# ----------------------------------------------------------------------------
class FaostatApi:
    """Thin client for https://faostatservices.fao.org/api/v1.

    Usage: FaostatApi(os.environ["FAOSTAT_TOKEN"]).data("QCL", area=106, item=15,
    element=2510, year=2022). The token is read from the environment, sent only
    as a bearer header, and never logged or persisted.
    """

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("FAOSTAT_TOKEN")
        if not self.token:
            raise RuntimeError("FAOSTAT_TOKEN is not set; the REST API needs a personal token")
        self.session = _session()
        self.session.headers["Authorization"] = f"Bearer {self.token}"

    def __repr__(self) -> str:  # never leak the token in tracebacks or logs
        return "FaostatApi(token=***)"

    def _get(self, path: str, **params) -> dict:
        _throttle()
        r = self.session.get(API_BASE_URL + path, params=params, timeout=120)
        r.raise_for_status()
        return r.json()

    def groups_and_domains(self) -> dict:
        return self._get("groupsanddomains")

    def definitions(self, domain: str, dimension: str) -> dict:
        return self._get(f"definitions/domain/{domain}/{dimension}", show_lists="true")

    def data(self, domain: str, **filters) -> list[dict]:
        return self._get(f"data/{domain}", **filters).get("data", [])


if __name__ == "__main__":
    print(json.dumps(extract_bulk(), indent=2))
