#!/usr/bin/env python3
"""Locate rules or bounded text matches in the user's local standard PDF."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys


def default_pdf_path() -> str | None:
    configured = os.environ.get("ASD_STE100_PDF")
    if configured:
        return configured
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    local = codex_home / "standards/asd-ste100/ASD-STE100_ISSUE9.pdf"
    return str(local) if local.is_file() else None


def matches(text: str, query: str) -> list[re.Match]:
    """Match a literal phrase with flexible whitespace, never executable regex."""
    parts = query.strip().split()
    if not parts:
        raise ValueError("The search query cannot be empty.")
    pattern = r"\s+".join(re.escape(part) for part in parts)
    return list(re.finditer(pattern, text, flags=re.IGNORECASE))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", default=default_pdf_path())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rule", help="Rule locator, for example 5.1 (Issue 9 only).")
    mode.add_argument("--query", help="Literal text to locate; no approval is inferred.")
    parser.add_argument("--dictionary", action="store_true", help="Search part 2 only (Issue 9).")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--context", type=int, default=360)
    args = parser.parse_args(argv)
    if not args.pdf:
        parser.error("Set ASD_STE100_PDF or provide --pdf with an authorized local copy.")
    if not 1 <= args.limit <= 10 or not 80 <= args.context <= 1200:
        parser.error("Use --limit 1..10 and --context 80..1200.")
    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.is_file():
        parser.error("The local PDF was not found.")
    try:
        import pymupdf
    except ImportError:
        print("Optional PDF dependency missing. Install PyMuPDF or use another local reader.", file=sys.stderr)
        return 2
    try:
        with pymupdf.open(pdf_path) as doc:
            if doc.needs_pass:
                print("The PDF needs a password. Open it with your authorized local reader.", file=sys.stderr)
                return 2
            cover = " ".join((doc[0].get_text() + " " + doc[1].get_text()).split())
            issue9 = bool(re.search(r"ISSUE\s+9\b", cover, re.IGNORECASE))
            if (args.rule or args.dictionary) and not issue9:
                print("Issue 9 page locators cannot be applied to this PDF. Use --query or another reader.", file=sys.stderr)
                return 2
            if args.rule:
                locators = json.loads((Path(__file__).resolve().parents[1] / "references/issue9-locators.json").read_text(encoding="utf-8"))
                item = locators["rules"].get(args.rule)
                if not item:
                    parser.error("Unknown Issue 9 rule number.")
                page_no = item["explanation_pdf_page"]
                if page_no > len(doc):
                    raise ValueError("The PDF is too short for the recorded page locator.")
                text = doc[page_no - 1].get_text()
                found = matches(text, "Rule " + args.rule)
                if not found:
                    print("The PDF does not match the recorded locator. Read the rule manually.", file=sys.stderr)
                    return 2
                start = found[-1].start()
                excerpt = text[start : start + args.context]
                print(f"Rule {args.rule}: PDF page {page_no}; printed page {item['printed_page']}")
                print("Read the complete explanation and dictionary. This is a bounded local excerpt.")
                print(excerpt.strip())
                return 0
            start_page = 130 if args.dictionary else 0
            found_count = 0
            for index in range(start_page, len(doc)):
                text = doc[index].get_text()
                found = matches(text, args.query)
                if not found:
                    continue
                match = found[0]
                start = max(0, match.start() - args.context // 3)
                print(f"PDF page {index + 1}: search result, not an approval decision")
                print(text[start : start + args.context].strip())
                found_count += 1
                if found_count >= args.limit:
                    break
            if not found_count:
                print("No text match. Absence is not a conformance decision.")
                return 1
            return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Cannot read this local PDF: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
