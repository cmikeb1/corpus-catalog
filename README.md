---
component_type: integration
component_id: catalog
status: prototype
maturity: prototype
adapters: []
deployments: []
---

# Catalog Integration

Catalog is the harness-neutral CANS integration for making Mike's
tiered Markdown corpus usable by agents and local models.

The source corpus remains Markdown plus Git. Catalog builds the
derived, queryable layer over that corpus: source references, parsed
front matter, lightweight indexes, context packets, and cheap
validation reports.

## Name And Boundary

`STATE` was the epic name. `catalog` is the integration name.

The distinction matters:

- **Corpus** is the canonical source material: AI-SPEC, project docs,
  registries, reference notes, and later tier-specific records.
- **Catalog** is the reproducible map over the corpus: inventory,
  search, validation, and source-cited context assembly.
- **Librarian** can be an agent, persona, or adapter that uses Catalog.
  It should not be the deterministic core.
- **Memory** remains separate. Catalog may expose memory metadata later,
  but durable learned recall belongs to CANS MEM.

Catalog is read-only in its first prototype. Write workflows should
arrive later as explicit patch proposals followed by validation, diff,
approval, apply, re-index, and report.

## First Surface

The initial deterministic surface is:

- discover relevant Markdown sources under a corpus root;
- parse simple YAML-style front matter from `AI.md`, component
  READMEs, registries, overviews, and task files;
- search corpus items lexically;
- assemble a source-cited context packet for a goal and cwd;
- run cheap validation checks, starting with root handbook presence and
  active epic bookmark checks.

This intentionally does not require an LLM. A Pydantic AI wrapper can
sit on top once the deterministic pieces are boring and tested.

## CLI

From this directory:

```bash
python -m cans_catalog.cli context \
  --root ../../.. \
  --cwd projects/cans/assets/epics/004-STATE \
  --goal "I am implementing the corpus catalog integration"
```

Search:

```bash
python -m cans_catalog.cli search --root ../../.. --query "context packet"
```

Validate:

```bash
python -m cans_catalog.cli validate --root ../../..
```

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

The package currently depends on Pydantic for boundary models and uses
the Python standard library for discovery, parsing, search, and CLI.
