# Corpus Catalog Changelog

Release history for the `corpus-catalog` Python package and CLI.

## Unreleased

*(none)*

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
  manifests, and generated `.corpus/AI.md`.
- Build artifact: Python wheel and source distribution from `uv build`.
