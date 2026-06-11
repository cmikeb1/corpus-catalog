from __future__ import annotations

from corpus_catalog.corpus import load_corpus
from corpus_catalog.config import CatalogConfig
from corpus_catalog.models import CorpusItem, SourceKind, SourceRef
from corpus_catalog.naming import LEGACY_ENTRY_DOC_TYPE, LEGACY_ENTRY_FILENAME, legacy_field
from corpus_catalog.validators import validate_corpus


def issue_codes(items, config: CatalogConfig) -> set[str]:
    return {issue.code for issue in validate_corpus(items, config)}


def ai_front_matter(
    profile: str = "root",
    adoption: str = "full",
) -> dict[str, object]:
    return {
        "doc_type": "corpus-entry",
        "corpus_spec_version": "v0.18",
        "corpus_spec_profile": profile,
        "corpus_spec_adoption": adoption,
        "corpus_spec_reviewed": "2026-06-08",
        "corpus_spec_betas": [],
    }


def legacy_front_matter(
    profile: str = "root",
    adoption: str = "full",
) -> dict[str, object]:
    return {
        "doc_type": LEGACY_ENTRY_DOC_TYPE,
        legacy_field("version"): "v0.18",
        legacy_field("profile"): profile,
        legacy_field("adoption"): adoption,
        legacy_field("reviewed"): "2026-06-08",
        legacy_field("betas"): [],
    }


def corpus_front_matter(
    profile: str = "root",
    adoption: str = "full",
) -> dict[str, object]:
    return {
        "doc_type": "corpus-entry",
        "corpus_spec_version": "v0.20",
        "corpus_spec_profile": profile,
        "corpus_spec_adoption": adoption,
        "corpus_spec_reviewed": "2026-06-10",
        "corpus_spec_betas": [],
    }


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
            "CORPUS.md",
            "handbook",
            front_matter=ai_front_matter(),
        ),
        item(
            "projects/example/CORPUS.md",
            "handbook",
            front_matter=ai_front_matter(
                profile="project-shell",
                adoption="pre-spec",
            ),
        ),
    ]

    codes = issue_codes(items, config)

    assert "profile-project-missing-overview" not in codes


def test_full_project_requires_overview(tmp_path):
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item(
            "CORPUS.md",
            "handbook",
            front_matter=ai_front_matter(),
        ),
        item(
            "projects/example/CORPUS.md",
            "handbook",
            front_matter=ai_front_matter(profile="project"),
        ),
    ]

    codes = issue_codes(items, config)

    assert "profile-project-missing-overview" in codes


def test_project_corpus_entry_requires_overview(tmp_path):
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item("corpus.md", "handbook", front_matter=ai_front_matter()),
        item(
            "projects/example/corpus.md",
            "handbook",
            front_matter=ai_front_matter(profile="project"),
        ),
    ]

    codes = issue_codes(items, config)

    assert "profile-project-missing-overview" in codes


def test_missing_corpusignore_warns_when_recommended_code_path_exists(tmp_path):
    code_readme = (
        tmp_path / "projects" / "spec" / "code" / "corpus-catalog" / "README.md"
    )
    code_readme.parent.mkdir(parents=True)
    code_readme.write_text("# Package README\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=tmp_path)

    issues = validate_corpus(load_corpus(config), config)

    assert any(issue.code == "core-corpusignore-missing" for issue in issues)


def test_corpusignore_warns_when_recommended_code_path_not_covered(tmp_path):
    code_readme = (
        tmp_path / "projects" / "spec" / "code" / "corpus-catalog" / "README.md"
    )
    code_readme.parent.mkdir(parents=True)
    code_readme.write_text("# Package README\n", encoding="utf-8")
    (tmp_path / ".corpusignore").write_text("# not enough yet\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=tmp_path)

    issues = validate_corpus(load_corpus(config), config)

    assert any(
        issue.code == "core-corpusignore-missing-recommended-rule"
        for issue in issues
    )


def test_corpusignore_recommended_rule_silences_code_path_warning(tmp_path):
    code_readme = tmp_path / "projects" / "spec" / "code" / "catalog" / "README.md"
    code_readme.parent.mkdir(parents=True)
    code_readme.write_text("# Package README\n", encoding="utf-8")
    (tmp_path / ".corpusignore").write_text(
        "projects/spec/code/corpus-catalog/\n",
        encoding="utf-8",
    )
    config = CatalogConfig(corpus_root=tmp_path)

    issues = validate_corpus(load_corpus(config), config)

    assert not any(issue.code.startswith("core-corpusignore-") for issue in issues)


def test_core_validator_accepts_corpus_root_entry(tmp_path):
    config = CatalogConfig(corpus_root=tmp_path)
    items = [item("CORPUS.md", "handbook", front_matter=corpus_front_matter())]

    codes = issue_codes(items, config)

    assert "core-missing-root-handbook" not in codes
    assert "core-corpus-entry-missing-frontmatter" not in codes


def test_core_validator_accepts_legacy_root_entry(tmp_path):
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item(
            LEGACY_ENTRY_FILENAME,
            "handbook",
            front_matter=legacy_front_matter(),
        )
    ]

    codes = issue_codes(items, config)

    assert "core-missing-root-handbook" not in codes


def test_core_validator_warns_on_duplicate_canonical_and_legacy_entry(tmp_path):
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item("CORPUS.md", "handbook", front_matter=corpus_front_matter()),
        item(
            LEGACY_ENTRY_FILENAME,
            "handbook",
            front_matter=legacy_front_matter(),
        ),
    ]

    codes = issue_codes(items, config)

    assert "core-corpus-entry-duplicate-legacy" in codes


