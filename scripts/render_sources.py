#!/usr/bin/env python3
"""Render the reviewed source catalog as a readable Markdown inventory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(catalog: dict) -> str:
    sources = catalog["sources"]
    monitored = sum(bool(item.get("monitor")) for item in sources)
    lines = [
        "# Source and documentation index", "",
        f"Research date: **{catalog['researched_on']}**. **{len(sources)} sources**, including **{monitored} monitored sources**.", "",
        catalog["scope"], "",
        "## What was checked", "",
        "All 11 HTML locations in the official sitemap were retrieved, along with the",
        "official Issue 9 PDF, current AI paper, and Zenodo metadata. Relevant rule",
        "explanations and the copyright page were inspected. Linked forms were identified",
        "but not submitted. Protected publications are not reproduced in this project.", "",
        "The active standard is Issue 9, dated 2025-01-15. The current FAQ schedules",
        "Issue 10 for January 2028. Legacy official pages still call Issue 8 current.",
        "Use edition-specific evidence rather than a site's domain alone.", "",
        "The concept DOI 10.5281/zenodo.23666005 resolved to the Issue 9 version record",
        "10.5281/zenodo.23666006. The October 2026 deposit date is separate from the",
        "standard's January 2025 publication date. The official FAIR explanation preserves",
        "the standard's copyright and special usage rights alongside the Zenodo license.", "",
        "## Verification labels", "",
        "- `direct-content`: publication or page content inspected in this research.",
        "- `direct-metadata`: authoritative bibliographic API metadata inspected.",
        "- `direct-retrieval`: endpoint returned a file/page, without a full content review.",
        "- `publisher-search`: publisher's own search-index record supports discovery; full text not verified.",
        "- `link-discovery`: link found on an inspected official page; target contents not verified.",
        "- `bibliography-only`: citation from Issue 9 with a publisher entrypoint; exact edition not verified.",
        "- `search-discovery`: community work surfaced in search; claims and behavior not verified.", "",
        "Monitored means included in the automated retrieval and hash check. It does not",
        "mean that every claim on the page has been independently validated. All entries",
        "are links and metadata, under their publishers' separate rights.", "",
    ]
    for category in dict.fromkeys(item["category"] for item in sources):
        lines.extend(["## " + category.replace("-", " ").title(), "", "| ID and source | Status and access evidence | Daily monitor | Purpose and limits |", "| --- | --- | --- | --- |"])
        for item in sources:
            if item["category"] != category:
                continue
            title = item["title"].replace("|", "\\|")
            notes = item["notes"].replace("|", "\\|")
            lines.append(f"| `{item['id']}`: [{title}]({item['url']}) | {item['status']}; {item['verification']} | {'Yes' if item['monitor'] else 'No'} | {notes} |")
        lines.append("")
    lines.extend([
        "## Coverage limits and open questions", "",
        "This inventory covers the public official surface and a curated surrounding",
        "bibliography. It cannot exhaust every paper, translation, vendor document, private",
        "course, contract, or internet mention. Search snippets and community repositories",
        "are discovery evidence, never substitutes for rule and dictionary verification.", "",
        "The Issue 9 bibliography contains edition/date details that do not exactly match",
        "some publisher records, including Gregg, GPO, the UN guide, and Kirkman. Those",
        "differences remain explicit in the table. Publisher homepages are identified as",
        "entrypoints, rather than invented direct links to an unverified edition.", "",
        "No general statement here establishes which aviation, defense, legal, or contract",
        "requirements apply to a particular organization. Verify the relevant instruments",
        "and editions for that task. No courses, standards, or vendor subscriptions were purchased.", "",
        "Edit sources/catalog.json and run `python scripts/render_sources.py` to update this",
        "index. Source-change acceptance is a separate step described in MAINTENANCE.md.", "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    catalog = json.loads((ROOT / "sources/catalog.json").read_text(encoding="utf-8"))
    output = render(catalog)
    path = ROOT / "docs/SOURCES.md"
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != output:
            print("Source index is stale. Run python scripts/render_sources.py.")
            return 1
        print("Source index matches catalog.")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        print(f"Rendered {len(catalog['sources'])} source entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
