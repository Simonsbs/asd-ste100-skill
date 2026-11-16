# ASD-STE100 skill for Codex

An independent, open-source Codex skill for drafting, revising, and reviewing
technical English with ASD-STE100 as its reference. It supports a source-based
review and a clearly labeled principles-only rewrite when the standard is absent.

**Reference edition:** Issue 9, 2025-01-15. **Research date:** 2026-11-16.
The current official FAQ schedules Issue 10 for January 2028; a schedule is not a
published edition. [Official FAQ](https://www.asd-ste100.org/STE_faq.html)

The skill does not contain the standard or its dictionary and cannot certify
conformance. See [NOTICE.md](NOTICE.md) for the separate rights in linked sources.

## Install in Codex

Ask Codex with its skill-installer available:

> Install the asd-ste100 skill from Simonsbs/asd-ste100-skill, path skills/asd-ste100.

Or use the installer bundled with Codex, adjusting its location if necessary:

```powershell
python "$env:USERPROFILE/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py" --repo Simonsbs/asd-ste100-skill --path skills/asd-ste100
```

The default destination is `$CODEX_HOME/skills/asd-ste100`, or
`~/.codex/skills/asd-ste100` if CODEX_HOME is unset. The installer refuses to
overwrite an existing installation. The skill is available on your next turn.

To maintain a local checkout and its installed copy:

```powershell
git clone https://github.com/Simonsbs/asd-ste100-skill.git
cd asd-ste100-skill
python scripts/sync_install.py --adopt
```

Adoption requires the installed copy to match this checkout exactly. Later,
update the checkout and run `python scripts/sync_install.py`. Locally edited skill
files are preserved by refusing the update. See [maintenance](docs/MAINTENANCE.md).

## Use

```text
Use $asd-ste100 to rewrite this maintenance procedure. Preserve all facts,
conditions, limits, labels, and work-step dependencies. Identify unresolved terms.

Use $asd-ste100 to review this description against my local Issue 9 PDF and
project glossary. Give rule references and distinguish findings from uncertainty.

Use $asd-ste100 to explain the standard and locate official documentation.
```

For detailed verification, obtain a copy through the
[official downloads page](https://www.asd-ste100.org/STE_downloads.html) or
[official DOI](https://doi.org/10.5281/zenodo.23666005). Keep it outside the skill and
repository. The optional local search helper needs Python 3.10+ and PyMuPDF:

```powershell
python -m pip install -r requirements-pdf.txt
$env:ASD_STE100_PDF = 'C:/Private/Standards/ASD-STE100_ISSUE9.pdf'
python skills/asd-ste100/scripts/lookup_standard.py --rule 5.1
python skills/asd-ste100/scripts/lookup_standard.py --query 'CHECK' --dictionary --limit 3
```

The helper prints page locations and bounded local excerpts. It does not infer
approval from a search hit, build a dictionary, upload content, or save extracts.
Keep the PDF and its output out of public issues and commits.

For automatic local discovery, place your authorized Issue 9 copy at
`$CODEX_HOME/standards/asd-ste100/ASD-STE100_ISSUE9.pdf`, or
`~/.codex/standards/asd-ste100/ASD-STE100_ISSUE9.pdf` when CODEX_HOME is unset.
An explicit `--pdf` or `ASD_STE100_PDF` setting takes priority.

## Sources and updates

[The source index](docs/SOURCES.md) inventories the official sitemap, current
standard and supporting materials, related publishers, research, historical pages,
and selected community implementations. It records the search scope and gaps.
It is not a claim to have found every mention on the internet.

- `sources/catalog.json`: source identities, authority, access, and monitoring scope.
- `sources/baseline.json`: reviewed hashes and public retrieval metadata.
- `python scripts/check_sources.py`: checks the monitored sources and reports changes.
- A daily GitHub Actions job detects changes and access failures, with a bounded
  metadata report retained for seven days. It does not alter the skill itself.
- A weekly Codex review can verify changes, update original guidance, run checks,
  publish this repository, and synchronize the locally installed skill. This is
  enabled separately in the maintainer's Codex app, not installed for every user.

```powershell
python scripts/check_sources.py --fail-on-change
python scripts/validate_project.py
python -m unittest discover -s tests -v
```

The monitor uses Python's standard library. PDF lookup is optional and separate.
See [maintenance instructions](docs/MAINTENANCE.md),
[evaluation cases](docs/EVALUATION.md), and [contribution guidance](CONTRIBUTING.md).
