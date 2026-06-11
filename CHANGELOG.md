# Corpus Catalog Changelog

Release history for the `corpus-catalog` Python package and CLI.

## Unreleased

- Nothing yet.

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
