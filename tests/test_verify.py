from runbookqa.answer import NOT_COVERED, Citation, Claim, ModelAnswer, verify_answer
from runbookqa.chunker import Chunk

CHUNKS = [
    Chunk(path="docs/a.md", heading="A > Steps", body="Run `kubectl scale deployment checkout -n shop --replicas=6` now."),
    Chunk(path="docs/b.md", heading="B", body="The default limits are minReplicas: 2 and maxReplicas: 10."),
]


def cit(path, quote, heading="X"):
    return Citation(path=path, heading=heading, quote=quote)


def test_real_quotes_survive_and_heading_is_corrected():
    ans, dc, dcl = verify_answer(ModelAnswer(claims=[
        Claim(text="Scale with kubectl.", citations=[cit("docs/a.md", "kubectl scale deployment checkout")]),
    ], confidence="high"), CHUNKS)
    assert (dc, dcl) == (0, 0)
    assert ans.citations[0].heading == "A > Steps"
    assert ans.answer == "Scale with kubectl. [1]"
    assert not ans.not_covered


def test_markdown_marks_and_whitespace_are_ignored_when_matching():
    ans, dc, _ = verify_answer(ModelAnswer(claims=[
        Claim(text="t", citations=[cit("docs/a.md", "`kubectl  scale deployment`")]),
    ]), CHUNKS)
    assert dc == 0 and ans.claims


def test_invented_quote_is_dropped_with_its_claim():
    ans, dc, dcl = verify_answer(ModelAnswer(claims=[
        Claim(text="real", citations=[cit("docs/b.md", "maxReplicas: 10")]),
        Claim(text="invented", citations=[cit("docs/b.md", "maxReplicas can be set to 500")]),
    ], confidence="high"), CHUNKS)
    assert [c.text for c in ans.claims] == ["real"]
    assert (dc, dcl) == (1, 1)
    assert ans.confidence == "medium"  # capped because something was dropped


def test_quote_from_the_wrong_file_is_dropped():
    _, dc, dcl = verify_answer(ModelAnswer(claims=[
        Claim(text="t", citations=[cit("docs/a.md", "maxReplicas: 10")]),
    ]), CHUNKS)
    assert (dc, dcl) == (1, 1)


def test_claim_with_one_bad_citation_is_dropped_entirely():
    ans, dc, dcl = verify_answer(ModelAnswer(claims=[
        Claim(text="t", citations=[cit("docs/b.md", "maxReplicas: 10"), cit("docs/b.md", "made up words here")]),
    ]), CHUNKS)
    assert ans.not_covered and ans.answer == NOT_COVERED
    assert (dc, dcl) == (1, 1)


def test_too_short_quotes_do_not_count():
    _, dc, _ = verify_answer(ModelAnswer(claims=[Claim(text="t", citations=[cit("docs/b.md", "2 and")])]), CHUNKS)
    assert dc == 1


def test_model_saying_not_covered_wins():
    ans, _, _ = verify_answer(ModelAnswer(not_covered=True), CHUNKS)
    assert ans.not_covered and ans.answer == NOT_COVERED and ans.citations == []
