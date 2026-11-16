---
name: asd-ste100
description: Draft, revise, explain, or review technical documentation using ASD-STE100 Simplified Technical English. Use for STE requests, controlled technical language, maintenance procedures, and explicit ASD-STE100 reviews. Do not impose its vocabulary on unrelated conversational, literary, or marketing writing.
---

# ASD-STE100 technical English

Help the reader understand and use technical information without changing its
meaning. This is an independent assistant skill, not the standard or a certification.

## Select the reference and task

Use the user's requested edition. Otherwise check the current edition through the
[official downloads](https://www.asd-ste100.org/STE_downloads.html) and
[FAQ](https://www.asd-ste100.org/STE_faq.html). This skill was checked against
Issue 9, 2025-01-15, on 2026-11-16. Do not silently combine editions. Old official
pages such as `about.html`, `faq.html`, and `request.html` still discuss Issue 8.

Identify whether the input contains procedures, descriptions, safety instructions,
or a mixture. Use the applicable reference sections for each passage. Ask only
for facts or requirements needed to resolve a consequential ambiguity.

- For drafting or revising, read [the writing guide](references/writing-guide.md).
- For an audit, vocabulary decision, or conformance request, also read
  [the verification workflow](references/verification.md).
- For source discovery or a source conflict, read [the source guide](references/sources.md).

Use a lawful local copy of the requested standard and the project's terminology
records for detailed decisions. Read relevant rule explanations and dictionary
entries, not just a rule heading or search hit. If the PDF is available, the
optional local helper can locate it:

```text
python <skill-dir>/scripts/lookup_standard.py --pdf <local-pdf> --rule 5.1
python <skill-dir>/scripts/lookup_standard.py --pdf <local-pdf> --query <term> --dictionary
```

`ASD_STE100_PDF` can supply the PDF path instead. The helper also detects a private
copy at `$CODEX_HOME/standards/asd-ste100/ASD-STE100_ISSUE9.pdf`, using `~/.codex`
when CODEX_HOME is unset. The helper needs PyMuPDF. Other
local PDF readers are valid alternatives. Do not require that package merely to
use the skill. Search output is local reference material, not public repository content.

## Preserve the technical information

Before editing, identify the actions, their actors and objects, prerequisites,
dependencies, values, units, tolerances, references, labels, and hazards. Keep
negation, modality, exceptions, simultaneous actions, and uncertainty intact.
Never invent a missing limit, tool, permission, sequence, or safety consequence.

Split a complicated sentence only after checking which conditions govern each
action. Keep an exact interface label or identifier recognizable. Record a label
as such instead of replacing it with a preferred general word. When shortening a
technical noun, establish its meaning and preserve traceability to the full name.

Do not convert a suggestion into a command, a possibility into a certainty, or a
description into an instruction. If the source is technically inconsistent,
identify the conflict rather than silently choosing a new procedure.

## Apply and verify

Revise sentence structure and terminology together. A mechanical synonym swap,
short sentence, readability score, or dictionary hit does not establish correctness.
For vocabulary decisions verify the intended meaning, part of speech, and allowed
form in the applicable edition. For technical nouns and verbs, record the project
term source and the applicable category. Do not turn every unknown word into a
technical term to bypass the dictionary.

Treat surface checks as review aids. Word counting must follow the edition's
counting rules. Do not present whitespace token counts, suffix matching, passive
voice heuristics, or an AI score as a conformance result.

Compare the finished text with the source information before delivery. For a
source-based review, give useful rule/page references and unresolved items.
The locator table in [issue9-locators.json](references/issue9-locators.json)
contains page locations, not a substitute for the rule explanations.

If the standard or dictionary is unavailable, continue with a useful rewrite and
call it a **principles-only draft; vocabulary and full rule conformance not verified**.
If only some checks were possible, name their scope and the remaining checks.
Never claim that ASD approved this skill or that AI output is certified.

## Deliver to the requested scope

For a rewrite, lead with the revised text. Add only material unresolved questions
and a brief verification status. For an audit, give a compact table with location,
finding, reference, proposed correction, and unresolved evidence as needed.
For an explanation, link the primary sources and distinguish project advice from
the standard. Keep detailed ledgers only when the task needs them.

Protect private documents and local source extracts. Do not upload, publish, or
commit them as part of an ordinary writing task. See
[the source guide](references/sources.md) for the official reuse and tools notices.
