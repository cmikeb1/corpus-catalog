from pydantic import ValidationError

from corpus_catalog.models import SourceRef


def test_source_ref_rejects_inverted_line_range():
    try:
        SourceRef(path="CORPUS.md", line_start=5, line_end=4)
    except ValidationError as error:
        assert "line_end must be greater than or equal" in str(error)
    else:
        raise AssertionError("Expected SourceRef to reject inverted line range")
