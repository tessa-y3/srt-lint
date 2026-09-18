# srtlint

A small validating parser and pretty printer for `.srt` subtitle files.

Subtitle files rot quietly. They get hand-edited, passed through three
different tools, saved with the wrong line endings, and eventually end
up with cue numbers out of order, timestamps that overlap, or a block
with no text in it. Most players are lenient and just show you
whatever garbage results. This tool is not lenient: it parses the file
strictly and tells you exactly which line broke, then can rewrite the
file into a normalized form.

## What it checks

- every cue has a number, a timing line, and at least one line of text
- timestamps match `HH:MM:SS,mmm` and have valid minutes/seconds
- each cue's end time is after its start time
- cues don't start before the previous cue has ended

## What the pretty printer does

Given a parsed set of cues, `render()` writes them back out with:

- cue numbers renumbered 1..N (the original numbers are just a display
  hint, not something downstream tools should rely on)
- timestamps zero-padded consistently
- trailing whitespace stripped from each text line
- a single blank line between cues and a trailing newline at EOF

## Usage

As a library:

```python
from srtlint import parse, render, SubtitleError

with open("movie.srt", encoding="utf-8") as f:
    content = f.read()

try:
    cues = parse(content)
except SubtitleError as e:
    print(f"invalid subtitle file: {e}")
else:
    print(f"parsed {len(cues)} cues")
    print(cues[0].text)
    normalized = render(cues)
```

From the command line:

```
$ python -m srtlint movie.srt
movie.srt: 214 cues, looks valid

$ python -m srtlint broken.srt
broken.srt: line 9: cue end time is not after its start time

$ python -m srtlint messy.srt --fix
messy.srt: rewrote 214 cues
```

## Example input

```
1
00:00:01,000 --> 00:00:04,000
Hello there.

2
00:00:04,500 --> 00:00:06,200
General Kenobi.
```

## Status

Early. Only the SRT format is handled so far -- see the roadmap in the
issue tracker for what's planned next (WebVTT support, a diff mode,
overlap/gap warnings that don't hard-fail parsing).

## Requirements

Python 3.10+, standard library only.

## License

MIT, see LICENSE.
