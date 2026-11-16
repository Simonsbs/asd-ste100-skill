#!/usr/bin/env python3
"""Validate skill metadata, local links, source coverage and public file boundaries."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

from check_sources import canonical_url, load_catalog
from render_sources import render

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/asd-ste100"
EXCLUDED = {".git", ".local", ".venv", "__pycache__"}


def project_files() -> list[Path]:
    return [path for path in ROOT.rglob("*") if path.is_file() and not any(part in EXCLUDED for part in path.relative_to(ROOT).parts)]


def validate() -> list[str]:
    import yaml

    errors = []
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        errors.append("Missing skill frontmatter.")
    else:
        metadata = yaml.safe_load(text.split("---", 2)[1])
        if metadata.get("name") != "asd-ste100" or not metadata.get("description"):
            errors.append("Skill name or description is invalid.")
    ui = yaml.safe_load((SKILL / "agents/openai.yaml").read_text(encoding="utf-8"))
    if "$asd-ste100" not in ui.get("interface", {}).get("default_prompt", ""):
        errors.append("UI prompt does not identify the skill.")
    if ui.get("policy", {}).get("allow_implicit_invocation") is False:
        errors.append("Automatic skill selection was unexpectedly disabled.")
    version = (SKILL / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or f"## {version} -" not in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"):
        errors.append("Version and changelog do not agree.")
    catalog = load_catalog(ROOT / "sources/catalog.json")
    urls = [canonical_url(item["url"]) for item in catalog["sources"]]
    if len(urls) != len(set(urls)):
        errors.append("Duplicate source URLs after canonicalization.")
    baseline = json.loads((ROOT / "sources/baseline.json").read_text(encoding="utf-8"))
    expected = {item["id"] for item in catalog["sources"] if item.get("monitor")}
    if set(baseline["sources"]) != expected:
        errors.append("Baseline does not cover exactly the monitored sources.")
    for key, entry in baseline["sources"].items():
        if not re.fullmatch(r"[a-f0-9]{64}", entry.get("sha256", "")) or entry.get("status") != 200:
            errors.append(f"Invalid successful baseline: {key}")
        if set(entry) - {"status", "sha256", "bytes", "kind", "content_type", "final_url"}:
            errors.append(f"Baseline contains unexpected publication fields: {key}")
    if (ROOT / "docs/SOURCES.md").read_text(encoding="utf-8") != render(catalog):
        errors.append("Rendered source index is stale.")
    locators = json.loads((SKILL / "references/issue9-locators.json").read_text(encoding="utf-8"))
    counts = {1: 14, 2: 2, 3: 7, 4: 5, 5: 5, 6: 6, 7: 3, 8: 7, 9: 4}
    expected_rules = {f"{section}.{number}" for section, count in counts.items() for number in range(1, count + 1)}
    if set(locators["rules"]) != expected_rules:
        errors.append("Rule locator inventory is incomplete.")
    for rule, locator in locators["rules"].items():
        if not 45 <= locator["summary_pdf_page"] <= locator["explanation_pdf_page"] <= 127:
            errors.append(f"Rule page locator out of range: {rule}")
    for path in project_files():
        relative = path.relative_to(ROOT)
        if path.suffix.lower() in {".pdf", ".docx", ".zip"} or path.name.startswith(".env"):
            errors.append(f"Protected or private file in public tree: {relative}")
            continue
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"Unexpected binary in public tree: {relative}")
            continue
        if chr(0x2014) in contents:
            errors.append(f"Disallowed punctuation in {relative}")
        if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-proj-[A-Za-z0-9_-]{25,})", contents):
            errors.append(f"Potential credential in {relative}")
        if path.suffix.lower() == ".md":
            for target in re.findall(r"\]\(([^)\s]+)\)", contents):
                if target.startswith(("http:", "https:", "mailto:", "#")):
                    continue
                local = target.split("#", 1)[0]
                if local and not (path.parent / local).exists():
                    errors.append(f"Broken local link in {relative}: {target}")
    return errors


def main() -> int:
    try:
        errors = validate()
    except ImportError:
        print("Install validation dependencies with python -m pip install -r requirements-dev.txt.", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError) as exc:
        print(f"Project validation failed: {exc}", file=sys.stderr)
        return 1
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        return 1
    print("Project valid: skill metadata, 53 locators, sources, links, and public file boundaries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
