"""Parsing for WebVTT subtitle files.

WebVTT is close enough to SRT -- blank-line-separated blocks, a timing
line with an arrow, text lines below it -- that it reuses the same
block splitter. The differences that matter for parsing: a mandatory
WEBVTT header, a dot instead of a comma before milliseconds, an
optional cue identifier instead of a mandatory numeric index, optional
hours in the timestamp, and NOTE comment blocks that carry no cue data.
Cues are also allowed to overlap (that's how simultaneous captions are
expressed), so unlike the SRT parser this one does not reject a cue
that starts before the previous one ends.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from ._blocks import split_blocks
from .parser import SubtitleError

VTT_TIMESTAMP_RE = re.compile(r"^(?:(\d{2,}):)?(\d{2}):(\d{2})\.(\d{3})$")


@dataclass
class VttTimestamp:
    hours: int
    minutes: int
    seconds: int
    millis: int

    def to_ms(self) -> int:
        return ((self.hours * 60 + self.minutes) * 60 + self.seconds) * 1000 + self.millis

    @classmethod
    def parse(cls, raw: str, line: int) -> "VttTimestamp":
        m = VTT_TIMESTAMP_RE.match(raw.strip())
        if not m:
            raise SubtitleError(f"malformed timestamp {raw!r}", line)
        hours_group, minutes, seconds, millis = m.groups()
        hours = int(hours_group) if hours_group else 0
        minutes, seconds, millis = int(minutes), int(seconds), int(millis)
        if minutes >= 60 or seconds >= 60:
            raise SubtitleError(f"timestamp {raw!r} has out-of-range minutes/seconds", line)
        return cls(hours, minutes, seconds, millis)

    def format(self) -> str:
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}.{self.millis:03d}"


@dataclass
class VttCue:
    identifier: str | None
    start: VttTimestamp
    end: VttTimestamp
    lines: list

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def parse(content: str) -> list:
    """Parse WebVTT text into a list of VttCue objects, or raise SubtitleError."""
    blocks = split_blocks(content)
    if not blocks:
        raise SubtitleError("file contains no subtitle cues", 1)

    header_line, header_block = blocks[0]
    if not header_block[0].strip().startswith("WEBVTT"):
        raise SubtitleError("file does not start with a WEBVTT header", header_line)

    cues = []
    for start_line, block in blocks[1:]:
        first_line = block[0].strip()
        if first_line.startswith("NOTE"):
            continue

        has_identifier = "-->" not in first_line
        offset = 1 if has_identifier else 0
        identifier = first_line if has_identifier else None

        if len(block) <= offset:
            raise SubtitleError("cue block has no timing line", start_line)

        timing_line = block[offset]
        if "-->" not in timing_line:
            raise SubtitleError(f"expected a timing line, got {timing_line!r}", start_line + offset)
        raw_start, raw_end = timing_line.split("-->", 1)
        # timing lines may carry cue settings after the end timestamp
        raw_end = raw_end.strip().split(" ")[0]
        start = VttTimestamp.parse(raw_start, start_line + offset)
        end = VttTimestamp.parse(raw_end, start_line + offset)
        if end.to_ms() <= start.to_ms():
            raise SubtitleError("cue end time is not after its start time", start_line + offset)

        text_lines = block[offset + 1:]
        if not text_lines:
            raise SubtitleError("cue has no text", start_line)

        cues.append(VttCue(identifier=identifier, start=start, end=end, lines=text_lines))

    if not cues:
        raise SubtitleError("file contains no subtitle cues", 1)

    return cues
