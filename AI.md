---
title: "AI.md - Catalog"
doc_type: ai-entry
ai_spec_version: v0.19
ai_spec_profile: project
ai_spec_adoption: partial
ai_spec_reviewed: 2026-06-03
ai_spec_betas: []
tag: personal
tier_composition: BRIEF
---

# AI.md - Catalog

Catalog is AI-SPEC's executable companion: a CLI-first tool for turning
AI-SPEC-shaped Markdown trees into queryable, source-cited corpora.

## Boundary

Catalog is tightly coupled to AI-SPEC but remains a separate codebase so
the lightweight `ai-spec/` source tree can still be pulled into projects
without Python tooling.

Catalog owns:

- corpus discovery;
- AI-SPEC version/profile/adoption parsing;
- source references;
- context packet assembly;
- deterministic validation;
- migration-aware conformance checks;
- CLI output suitable for humans and local AI tools.

Catalog does not own:

- normative AI-SPEC text;
- CANS deployments or adapters;
- persistent memory;
- MCP/gateway protocols as the primary product.

## Working Rules

- Keep the executable CLI as the primary product. Adapters should wrap
  the CLI or library, not replace it.
- When AI-SPEC changes, update Catalog selectors and validators in the
  same work cycle.
- Support mixed conformance. Validate each project against its declared
  baseline instead of forcing every project to the newest AI-SPEC
  immediately.
- Keep deterministic behavior useful without a model.
- Do not add write automation until patch, diff, approval, validation,
  apply, and report behavior is explicit.

## Current Surface

- `catalog init`
- `catalog index`
- `catalog status`
- `catalog context`
- `catalog search`
- `catalog validate`
- `catalog project new`

The Python module path is `ai_spec_catalog`.

## Verification

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run catalog context --root /Users/cmikeb/work/brief --cwd projects/spec --goal "Create a new project according to the local AI-SPEC baseline"
```
