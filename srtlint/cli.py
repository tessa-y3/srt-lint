"""Command-line entry point: python -m srtlint <file> [--fix]"""
from __future__ import annotations

import sys

from .parser import parse, SubtitleError
from .printer import render


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: srtlint <file.srt> [--fix]", file=sys.stderr)
        return 2

    path = argv[0]
    fix = "--fix" in argv[1:]

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        cues = parse(content)
    except SubtitleError as e:
        print(f"{path}: {e}", file=sys.stderr)
        return 1

    if fix:
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(cues))
        print(f"{path}: rewrote {len(cues)} cues")
    else:
        print(f"{path}: {len(cues)} cues, looks valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
