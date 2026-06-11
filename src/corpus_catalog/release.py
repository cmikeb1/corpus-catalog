from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


PACKAGE_NAME = "corpus-catalog"
VALIDATED_CORPUS_SPEC_VERSION = "v0.20"


def catalog_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return "0.2.0"


def release_metadata() -> dict[str, str]:
    return {
        "catalog_version": catalog_version(),
        "validated_corpus_spec_version": VALIDATED_CORPUS_SPEC_VERSION,
    }
