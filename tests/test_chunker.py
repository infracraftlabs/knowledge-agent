from runbookqa.chunker import MAX_CHARS, chunk_markdown, parse_front_matter

DOC = """# Title

Intro text.

## Steps

Run this:

```bash
# not a heading, a shell comment
echo hello
```

### Sub step

Details.
"""


def test_splits_by_heading_and_keeps_heading_path():
    chunks = chunk_markdown("docs/a.md", DOC)
    assert [c.heading for c in chunks] == ["Title", "Title > Steps", "Title > Steps > Sub step"]
    assert all(c.path == "docs/a.md" for c in chunks)


def test_headings_inside_code_fences_are_ignored():
    steps = chunk_markdown("docs/a.md", DOC)[1]
    assert "# not a heading, a shell comment" in steps.body


def test_text_before_first_heading_uses_file_name():
    chunks = chunk_markdown("docs/notes.md", "Just a line.\n\n# Later\n\nMore.")
    assert chunks[0].heading == "notes.md"


def test_long_sections_are_split():
    body = "\n\n".join(f"Paragraph {i} " + "word " * 60 for i in range(20))
    chunks = chunk_markdown("docs/long.md", "# Long\n\n" + body)
    assert len(chunks) > 1
    assert all(len(c.body) <= MAX_CHARS + 400 for c in chunks)
    assert chunks[1].heading == "Long (part 2)"


def test_front_matter_access_tag():
    meta, rest = parse_front_matter("---\ntitle: X\naccess: platform-admins\n---\n# X\n\nBody")
    assert meta["access"] == "platform-admins"
    assert rest.startswith("# X")
    assert parse_front_matter("# No front matter")[0] == {}
