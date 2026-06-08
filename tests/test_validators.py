from __future__ import annotations

from ai_spec_catalog.corpus import load_corpus
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


def test_missing_corpusignore_warns_when_recommended_code_path_exists(tmp_path):
    code_readme = tmp_path / "projects" / "spec" / "code" / "catalog" / "README.md"
    code_readme.parent.mkdir(parents=True)
    code_readme.write_text("# Package README\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=tmp_path)

    issues = validate_corpus(load_corpus(config), config)

    assert any(issue.code == "corpusignore-missing" for issue in issues)


def test_corpusignore_warns_when_recommended_code_path_not_covered(tmp_path):
    code_readme = tmp_path / "projects" / "spec" / "code" / "catalog" / "README.md"
    code_readme.parent.mkdir(parents=True)
    code_readme.write_text("# Package README\n", encoding="utf-8")
    (tmp_path / ".corpusignore").write_text("# not enough yet\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=tmp_path)

    issues = validate_corpus(load_corpus(config), config)

    assert any(
        issue.code == "corpusignore-missing-recommended-rule" for issue in issues
    )


def test_corpusignore_recommended_rule_silences_code_path_warning(tmp_path):
    code_readme = tmp_path / "projects" / "spec" / "code" / "catalog" / "README.md"
    code_readme.parent.mkdir(parents=True)
    code_readme.write_text("# Package README\n", encoding="utf-8")
    (tmp_path / ".corpusignore").write_text(
        "projects/spec/code/catalog/\n",
        encoding="utf-8",
    )
    config = CatalogConfig(corpus_root=tmp_path)

    issues = validate_corpus(load_corpus(config), config)

    assert not any(issue.code.startswith("corpusignore-") for issue in issues)
