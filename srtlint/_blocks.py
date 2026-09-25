"""Shared line-block splitting used by both the SRT and WebVTT parsers."""
from __future__ import annotations


def split_blocks(content: str):
    """Split file text into (start_line, lines) blocks on blank lines."""
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")

    blocks = []
    current = []
    start_line = 1
    for i, line in enumerate(lines, start=1):
        if line.strip() == "":
            if current:
                blocks.append((start_line, current))
                current = []
        else:
            if not current:
                start_line = i
            current.append(line)
    if current:
        blocks.append((start_line, current))
    return blocks
