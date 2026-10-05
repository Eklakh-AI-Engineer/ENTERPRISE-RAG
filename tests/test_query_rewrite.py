import pytest

from app.query.rewrite import QueryRewriter


def test_rewriting_is_disabled_by_default():
    rewriter = QueryRewriter()

    assert not rewriter.enabled
    assert rewriter.rewrite("What does CHA say about employment at will?") == (
        "What does CHA say about employment at will?"
    )


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("What does CHA say about HR-42?", "CHA say about HR-42?"),
        ("What is the OIG policy?", "the OIG policy?"),
        ("How should CHA report case 007?", "CHA report case 007?"),
        ("What happens when an employee does not comply?", "an employee does not comply?"),
        ("What are only reasonable accommodations?", "only reasonable accommodations?"),
        ("Can you tell me policy section 4.2 on page 17?", "policy section 4.2 on page 17?"),
        (
            "Could you tell me document_id=DOC-17 tenant_id=TEN-3?",
            "document_id=DOC-17 tenant_id=TEN-3?",
        ),
    ],
)
def test_rewrite_preserves_query_body_and_protected_terms(query, expected):
    assert QueryRewriter(enabled=True).rewrite(query) == expected


def test_query_rewriter_reports_original_and_rewritten_text():
    result = QueryRewriter(enabled=True).as_result("  What does CHA say?  ")

    assert result.original_query == "What does CHA say?"
    assert result.rewritten_query == "CHA say?"
    assert result.changed
    assert result.enabled