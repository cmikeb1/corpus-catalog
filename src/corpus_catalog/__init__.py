"""CORPUS-SPEC Catalog CLI and library surface."""

from corpus_catalog.config import CatalogConfig
from corpus_catalog.context import build_context_packet
from corpus_catalog.corpus import load_corpus, search_corpus
from corpus_catalog.models import (
    CatalogQuery,
    CorpusIdentity,
    ContextItem,
    ContextPacket,
    CorpusItem,
    CorpusMount,
    KnownCorpusMount,
    MountInventory,
    MountSyncStatus,
    SourceRef,
    ValidationIssue,
)
from corpus_catalog.release import (
    VALIDATED_CORPUS_SPEC_VERSION,
    catalog_version,
    release_metadata,
)

__all__ = [
    "CatalogConfig",
    "CatalogQuery",
    "ContextItem",
    "ContextPacket",
    "CorpusIdentity",
    "CorpusItem",
    "CorpusMount",
    "KnownCorpusMount",
    "MountInventory",
    "MountSyncStatus",
    "SourceRef",
    "ValidationIssue",
    "VALIDATED_CORPUS_SPEC_VERSION",
    "build_context_packet",
    "catalog_version",
    "load_corpus",
    "release_metadata",
    "search_corpus",
]
