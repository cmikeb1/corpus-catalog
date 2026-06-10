from importlib.metadata import version
from pathlib import Path
import tomllib

from corpus_catalog.release import (
    PACKAGE_NAME,
    VALIDATED_CORPUS_SPEC_VERSION,
    catalog_version,
)


def test_release_metadata_matches_pyproject():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == PACKAGE_NAME
    assert catalog_version() == pyproject["project"]["version"]
    assert version(PACKAGE_NAME) == pyproject["project"]["version"]
    assert (
        VALIDATED_CORPUS_SPEC_VERSION
        == pyproject["tool"]["corpus-catalog"]["release"]["validated-corpus-spec"]
    )
