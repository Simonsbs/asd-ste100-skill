#!/usr/bin/env python3
"""Check reviewed public sources without retaining their publication content."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 8 * 1024 * 1024
USER_AGENT = "asd-ste100-skill-source-monitor/0.1 (+https://github.com/Simonsbs/asd-ste100-skill)"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_url(url: str) -> str:
    parts = urlsplit(urldefrag(url)[0])
    host = (parts.hostname or "").lower()
    if host in {"asd-ste100.org", "www.asd-ste100.org"}:
        path = parts.path or "/"
        if path == "/index.html":
            path = "/"
        return "https://www.asd-ste100.org" + path
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


class SemanticHTML(HTMLParser):
    EXCLUDED = {"script", "style", "nav", "footer", "noscript"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.skip = 0
        self.text: list[str] = []
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.EXCLUDED:
            self.skip += 1
        href = dict(attrs).get("href") if tag == "a" else None
        if href:
            link = urljoin(self.base_url, href)
            if urlsplit(link).scheme in {"http", "https"}:
                self.links.add(canonical_url(link))

    def handle_endtag(self, tag: str) -> None:
        if tag in self.EXCLUDED:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, data: str) -> None:
        if not self.skip and data.strip():
            self.text.append(data.strip())


def fingerprint(data: bytes, kind: str, url: str) -> tuple[str, list[str]]:
    """Hash stable content; only return hashes and discovered links, never text."""
    links: list[str] = []
    if kind == "html":
        parser = SemanticHTML(url)
        parser.feed(data.decode("utf-8", errors="replace"))
        links = sorted(parser.links)
        payload = {"text": re.sub(r"\s+", " ", " ".join(parser.text)).strip(), "links": links}
    elif kind == "sitemap":
        tree = ET.fromstring(data)
        links = sorted({canonical_url(item.text.strip()) for item in tree.iter() if item.tag.endswith("}loc") and item.text})
        payload = {"locations": links}
    elif kind == "json":
        record = json.loads(data)
        metadata = record.get("metadata", {})
        # Zenodo download counts, signed URLs and API modification times are not edition changes.
        payload = {
            "id": record.get("id"),
            "doi": record.get("doi"),
            "metadata": {key: metadata.get(key) for key in (
                "title", "publication_date", "version", "license", "access_right",
                "relations", "notes", "keywords", "alternate_identifiers",
            )},
            "files": sorted(
                ({key: item.get(key) for key in ("key", "size", "checksum")} for item in record.get("files", [])),
                key=lambda item: item.get("key") or "",
            ),
        }
    elif kind == "binary":
        return hashlib.sha256(data).hexdigest(), links
    else:
        raise ValueError(f"Unsupported source kind: {kind}")
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest(), links


def load_catalog(path: Path) -> dict:
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("sources"), list):
        raise ValueError("Unsupported source catalog schema.")
    ids: set[str] = set()
    for source in catalog["sources"]:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source.get("id", "")) or source["id"] in ids:
            raise ValueError("Source IDs must be unique lowercase identifiers.")
        ids.add(source["id"])
        parts = urlsplit(source["url"])
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ValueError(f"Source {source['id']} must have a public HTTPS URL without credentials.")
        if source.get("monitor") and source.get("kind") not in {"html", "sitemap", "json", "binary"}:
            raise ValueError(f"Unsupported monitored source kind: {source['id']}")
    return catalog


def fetch_source(source: dict, timeout: float = 20) -> dict:
    url = source["url"]
    for attempt in range(2):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urlopen(request, timeout=timeout) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ValueError("Response exceeds the monitor's 8 MiB limit.")
                content_type = response.headers.get_content_type()
                kind = source["kind"]
                if kind == "binary" and urlsplit(url).path.lower().endswith(".pdf") and not data.startswith(b"%PDF-"):
                    raise ValueError("A PDF URL returned non-PDF content.")
                if kind == "binary" and urlsplit(url).path.lower().endswith(".docx") and not data.startswith(b"PK"):
                    raise ValueError("A DOCX URL returned non-ZIP content.")
                if kind == "html" and ("html" not in content_type or not data.strip()):
                    raise ValueError("An HTML source returned an unexpected or empty body.")
                digest, links = fingerprint(data, kind, response.geturl())
                return {
                    "ok": True, "status": response.status,
                    "sha256": digest, "bytes": len(data), "kind": kind,
                    "content_type": content_type, "final_url": response.geturl(),
                    "links": links,
                }
        except HTTPError as exc:
            error = f"HTTP {exc.code}"
            if exc.code not in {429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError, OSError, ValueError, ET.ParseError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        if attempt == 1:
            break
    return {"ok": False, "error": error}


def build_report(catalog: dict, baseline: dict, results: dict[str, dict]) -> dict:
    before = baseline.get("sources", {})
    expected = {item["id"] for item in catalog["sources"] if item.get("monitor")}
    known_urls = {canonical_url(item["url"]) for item in catalog["sources"]}
    changes: list[dict] = []
    errors: list[dict] = []
    discovered: set[str] = set()
    for source_id, current in sorted(results.items()):
        if not current["ok"]:
            errors.append({"id": source_id, "error": current["error"]})
            continue
        prior = before.get(source_id)
        if not prior:
            changes.append({"id": source_id, "change": "new-source", "new_sha256": current["sha256"]})
        elif prior.get("sha256") != current["sha256"] or prior.get("final_url") != current["final_url"]:
            changes.append({"id": source_id, "change": "content-or-location", "old_sha256": prior.get("sha256"), "new_sha256": current["sha256"]})
        for link in current.get("links", []):
            parts = urlsplit(link)
            if parts.hostname == "www.asd-ste100.org" and link not in known_urls:
                if parts.path.endswith((".html", ".pdf", ".docx")) or parts.path == "/":
                    discovered.add(link)
    for source_id in sorted(set(before) - expected):
        changes.append({"id": source_id, "change": "removed-from-monitoring"})
    return {
        "schema_version": 1, "checked_at": utc_now(),
        "checked_sources": len(results), "changes": changes, "errors": errors,
        "discovered_urls": sorted(discovered),
        "sources": results,
        "has_changes": bool(changes or discovered),
    }


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def accept_report(report: dict, path: Path) -> None:
    if report["errors"]:
        raise ValueError("Cannot accept a baseline while any source retrieval failed.")
    if report["discovered_urls"]:
        raise ValueError("Classify discovered official URLs in the catalog before accepting a baseline.")
    # Publication text is not stored. Links are retained only in the temporary report.
    sources = {
        source_id: {key: value for key, value in result.items() if key not in {"links", "ok"}}
        for source_id, result in sorted(report["sources"].items())
    }
    save_json(path, {"schema_version": 1, "fingerprint_version": 1, "reviewed_at": report["checked_at"], "sources": sources})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "sources/catalog.json")
    parser.add_argument("--baseline", type=Path, default=ROOT / "sources/baseline.json")
    parser.add_argument("--report", type=Path, default=ROOT / ".local/source-report.json")
    parser.add_argument("--accept", action="store_true", help="Explicitly acknowledge reviewed source changes.")
    parser.add_argument("--fail-on-change", action="store_true")
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog(args.catalog)
        baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline.exists() else {"sources": {}}
        if baseline.get("fingerprint_version", 1) != 1:
            raise ValueError("Unsupported fingerprint version; review the migration before replacing the baseline.")
        monitored = [item for item in catalog["sources"] if item.get("monitor")]
        if not monitored:
            raise ValueError("The catalog has no monitored sources.")
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = dict(zip((item["id"] for item in monitored), pool.map(fetch_source, monitored)))
        report = build_report(catalog, baseline, results)
        save_json(args.report, report)
        print(f"Checked {report['checked_sources']} sources: {len(report['changes'])} changed, {len(report['errors'])} errors, {len(report['discovered_urls'])} discovered URLs.")
        for item in report["changes"]:
            print(f"CHANGE {item['id']}: {item['change']}")
        for item in report["errors"]:
            print(f"ERROR {item['id']}: {item['error']}", file=sys.stderr)
        for url in report["discovered_urls"]:
            print(f"DISCOVERED {url}")
        if args.accept:
            accept_report(report, args.baseline)
            print("Reviewed metadata baseline saved.")
        if report["errors"]:
            return 2
        return 1 if report["has_changes"] and args.fail_on_change and not args.accept else 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"Source check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
