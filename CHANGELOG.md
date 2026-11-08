# Corpus Catalog Changelog

Release history for the `corpus-catalog` Python package and CLI.

## Unreleased

No unreleased changes.

## v0.3.1 - 2026-11-07

Validated against `corpus-spec` `v0.21`.

- The corpus URI's third segment is now the corpus **name**, not the
  tier (CORPUS-SPEC Spec epic `018-PROMOTE`, option A). A tier root is
  named after its tier as before (`corpus://cmikeb/work/hold` is the
  HOLD tier); a project promoted to a corpus of its own carries its own
  name (`corpus://iniate/github/cogent-agent-meta`) and declares its
  access tier with `corpus_spec_tier` alone. Owner, realm and node are
  still checked against both URIs, and the two URIs must name the same
  corpus. Identity and mount records gain a `name` field; aliases are
  built from the name (unchanged for tier roots).
- New validation warning `core-corpus-identity-name-not-tier` when a
  `tier-root` handbook's corpus URI names something other than its tier
  (previously a hard refusal of the whole root).
- `catalog mounts` prints `Corpus name:` for a named root.

## v0.3.0 - 2026-10-10

Validated against `corpus-spec` `v0.21`.

- Fixed BUG-001: the reference-subsection validator now honors
  `.corpusignore`, so ignored directories under `reference/` no longer
  produce `profile-reference-subsection-missing-entry` warnings.
- `catalog validate` now warns when the current mount is missing from
  the local mount registry, and `catalog status` reports registration
  state and suggests `catalog mounts --root <root>`.
- Bumped the validated `corpus-spec` release from `v0.20` to `v0.21`
  (`pyproject.toml` and the `corpus_catalog.release` runtime mirror).
- Install note: `scripts/install-catalog-release` reinstalls the stable
  `catalog` tool from the new wheel; `scripts/install-catalog-dev` keeps
  the source-backed `catalog-dev` wrapper.
- Added `catalog stats` for local corpus file/byte inventory, Markdown
  versus non-Markdown balance, Catalog-visible source counts, extension
  and directory summaries, largest-file reporting, `.corpusignore`
  coverage, Git-tracked status when available, and package-like
  `projects/*/code/*` awareness.
- Added `catalog health` for local operational health checks: large
  Git-tracked files, large local files, heavy visible directories,
  generated/dependency directory recommendations, source-code directory
  review recommendations, scheduled-run receipts, and configurable
  `--fail-on` exit behavior.
- Added optional mount placement metadata in the local mount registry
  (`storage_role`, `intent`, `preferred_for`, `avoid_for`, and
  large-file thresholds), preserved across mount re-registration and
  used only for health suggestions.
- Documented the split between `catalog validate` for corpus
  content/conformance and `catalog health` for local tooling,
  derived-data, search, sync, and mount-placement posture.

## v0.2.0 - 2026-06-10

- Added canonical `CORPUS.md`, `CORPUS-SPEC.md`, and
  `corpus_spec_*` support for the corpus naming cutover while keeping
  temporary read aliases for pre-cutover corpora.
- Changed generated `.corpus/` orientation to `.corpus/CORPUS.md`.
- Updated project-creation plans to scaffold `CORPUS.md` and report
  `corpus_spec_baseline`.
- Added duplicate-entry validation when `CORPUS.md` and a legacy entry
  file exist at the same scope.
- Added install scripts for stable `catalog` and source-backed
  `catalog-dev` commands.

## v0.1.0 - 2026-06-09

- First tagged Catalog release.
- Renamed the package and Python module to `corpus-catalog` /
  `corpus_catalog`.
- Validated against `corpus-spec` `v0.19`.
- Added `.corpus/` generated state, `.corpusignore`, corpus identity,
  mount registry, spec/profile module inventory, profile-aware context
  routing, source validation, lexical search, and read-only project
  creation planning.
- Added runtime release metadata through `catalog version`, generated
  manifests, and generated `.corpus/CORPUS.md`.
- Build artifact: Python wheel and source distribution from `uv build`.
