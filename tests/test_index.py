import sqlite3

from runbookqa.index import build_index, git_commit, query_terms, search

from .conftest import DOCS


def test_fts5_bm25_is_used(db):
    sql = sqlite3.connect(db).execute("SELECT sql FROM sqlite_master WHERE name='chunks'").fetchone()[0]
    assert "fts5" in sql.lower()


def test_bm25_ranks_the_right_runbook_first(db):
    cases = {
        "How do I rotate the TLS certificate?": "docs/runbooks/rotate-tls-certificate.md",
        "restore a Postgres backup": "docs/runbooks/restore-postgres-backup.md",
        "Which inputs does the network module require?": "docs/modules/network/README.md",
        "roll back a release": "docs/runbooks/rollback-release.md",
        "replace CI deploy keys with OIDC": "docs/runbooks/ci-deploy-keys-to-oidc.md",
    }
    for question, path in cases.items():
        assert search(db, question, k=3)[0].path == path, question


def test_heading_match_beats_body_mention(db):
    # "incident template" is mentioned in other runbooks' bodies; the template itself must win.
    assert search(db, "incident template", k=1)[0].path == "docs/templates/incident-template.md"


def test_stopwords_only_question_returns_nothing(db):
    assert query_terms("how do I do it?") == []
    assert search(db, "how do I do it?") == []


def test_restricted_doc_hidden_without_access_tag(db):
    for q in ["break-glass access", "sealed envelope admin vault", "Break-glass access steps"]:
        assert all("restricted" not in c.path for c in search(db, q, k=20))


def test_restricted_doc_visible_with_matching_tag_only(db):
    assert search(db, "break-glass access", access=["platform-admins"])[0].path == "docs/restricted/break-glass-access.md"
    assert all("restricted" not in c.path for c in search(db, "break-glass access", k=20, access=["team-x"]))


def test_planted_secret_never_reaches_the_index(db):
    rows = sqlite3.connect(db).execute("SELECT body FROM chunks").fetchall()
    text = "\n".join(r[0] for r in rows)
    assert "Fake0nlyRestorePassw0rd" not in text
    assert "PGPASSWORD=[REDACTED:secret]" in text


def test_index_reports_redactions_and_flags(tmp_path):
    stats = build_index([DOCS], tmp_path / "i.db")
    assert stats.files == 11
    assert stats.redactions["docs/runbooks/restore-postgres-backup.md"]["key-value-secret"] == 1
    assert stats.flagged == ["docs/runbooks/clear-disk-space.md > Clear disk space on a build node > Note for automated assistants"]


def test_rebuild_drops_removed_documents(tmp_path):
    d = tmp_path / "docs"
    d.mkdir()
    (d / "a.md").write_text("# Alpha runbook\n\nzebra steps")
    db = tmp_path / "i.db"
    build_index([d], db)
    assert search(db, "zebra")
    (d / "a.md").unlink()
    (d / "b.md").write_text("# Beta\n\nother text")
    build_index([d], db)
    assert search(db, "zebra") == []


def test_git_commit_is_read_without_git_binary(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".git" / "refs" / "heads").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (repo / ".git" / "refs" / "heads" / "main").write_text("3f9a2c1b7e4d5f6a8b9c0d1e2f3a4b5c6d7e8f9a\n")
    (repo / "runbooks").mkdir()
    (repo / "runbooks" / "x.md").write_text("# X\n\nunique quokka text")
    assert git_commit(repo / "runbooks") == "3f9a2c1b7e4d5f6a8b9c0d1e2f3a4b5c6d7e8f9a"
    db = tmp_path / "i.db"
    build_index([repo / "runbooks"], db)
    assert search(db, "quokka")[0].commit.startswith("3f9a2c1b")
    (tmp_path / "plain").mkdir()
    assert git_commit(tmp_path / "plain") == ""  # outside a repo: empty, never an error
