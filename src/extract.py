"""Extract stage: fetch FAOSTAT bulk archives (and optionally the REST API).

Design notes
------------
* Bulk zips are the primary source: they are public, versioned by FAO (each has
  a `last-modified` header and an ETag) and carry their own code lists.
* Downloads are resumable (`Range` header) because the bucket is slow from some
  networks and the largest domain is ~34 MB.
* Every archive is hashed (SHA-256) and recorded in a manifest so a rebuild can
  prove which release of each domain it was built from.
* The REST API path exists for completeness (`FAOSTAT_TOKEN`); it returns the
  same schema in JSON, so downstream code is agnostic to where a domain came from.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import API_BASE_URL, BULK_BASE_URL, BULK_CATALOGUE_URL, DOMAINS, RAW_DIR, Domain

MANIFEST_PATH = RAW_DIR / "manifest.json"
CHUNK = 1 << 20


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _head(url: str) -> dict:
    r = requests.head(url, timeout=60, allow_redirects=True)
    r.raise_for_status()
    return {k.lower(): v for k, v in r.headers.items()}


def download(url: str, dest: Path, retries: int = 6) -> Path:
    """Resumable download with retry; returns dest once the size matches the server."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = _head(url)
    total = int(headers.get("content-length", 0))
    if dest.exists() and total and dest.stat().st_size == total:
        return dest
    for attempt in range(1, retries + 1):
        have = dest.stat().st_size if dest.exists() else 0
        if total and have >= total:
            break
        req_headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with requests.get(url, headers=req_headers, stream=True, timeout=(30, 300)) as r:
                if r.status_code not in (200, 206):
                    r.raise_for_status()
                mode = "ab" if r.status_code == 206 else "wb"
                with dest.open(mode) as f:
                    for block in r.iter_content(CHUNK):
                        f.write(block)
        except (requests.RequestException, OSError) as exc:  # noqa: PERF203
            print(f"    retry {attempt}/{retries} after error: {exc}")
            time.sleep(2 * attempt)
    if total and dest.stat().st_size != total:
        raise RuntimeError(f"incomplete download for {url}: {dest.stat().st_size}/{total} bytes")
    with zipfile.ZipFile(dest) as zf:
        bad = zf.testzip()
        if bad:
            dest.unlink()
            raise RuntimeError(f"corrupt member {bad} in {dest.name}; deleted, re-run")
    return dest


def fetch_catalogue() -> dict:
    r = requests.get(BULK_CATALOGUE_URL, timeout=60)
    r.raise_for_status()
    return {d["DatasetCode"]: d for d in r.json()["Datasets"]["Dataset"]}


def extract_bulk(domains: dict[str, Domain] = DOMAINS, force: bool = False) -> dict:
    """Download every configured domain; return the manifest."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {}
    try:
        catalogue = fetch_catalogue()
    except requests.RequestException as exc:
        print(f"  catalogue unavailable ({exc}); continuing with file headers only")
        catalogue = {}
    for code, dom in domains.items():
        url = BULK_BASE_URL + dom.zip_name
        dest = RAW_DIR / dom.zip_name
        if force and dest.exists():
            dest.unlink()
        print(f"  [{code}] {dom.zip_name}")
        download(url, dest)
        headers = _head(url)
        entry = {
            "domain": code,
            "name": dom.name,
            "file": dom.zip_name,
            "url": url,
            "bytes": dest.stat().st_size,
            "sha256": sha256_of(dest),
            "server_last_modified": headers.get("last-modified"),
            "etag": headers.get("etag"),
            "catalogue_date_update": (catalogue.get(code) or {}).get("DateUpdate"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        manifest[code] = entry
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    return manifest


# ----------------------------------------------------------------------------
# Optional REST API client (token required by FAO since 2026)
# ----------------------------------------------------------------------------
class FaostatApi:
    """Thin client for https://faostatservices.fao.org/api/v1.

    Usage: FaostatApi(os.environ["FAOSTAT_TOKEN"]).data("QCL", area=106, item=15,
    element=2510, year=2022). Never log or persist the token.
    """

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("FAOSTAT_TOKEN")
        if not self.token:
            raise RuntimeError("FAOSTAT_TOKEN is not set; the REST API needs a personal token")
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _get(self, path: str, **params) -> dict:
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
    m = extract_bulk()
    print(json.dumps(m, indent=2))
