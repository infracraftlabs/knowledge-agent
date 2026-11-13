"""Local keyword index: SQLite FTS5 with BM25 ranking.

`build_index` reads Markdown files from the directories it is given (nothing else: no
crawling, no following links), redacts each file with opscore.redact, splits it into
sections and stores them in one SQLite file. Each run rebuilds the index from scratch,
so removed or changed documents never linger.

`search` ranks sections with SQLite's built-in bm25() and applies access tags at query
time: untagged sections are visible to everyone; tagged sections only when the caller
passes a matching --access tag.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .chunker import Chunk, chunk_markdown, parse_front_matter
from .opscore.redact import redact

MARKDOWN_SUFFIXES = {".md", ".markdown"}
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__"}

# Words that carry no meaning for retrieval. Kept short on purpose.
STOPWORDS = set(
    "a an and are as at be by can do does for from has have how i if in is it its me my of on or "
    "our should so that the their there this to was we what when where which who why will with "
    "you your".split()
)


# Text in a document that addresses an AI assistant. Heuristic only: it makes a poisoned
# section visible to reviewers; the real defences are no tools, data wrapping and citations.
INJECTION_HINTS = re.compile(
    r"(?i)(ignore|disregard|forget)\s+(all\s+|any\s+)?(your|previous|prior|earlier|the above)\s+"
    r"(instructions|rules|prompt)|\b(ai|llm)\s+assistant\s*:|\bsystem prompt\b"
)


def looks_like_injection(text: str) -> bool:
    return bool(INJECTION_HINTS.search(text))


@dataclass
class IndexStats:
    files: int = 0
    chunks: int = 0
    redactions: dict[str, dict[str, int]] = field(default_factory=dict)  # path -> kind -> count
    flagged: list[str] = field(default_factory=list)  # "path > heading" with instruction-like text

    @property
    def redaction_total(self) -> int:
        return sum(sum(c.values()) for c in self.redactions.values())


def git_commit(directory: Path) -> str:
    """Return the HEAD commit SHA if `directory` is inside a Git repository, else "".

    Reads .git files directly (no git binary, no subprocess)."""
    for parent in [directory, *directory.parents]:
        git = parent / ".git"
        if git.is_file():  # worktree or submodule: "gitdir: <path>"
            content = git.read_text().strip()
            if content.startswith("gitdir:"):
                git = (parent / content.split(":", 1)[1].strip()).resolve()
        if not (git / "HEAD").is_file():
            continue
        head = (git / "HEAD").read_text().strip()
        if not head.startswith("ref:"):
            return head
        ref = head.split(":", 1)[1].strip()
        ref_file = git / ref
        if ref_file.is_file():
            return ref_file.read_text().strip()
        packed = git / "packed-refs"
        if packed.is_file():
            for line in packed.read_text().splitlines():
                if line.endswith(" " + ref):
                    return line.split(" ", 1)[0]
        return ""  # a repository with no commits yet
    return ""


def connect(db_path: str | Path) -> sqlite3.Connection:
    return sqlite3.connect(str(db_path))


def _create(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS chunks;
        CREATE VIRTUAL TABLE chunks USING fts5(
            path, heading, body,
            access UNINDEXED, sha UNINDEXED, flagged UNINDEXED,
            tokenize = 'porter unicode61'
        );
        """
    )


def iter_markdown(directory: Path):
    for p in sorted(directory.rglob("*")):
        if p.is_file() and p.suffix.lower() in MARKDOWN_SUFFIXES and not (SKIP_DIRS & set(p.parts)):
            yield p


def build_index(directories: list[str | Path], db_path: str | Path) -> IndexStats:
    stats = IndexStats()
    conn = connect(db_path)
    with conn:
        _create(conn)
        for d in directories:
            directory = Path(d).resolve()
            if not directory.is_dir():
                raise FileNotFoundError(f"not a directory: {d}")
            sha = git_commit(directory)
            for file in iter_markdown(directory):
                rel = f"{directory.name}/{file.relative_to(directory).as_posix()}"
                meta, body = parse_front_matter(file.read_text(encoding="utf-8", errors="replace"))
                cleaned = redact(body)
                if cleaned.counts:
                    stats.redactions[rel] = cleaned.counts
                chunks = chunk_markdown(rel, cleaned.text, access=meta.get("access", ""), commit=sha)
                for c in chunks:
                    c.flagged = looks_like_injection(c.heading + "\n" + c.body)
                    if c.flagged:
                        stats.flagged.append(f"{c.path} > {c.heading}")
                conn.executemany(
                    "INSERT INTO chunks(path, heading, body, access, sha, flagged) VALUES (?, ?, ?, ?, ?, ?)",
                    [(c.path, c.heading, c.body, c.access, c.commit, int(c.flagged)) for c in chunks],
                )
                stats.files += 1
                stats.chunks += len(chunks)
    conn.close()
    return stats


def query_terms(question: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9_]+", question.lower())
    seen: list[str] = []
    for w in words:
        if w not in STOPWORDS and len(w) > 1 and w not in seen:
            seen.append(w)
    return seen


def search(db_path: str | Path, question: str, k: int = 5, access: list[str] | None = None) -> list[Chunk]:
    """Top-k sections by BM25. Heading matches count double, path matches half."""
    terms = query_terms(question)
    if not terms:
        return []
    match = " OR ".join(f'"{t}"' for t in terms)
    tags = [t for t in (access or []) if t]
    placeholders = ",".join("?" for _ in tags)
    access_clause = f"(access = '' OR access IN ({placeholders}))" if tags else "access = ''"
    sql = (
        "SELECT path, heading, body, access, sha, flagged FROM chunks "
        f"WHERE chunks MATCH ? AND {access_clause} "
        "ORDER BY bm25(chunks, 0.5, 2.0, 1.0) LIMIT ?"
    )
    conn = connect(db_path)
    try:
        rows = conn.execute(sql, [match, *tags, k]).fetchall()
    finally:
        conn.close()
    return [Chunk(path=r[0], heading=r[1], body=r[2], access=r[3], commit=r[4], flagged=bool(r[5])) for r in rows]
