"""Parsing and validation for SRT subtitle files."""
from __future__ import annotations

from dataclasses import dataclass
import re

TIMESTAMP_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2}),(\d{3})$")


class SubtitleError(ValueError):
    """Raised when a subtitle file fails validation.

    Carries the line number of the offending block so a caller can
    point a user at the right spot in the file -- SRT itself gives
    no other way to correlate an error back to source text.
    """

    def __init__(self, message: str, line: int | None = None):
        self.line = line
        if line is not None:
            message = f"line {line}: {message}"
        super().__init__(message)


@dataclass
class Timestamp:
    hours: int
    minutes: int
    seconds: int
    millis: int

    def to_ms(self) -> int:
        return ((self.hours * 60 + self.minutes) * 60 + self.seconds) * 1000 + self.millis

    @classmethod
    def parse(cls, raw: str, line: int) -> "Timestamp":
        m = TIMESTAMP_RE.match(raw.strip())
        if not m:
            raise SubtitleError(f"malformed timestamp {raw!r}", line)
        hours, minutes, seconds, millis = (int(g) for g in m.groups())
        if minutes >= 60 or seconds >= 60:
            raise SubtitleError(f"timestamp {raw!r} has out-of-range minutes/seconds", line)
        return cls(hours, minutes, seconds, millis)

    def format(self) -> str:
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d},{self.millis:03d}"


@dataclass
class Cue:
    index: int
    start: Timestamp
    end: Timestamp
    lines: list

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def _split_blocks(content: str):
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


def parse(content: str) -> list:
    """Parse SRT text into a list of Cue objects, or raise SubtitleError."""
    blocks = _split_blocks(content)

    cues = []
    last_end_ms = -1
    for start_line, block in blocks:
        if len(block) < 2:
            raise SubtitleError(f"cue block has no timing line: {block!r}", start_line)

        index_line = block[0].strip()
        try:
            index = int(index_line)
        except ValueError:
            raise SubtitleError(f"expected a cue number, got {index_line!r}", start_line)

        timing_line = block[1]
        if "-->" not in timing_line:
            raise SubtitleError(f"expected a timing line, got {timing_line!r}", start_line + 1)
        raw_start, raw_end = timing_line.split("-->", 1)
        # timing lines may carry positioning hints after the end timestamp
        raw_end = raw_end.strip().split(" ")[0]
        start = Timestamp.parse(raw_start, start_line + 1)
        end = Timestamp.parse(raw_end, start_line + 1)
        if end.to_ms() <= start.to_ms():
            raise SubtitleError("cue end time is not after its start time", start_line + 1)
        if start.to_ms() < last_end_ms:
            raise SubtitleError("cue starts before the previous cue ends", start_line + 1)
        last_end_ms = end.to_ms()

        text_lines = block[2:]
        if not text_lines:
            raise SubtitleError("cue has no text", start_line)

        cues.append(Cue(index=index, start=start, end=end, lines=text_lines))

    if not cues:
        raise SubtitleError("file contains no subtitle cues", 1)

    return cues
