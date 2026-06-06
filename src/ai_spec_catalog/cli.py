from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from ai_spec_catalog.config import CatalogConfig
from ai_spec_catalog.context import build_context_packet
from ai_spec_catalog.corpus import search_corpus
from ai_spec_catalog.models import CatalogStatus
from ai_spec_catalog.projects import build_project_creation_plan
from ai_spec_catalog.storage import (
    catalog_status,
    gitignore_warning,
    index_catalog,
    init_catalog,
    load_index_or_corpus,
)
from ai_spec_catalog.validators import validate_corpus


def main() -> None:
    parser = argparse.ArgumentParser(prog="catalog")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    add_root_argument(init_parser)

    index_parser = subparsers.add_parser("index")
    add_root_argument(index_parser)

    status_parser = subparsers.add_parser("status")
    add_root_argument(status_parser)
    status_parser.add_argument("--format", choices=("text", "json"), default="text")

    context_parser = subparsers.add_parser("context")
    add_root_argument(context_parser)
    context_parser.add_argument("--cwd")
    context_parser.add_argument("--goal", required=True)

    search_parser = subparsers.add_parser("search")
    add_root_argument(search_parser)
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=10)

    validate_parser = subparsers.add_parser("validate")
    add_root_argument(validate_parser)
    validate_parser.add_argument("--format", choices=("json", "markdown"), default="json")

    project_parser = subparsers.add_parser("project")
    project_subparsers = project_parser.add_subparsers(
        dest="project_command", required=True
    )
    project_new_parser = project_subparsers.add_parser("new")
    add_root_argument(project_new_parser)
    project_new_parser.add_argument("--name", required=True)
    project_new_parser.add_argument("--slug")
    project_new_parser.add_argument("--tag")
    project_new_parser.add_argument("--tier")
    project_new_parser.add_argument("--lifecycle", default="DRAFT")

    argv = sys.argv[1:]
    if not argv:
        if looks_like_corpus_root(Path.cwd()):
            argv = ["status"]
        else:
            parser.print_help()
            return

    args = parser.parse_args(argv)
    config = CatalogConfig(corpus_root=Path(args.root))

    if args.command == "init":
        manifest = init_catalog(config)
        warning = gitignore_warning(config)
        if warning:
            print(f"warning: {warning}", file=sys.stderr)
        print(manifest.model_dump_json(indent=2))
    elif args.command == "index":
        manifest = index_catalog(config)
        print(manifest.model_dump_json(indent=2))
    elif args.command == "status":
        status = catalog_status(config)
        if args.format == "json":
            print(status.model_dump_json(indent=2))
        else:
            print(format_status(status))
    elif args.command == "context":
        packet = build_context_packet(goal=args.goal, cwd=args.cwd, config=config)
        print(packet.model_dump_json(indent=2))
    elif args.command == "search":
        items = search_corpus(args.query, load_index_or_corpus(config), limit=args.limit)
        print(json.dumps(format_search_results(args.query, items), indent=2))
    elif args.command == "validate":
        index_catalog(config)
        issues = validate_corpus(load_index_or_corpus(config), config)
        if args.format == "markdown":
            report_path = config.catalog_dir / "reports" / "validation.md"
            print(report_path.read_text(encoding="utf-8"))
        else:
            print(json.dumps([issue.model_dump(mode="json") for issue in issues], indent=2))
    elif args.command == "project" and args.project_command == "new":
        plan = build_project_creation_plan(
            name=args.name,
            config=config,
            slug=args.slug,
            tag=args.tag,
            tier=args.tier,
            lifecycle=args.lifecycle,
        )
        print(plan.model_dump_json(indent=2))


def add_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        default=".",
        help="Corpus root directory. Defaults to the current working directory.",
    )


def looks_like_corpus_root(path: Path) -> bool:
    if (path / ".catalog").is_dir():
        return True
    if not (path / "AI.md").is_file():
        return False
    return any((path / name).exists() for name in ("projects", "reference", "ai-spec"))


def format_search_results(query: str, items) -> list[dict[str, object]]:
    return [
        {
            "source": item.source.model_dump(mode="json"),
            "title": item.title,
            "snippet": search_snippet(query, item.text) or item.source.excerpt,
            "metadata": search_metadata(item.front_matter),
            "content_hash": item.content_hash,
        }
        for item in items
    ]


def search_metadata(front_matter: dict[str, object]) -> dict[str, object]:
    keys = (
        "doc_type",
        "ai_spec_version",
        "ai_spec_profile",
        "ai_spec_adoption",
        "ai_spec_reviewed",
        "ai_spec_betas",
    )
    return {key: front_matter[key] for key in keys if key in front_matter}


def search_snippet(query: str, text: str, context_chars: int = 140) -> str | None:
    terms = [term.casefold() for term in query.split() if term.strip()]
    if not terms:
        return None

    folded = text.casefold()
    matches = [
        (index, term)
        for term in terms
        if (index := folded.find(term)) >= 0
    ]
    if not matches:
        return None

    index, term = min(matches, key=lambda match: match[0])
    start = max(0, index - context_chars)
    end = min(len(text), index + len(term) + context_chars)
    snippet = " ".join(text[start:end].split())
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(text):
        snippet = f"{snippet}..."
    return snippet


def format_status(status: CatalogStatus) -> str:
    lines = [
        f"Catalog state: {status.state}",
        f"Corpus root: {status.corpus_root}",
        f"Catalog dir: {status.catalog_dir}",
    ]
    if status.manifest and status.manifest.generated_at:
        lines.append(f"Generated: {status.manifest.generated_at}")
    if status.manifest and status.manifest.ai_spec_baseline:
        lines.append(f"AI-SPEC baseline: {status.manifest.ai_spec_baseline}")
    if status.missing_artifacts:
        lines.append("Missing artifacts:")
        lines.extend(f"- {artifact}" for artifact in status.missing_artifacts)
    if status.stale_reasons:
        lines.append("Reasons:")
        lines.extend(f"- {reason}" for reason in status.stale_reasons)
    if status.next_commands:
        lines.append("Next commands:")
        lines.extend(f"- {command}" for command in status.next_commands)
    return "\n".join(lines)


if __name__ == "__main__":
    main()
