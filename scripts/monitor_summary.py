#!/usr/bin/env python3
"""Write a GitHub Actions summary containing reviewed IDs and counts only."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
report_path = ROOT / ".local/source-report.json"
if report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))
    lines = [
        "## Official source status", "",
        f"Checked: {report['checked_sources']}. Changed: {len(report['changes'])}. Errors: {len(report['errors'])}. New URLs: {len(report['discovered_urls'])}.", "",
    ]
    for item in report["changes"]:
        lines.append(f"- Changed source: `{item['id']}` ({item['change']}).")
    for item in report["errors"]:
        lines.append(f"- Retrieval failed: `{item['id']}`. Check the metadata report.")
    lines.extend(["", "Review changes with docs/MAINTENANCE.md before accepting a new baseline.", ""])
else:
    lines = ["Source check did not produce a metadata report. Inspect the job log.", ""]
summary = "\n".join(lines)
destination = os.environ.get("GITHUB_STEP_SUMMARY")
if destination:
    with open(destination, "a", encoding="utf-8") as handle:
        handle.write(summary)
else:
    print(summary)