def test_workspace_profile_warns_for_missing_workspace_files(tmp_path):
    (tmp_path / "workspace").mkdir()
    config = CatalogConfig(corpus_root=tmp_path)
    items = [item("CORPUS.md", "handbook", front_matter=ai_front_matter())]

    codes = issue_codes(items, config)

    assert "profile-workspace-missing-kanban" in codes
    assert "profile-workspace-missing-inbox" in codes


def test_workspace_profile_accepts_required_workspace_files(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "kanban.md").write_text("# Kanban\n", encoding="utf-8")
    (workspace / "inbox.md").write_text("# Inbox\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=tmp_path)
    items = [item("CORPUS.md", "handbook", front_matter=ai_front_matter())]

    codes = issue_codes(items, config)

    assert "profile-workspace-missing-kanban" not in codes
    assert "profile-workspace-missing-inbox" not in codes


def test_reference_profile_warns_for_missing_reference_entries(tmp_path):
    subsection = tmp_path / "reference" / "tools"
    subsection.mkdir(parents=True)
    (subsection / "note.md").write_text("# Tool Note\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=tmp_path)
    items = [item("CORPUS.md", "handbook", front_matter=ai_front_matter())]

    codes = issue_codes(items, config)

    assert "profile-reference-missing-root-entry" in codes
    assert "profile-reference-subsection-missing-entry" in codes


def test_reference_profile_accepts_canonical_or_legacy_entries(tmp_path):
    reference = tmp_path / "reference"
    subsection = reference / "tools"
    subsection.mkdir(parents=True)
    (reference / "CORPUS.md").write_text("# Reference\n", encoding="utf-8")
    (subsection / "corpus.md").write_text("# Tools\n", encoding="utf-8")
    (subsection / "note.md").write_text("# Tool Note\n", encoding="utf-8")
    config = CatalogConfig(corpus_root=tmp_path)
    items = [item("CORPUS.md", "handbook", front_matter=ai_front_matter())]

    codes = issue_codes(items, config)

    assert "profile-reference-missing-root-entry" not in codes
    assert "profile-reference-subsection-missing-entry" not in codes


def test_beta_stewardship_warns_when_spec_module_has_no_owner(tmp_path):
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item("CORPUS.md", "handbook", front_matter=ai_front_matter()),
        item(
            "projects/spec/code/corpus-spec/specs/example.md",
            "spec-module",
            front_matter={"corpus_spec_status": "beta"},
        ),
    ]

    codes = issue_codes(items, config)

    assert "spec-beta-missing-stewardship-epic" in codes


def test_beta_stewardship_warns_when_profile_owner_epic_is_missing(tmp_path):
    (tmp_path / "projects" / "spec" / "assets" / "epics").mkdir(parents=True)
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item("CORPUS.md", "handbook", front_matter=ai_front_matter()),
        item(
            "projects/spec/code/corpus-spec/profiles/example.md",
            "profile-module",
            text="Beta stewardship epic: Spec project `999-MISSING`.\n",
            front_matter={"corpus_spec_status": "beta"},
        ),
    ]

    codes = issue_codes(items, config)

    assert "profile-beta-stewardship-epic-missing" in codes


def test_beta_stewardship_accepts_existing_owner_epic(tmp_path):
    (
        tmp_path
        / "projects"
        / "spec"
        / "assets"
        / "epics"
        / "999-MISSING"
    ).mkdir(parents=True)
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item("CORPUS.md", "handbook", front_matter=ai_front_matter()),
        item(
            "projects/spec/code/corpus-spec/profiles/example.md",
            "profile-module",
            text="Beta stewardship epic: Spec project `999-MISSING`.\n",
            front_matter={"corpus_spec_status": "beta"},
        ),
    ]

    codes = issue_codes(items, config)

    assert "profile-beta-stewardship-epic-missing" not in codes


def test_beta_stewardship_ignores_consumed_release_checkout(tmp_path):
    config = CatalogConfig(corpus_root=tmp_path)
    items = [
        item("CORPUS.md", "handbook", front_matter=ai_front_matter()),
        item(
            "corpus-spec/profiles/example.md",
            "profile-module",
            front_matter={"corpus_spec_status": "beta"},
        ),
    ]

    codes = issue_codes(items, config)

    assert "profile-beta-missing-stewardship-epic" not in codes
