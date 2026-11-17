# runbookqa

runbookqa answers operational questions from your own Markdown runbooks, module READMEs and
design notes, and shows the source for every sentence. You index one or more directories into
a local SQLite file, then ask a question. A local language model (through Ollama) writes the
answer using only the sections that keyword search retrieved, and every citation is checked
against those sections before you see it. If the documents don't answer the question, it says
"The indexed documents don't cover this." Part of the InfraCraft Labs AI Lab
(https://infracraftlabs.com).

## Status

**Prototype.** It works on the synthetic demo documents in `examples/docs/`. It is not for
production use.

## Quick start

```sh
ollama pull qwen3:8b                      # the default local model
python3.12 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/runbookqa index examples/docs
.venv/bin/runbookqa ask "How do I restore a Postgres backup to a new database?"
.venv/bin/runbookqa ask "How do I upgrade the Kafka cluster to a new version?"   # not covered
.venv/bin/runbookqa ask "break-glass access" --access platform-admins --rules-only
.venv/bin/runbookqa ask "rotate TLS certificate" --rules-only                  # no model needed
```

Options: `--db PATH` (or `RUNBOOKQA_DB`, default `./runbookqa.db`), `-k` sections to retrieve
(default 5), `--access TAG` (repeatable), `--json`, `--recorded FILE` (replay a saved model
response). The model and host come from `OLLAMA_MODEL` and `OLLAMA_HOST`.

## How it works

1. **Index (rules).** `runbookqa index` reads `.md` files in the directories you name, and
   nothing else: no crawling, no following links. Each file is redacted, split into sections
   by heading, and stored in SQLite FTS5 with its path, heading path ("Title > Section"),
   optional `access:` front-matter tag, and the Git commit SHA if the directory is in a Git
   repository (read from `.git` files; no git binary is run). Each run rebuilds the index from
   scratch. The command reports how many secrets it redacted per file, and which sections
   contain text that looks like instructions to an AI.
2. **Retrieve.** The question is turned into keywords and ranked with SQLite's built-in BM25
   (heading matches weigh more than body matches). Access tags are applied here: untagged
   sections are visible to everyone; tagged sections only with a matching `--access` tag.
3. **Redaction.** Documents are redacted at index time, so secrets never reach the index. The
   question and retrieved sections are redacted again before the model call, and the report
   shows how many new items were removed.
4. **Model.** The question and the top sections, each wrapped as untrusted data, go to the
   local model, which must return claims with citations (path, heading, exact quote) as JSON.
5. **Evidence check.** Every quote must appear in a retrieved section of the cited file. A
   citation that can't be found is dropped, together with every claim that relied on it, and
   the counts are printed. If nothing survives, the answer is "The indexed documents don't
   cover this."

With `--rules-only`, or when no model is reachable, it skips steps 4 and 5 and prints the
best-matching sections and their sources instead of an answer.

There is no embedding model in v0.1: retrieval is keyword search only. For runbooks full of
exact command names and error strings this is a strong baseline. Embeddings with PostgreSQL and
pgvector, compared against this baseline, are the documented next step.

## Security model

- **Permissions:** none beyond reading the directories you pass to `index` and writing the
  index file. It needs no tokens or cloud credentials.
- **What is read:** Markdown files in the named directories, and `.git/HEAD` plus refs to find
  the commit SHA.
- **What never happens:** it runs no commands, has no shell or tools, makes no network calls
  other than to the Ollama host, and never changes anything. Commands in answers are text for
  a person to read and check.
- **Secrets:** redacted at index time with conservative patterns (keys, tokens, passwords,
  connection strings, emails, IP addresses, long random strings); the index report names the
  files so you can fix the source.
- **Access tags:** sections tagged `access: <tag>` are filtered out before anything reaches the
  model unless the caller passes that tag. This is a filter, not authentication: anyone who can
  read the index file can read every section. Use one index per audience. Front matter is read
  even after a byte-order mark or blank lines, and a file whose front matter opens but never
  closes is skipped and reported, never indexed without its tag (fail closed). Before
  2026-11-17 such files were indexed as untagged and visible to everyone; re-index if you used
  an earlier version.
- **Prompt injection in documents:** retrieved text is wrapped and labelled as data, the model
  has no tools to misuse, it only sees sections the access filter allowed, and every citation
  must quote a retrieved section. Sections containing instruction-like text are flagged at
  index time and marked in any answer that cites them. The demo set includes such a document
  (`runbooks/clear-disk-space.md`) and tests show it cannot widen access or add sources.

## Limitations

- Keyword search only: questions worded differently from the documents can miss the right
  section. No synonyms, no embeddings.
- Markdown only. No PDFs, wikis or `*.tf` files yet.
- Redaction is lossy by design. In the demo it hides the example CIDR in the network module
  README and the `id-token: write` permission line in the OIDC runbook.
- Access tags are a query-time filter on a shared file, not per-user permissions.
- The evidence check proves a quote exists in a cited section; it does not prove the claim's
  wording follows from it. A model can still relay a poisoned instruction if it quotes it; the
  flag makes this visible but does not block it. Read the sources.
- Stale or conflicting documents give stale or conflicting answers. Conflict detection is not
  built.
- The small local model is sometimes over-cautious (it often reports low confidence) and quotes
  long passages.
- No audit log and no HTTP API yet.
- Replay fixtures in `examples/recorded/` are hand-written in the model's response format for
  tests; only `examples/demo-output.md` comes from a real model run.

## Tests

```sh
.venv/bin/pip install -e .[dev]
.venv/bin/pytest -q              # offline; uses recorded responses
.venv/bin/pytest -m live         # optional: one real case against a local model
```

Tests cover chunking, BM25 ranking, access filtering, redaction, citation checks, the injection
document, end-to-end CLI runs, and a small retrieval evaluation (`examples/eval/questions.json`:
each question's expected source must be in the top 3).

## Demo

See [examples/demo-output.md](examples/demo-output.md): one real run with qwen3:8b on the
synthetic documents, including a question the documents don't cover.

## Licence

MIT. See [LICENSE](LICENSE). Security reports: see [SECURITY.md](SECURITY.md).
