"""Pretty printer that re-serializes parsed cues into normalized SRT."""
from __future__ import annotations


def render(cues, renumber: bool = True) -> str:
    """Render cues back into SRT text with consistent formatting.

    Renumbers cues 1..N by default, since the leading index in a
    cue block is only a display hint -- nothing requires it to be
    sequential or even unique, so it isn't safe to trust on the way
    back out.
    """
    blocks = []
    for i, cue in enumerate(cues, start=1):
        index = i if renumber else cue.index
        timing = f"{cue.start.format()} --> {cue.end.format()}"
        text = "\n".join(line.strip() for line in cue.lines)
        blocks.append(f"{index}\n{timing}\n{text}")
    return "\n\n".join(blocks) + "\n"
