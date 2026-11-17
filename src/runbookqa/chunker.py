"""Read Markdown files and split them into sections by heading.

Each chunk keeps its file path, its heading path ("Title > Section") and the optional
`access` tag from the file's front matter. Headings inside fenced code blocks are ignored.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
MAX_CHARS = 1500  # a section longer than this is split on blank lines


@dataclass
class Chunk:
    path: str
    heading: str
    body: str
    access: str = ""  # "" means readable by everyone using this index
    commit: str = ""
    flagged: bool = False  # contains text that looks like instructions to an AI


class FrontMatterError(ValueError):
    """A file starts like front matter but it can't be read. Such files are skipped, never indexed
    without their access tag (fail closed)."""


_OPEN = re.compile(r"\A---[ \t]*\n")
_CLOSE = re.compile(r"\n---[ \t]*(?:\n|\Z)")


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Very small front-matter reader: `key: value` lines between two `---` lines.

    Tolerates a byte-order mark, leading blank lines and trailing spaces on the `---` lines, so an
    access tag is never silently ignored. Raises FrontMatterError when a block opens but never closes.
    """
    stripped = text.lstrip("\ufeff").lstrip(" \t\r\n")
    if not _OPEN.match(stripped):
        return {}, text
    start = _OPEN.match(stripped).end()
    close = _CLOSE.search(stripped, start - 1)
    if close is None:
        raise FrontMatterError("front matter opens with --- but never closes")
    meta: dict[str, str] = {}
    for line in stripped[start:close.start()].splitlines():
        if ":" in line and not line.startswith((" ", "#")):
            key, value = line.split(":", 1)
            meta[key.strip().lower()] = value.strip().strip("\"'")
    rest = stripped[close.end():]
    return meta, rest.lstrip("\n")


def _split_long(body: str) -> list[str]:
    if len(body) <= MAX_CHARS:
        return [body]
    parts: list[str] = []
    current = ""
    for para in re.split(r"\n\s*\n", body):
        if current and len(current) + len(para) + 2 > MAX_CHARS:
            parts.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        parts.append(current)
    return parts


def chunk_markdown(path: str, text: str, access: str = "", commit: str = "") -> list[Chunk]:
    """Split Markdown text (front matter already removed) into heading sections."""
    stack: list[tuple[int, str]] = []
    sections: list[tuple[str, list[str]]] = [("", [])]
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
        m = None if in_fence else HEADING.match(line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            sections.append((" > ".join(t for _, t in stack), []))
        else:
            sections[-1][1].append(line)

    chunks: list[Chunk] = []
    for heading, lines in sections:
        body = "\n".join(lines).strip()
        if not body:
            continue
        heading = heading or path.rsplit("/", 1)[-1]
        parts = _split_long(body)
        for i, part in enumerate(parts, 1):
            h = heading if len(parts) == 1 else f"{heading} (part {i})"
            chunks.append(Chunk(path=path, heading=h, body=part, access=access, commit=commit))
    return chunks
