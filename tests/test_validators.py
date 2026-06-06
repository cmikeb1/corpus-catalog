from __future__ import annotations

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.models import CorpusItem, SourceKind, SourceRef
from ai_spec_catalog.validators import validate_corpus


def item(
    path: str,
    kind: SourceKind,
    text: str = "# Test\n",
    front_matter: dict[str, object] | None = None,
) -> CorpusItem:
    return CorpusItem(
        source=SourceRef(path=path, kind=kind),
        title=path,
        front_matter=front_matter or {},
        text=text,
    )


def test_project_shell_pre_spec_does_not_require_overview(tmp_path):
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item(
            "AI.md",
            "handbook",
            front_matter={
                "ai_spec_version": "v0.18",
            },
        ),
        item(
            "projects/example/AI.md",
            "handbook",
            front_matter={
                "doc_type": "ai-entry",
                "ai_spec_version": "v0.18",
                "ai_spec_profile": "project-shell",
                "ai_spec_adoption": "pre-spec",
                "ai_spec_reviewed": "2026-06-06",
                "ai_spec_betas": [],
            },
        ),
    ]

    issues = validate_corpus(items, config)

    assert not any(issue.code == "project-missing-overview" for issue in issues)


def test_full_project_requires_overview(tmp_path):
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item(
            "AI.md",
            "handbook",
            front_matter={
                "ai_spec_version": "v0.18",
            },
        ),
        item(
            "projects/example/AI.md",
            "handbook",
            front_matter={
                "doc_type": "ai-entry",
                "ai_spec_version": "v0.18",
                "ai_spec_profile": "project",
                "ai_spec_adoption": "full",
                "ai_spec_reviewed": "2026-06-06",
                "ai_spec_betas": [],
            },
        ),
    ]

    issues = validate_corpus(items, config)

    assert any(issue.code == "project-missing-overview" for issue in issues)
