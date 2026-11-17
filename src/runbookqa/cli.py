"""runbookqa command line.

  runbookqa index DIR [DIR ...]        build the local index (rebuilds from scratch)
  runbookqa ask "question"             answer from the index, with cited sources

AI mode (local Ollama model) is the default. If no model is reachable, or with
--rules-only, it prints the best-matching sections instead of an answer.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .answer import OllamaAnswerer, QAReport, RecordedAnswerer, ask
from .index import build_index, search
from .opscore.llm import ModelUnavailable

DEFAULT_DB = os.environ.get("RUNBOOKQA_DB", "runbookqa.db")


def render(report: QAReport) -> str:
    a = report.answer
    out = ["Answer (advisory, from the indexed documents only; check the sources before acting)", ""]
    out += [f"  {line}" for line in a.answer.splitlines()]
    if a.citations:
        out += ["", "Sources"]
        for i, c in enumerate(a.citations, 1):
            commit = next((r["commit"] for r in report.retrieved if r["path"] == c.path and r["commit"]), "")
            flag = "  [FLAGGED: looks like instructions to an AI]" if f"{c.path} > {c.heading}" in report.flagged else ""
            out.append(f"  [{i}] {c.path} > {c.heading}" + (f"  (commit {commit})" if commit else "") + flag)
            quote = c.quote.strip().replace("\n", "\n       ")
            out.append(f'      "{quote}"')
    out += [""]
    if report.flagged:
        out.append("Warning: these retrieved sections contain text that looks like instructions to an AI.")
        out.append("They were passed to the model as data only. Review them and check any answer that cites them:")
        out += [f"  - {f}" for f in report.flagged]
        out.append("")
    if report.mode != "rules-only":
        out.append(f"Confidence: {a.confidence}")
    out.append(f"Mode: {report.mode}" + (f", model {report.model}" if report.model else ""))
    out.append(f"Access tags: {', '.join(report.access) if report.access else 'none (untagged documents only)'}")
    out.append(f"Sections retrieved: {len(report.retrieved)}")
    if report.mode != "rules-only":
        red = sum(report.redactions.values())
        out.append(f"Redactions before the model call: {red} new (documents were redacted at index time)"
                   + (f" ({', '.join(f'{k}: {v}' for k, v in sorted(report.redactions.items()))})" if red else ""))
        out.append(f"Evidence check: {report.dropped_citations} citation(s) and "
                   f"{report.dropped_claims} claim(s) dropped")
    out.append(report.note)
    return "\n".join(out)


def cmd_index(args: argparse.Namespace) -> int:
    stats = build_index(args.dirs, args.db)
    print(f"Indexed {stats.files} file(s) into {stats.chunks} section(s): {args.db}")
    print(f"Redacted at index time: {stats.redaction_total} item(s)")
    if stats.skipped:
        print(f"Skipped (unreadable front matter, so its access tag can't be trusted): {len(stats.skipped)}")
        for s in stats.skipped:
            print(f"  - {s}")
    for path, counts in sorted(stats.redactions.items()):
        print(f"  {path}: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    if stats.redactions:
        print("Fix the source documents above: secrets do not belong in runbooks.")
    if stats.flagged:
        print(f"Sections with text that looks like instructions to an AI (review them): {len(stats.flagged)}")
        for f in stats.flagged:
            print(f"  {f}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    if not Path(args.db).exists():
        print(f"No index at {args.db}. Run: runbookqa index <dir>", file=sys.stderr)
        return 2
    chunks = search(args.db, args.question, k=args.k, access=args.access)

    provider = None
    if args.recorded:
        provider = RecordedAnswerer(Path(args.recorded))
    elif not args.rules_only:
        provider = OllamaAnswerer()
        if not provider.available():
            print(f"Model {provider.model} not reachable at {provider.host}; using rules-only mode.",
                  file=sys.stderr)
            provider = None
    try:
        report = ask(args.question, chunks, provider, access=args.access)
    except ModelUnavailable as e:
        print(f"Model call failed ({e}); using rules-only mode.", file=sys.stderr)
        report = ask(args.question, chunks, None, access=args.access)

    print(report.model_dump_json(indent=2) if args.json else render(report))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="runbookqa", description="Cited answers from your own runbooks.")
    p.add_argument("--db", default=DEFAULT_DB, help=f"index file (default {DEFAULT_DB}, env RUNBOOKQA_DB)")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("index", help="index Markdown files in one or more directories")
    pi.add_argument("dirs", nargs="+")
    pi.set_defaults(func=cmd_index)

    pa = sub.add_parser("ask", help="ask a question")
    pa.add_argument("question")
    pa.add_argument("--access", action="append", default=[], metavar="TAG",
                    help="also include documents with this access tag (repeatable)")
    pa.add_argument("-k", type=int, default=5, help="sections to retrieve (default 5)")
    pa.add_argument("--rules-only", action="store_true", help="no model: show the best-matching sections")
    pa.add_argument("--recorded", metavar="FILE", help="replay a saved model response (tests, offline demo)")
    pa.add_argument("--json", action="store_true", help="print the report as JSON")
    pa.set_defaults(func=cmd_ask)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
