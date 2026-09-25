import unittest

from srtlint.parser import SubtitleError
from srtlint.vtt import VttTimestamp, parse


class VttTimestampTests(unittest.TestCase):
    def test_parse_with_hours(self):
        ts = VttTimestamp.parse("01:02:03.456", line=1)
        self.assertEqual((ts.hours, ts.minutes, ts.seconds, ts.millis), (1, 2, 3, 456))

    def test_parse_without_hours(self):
        ts = VttTimestamp.parse("02:03.456", line=1)
        self.assertEqual((ts.hours, ts.minutes, ts.seconds, ts.millis), (0, 2, 3, 456))

    def test_to_ms(self):
        ts = VttTimestamp.parse("00:01:01.500", line=1)
        self.assertEqual(ts.to_ms(), 61500)

    def test_format_zero_pads(self):
        ts = VttTimestamp(hours=1, minutes=2, seconds=3, millis=4)
        self.assertEqual(ts.format(), "01:02:03.004")

    def test_rejects_srt_comma_separator(self):
        with self.assertRaises(SubtitleError):
            VttTimestamp.parse("00:00:00,000", line=1)

    def test_rejects_out_of_range_minutes(self):
        with self.assertRaises(SubtitleError):
            VttTimestamp.parse("00:60:00.000", line=1)


class ParseValidTests(unittest.TestCase):
    def test_single_cue_without_identifier(self):
        content = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nHello there.\n"
        cues = parse(content)
        self.assertEqual(len(cues), 1)
        self.assertIsNone(cues[0].identifier)
        self.assertEqual(cues[0].start.to_ms(), 1000)
        self.assertEqual(cues[0].end.to_ms(), 4000)
        self.assertEqual(cues[0].text, "Hello there.")

    def test_cue_with_identifier(self):
        content = "WEBVTT\n\nintro\n00:00:01.000 --> 00:00:04.000\nHello there.\n"
        cues = parse(content)
        self.assertEqual(cues[0].identifier, "intro")

    def test_multiple_cues_may_overlap(self):
        content = (
            "WEBVTT\n\n"
            "00:00:00.000 --> 00:00:05.000\nHello.\n\n"
            "00:00:02.000 --> 00:00:06.000\nWorld.\n"
        )
        cues = parse(content)
        self.assertEqual(len(cues), 2)

    def test_cue_settings_after_timestamp_are_ignored(self):
        content = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000 align:middle line:0\nHello there.\n"
        cues = parse(content)
        self.assertEqual(cues[0].end.to_ms(), 4000)

    def test_note_block_is_skipped(self):
        content = (
            "WEBVTT\n\n"
            "NOTE this is a comment\nspanning two lines\n\n"
            "00:00:01.000 --> 00:00:04.000\nHello there.\n"
        )
        cues = parse(content)
        self.assertEqual(len(cues), 1)

    def test_header_with_trailing_description(self):
        content = "WEBVTT - a description\n\n00:00:01.000 --> 00:00:04.000\nHi.\n"
        cues = parse(content)
        self.assertEqual(len(cues), 1)

    def test_multiline_cue_text_preserved(self):
        content = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nLine one\nLine two\n"
        cues = parse(content)
        self.assertEqual(cues[0].lines, ["Line one", "Line two"])


class ParseErrorTests(unittest.TestCase):
    def test_missing_header(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("00:00:01.000 --> 00:00:04.000\nHello there.\n")
        self.assertIn("WEBVTT header", str(cm.exception))

    def test_empty_file(self):
        with self.assertRaises(SubtitleError):
            parse("")

    def test_cue_block_missing_timing_line(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("WEBVTT\n\nintro\n\n")
        self.assertIn("no timing line", str(cm.exception))

    def test_timing_line_missing_arrow(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("WEBVTT\n\n00:00:01.000 - 00:00:04.000\ntext\n")
        self.assertIn("timing line", str(cm.exception))

    def test_end_before_start(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("WEBVTT\n\n00:00:05.000 --> 00:00:01.000\ntext\n")
        self.assertIn("not after its start", str(cm.exception))

    def test_cue_with_no_text(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n\n")
        self.assertIn("no text", str(cm.exception))

    def test_no_cues_after_header(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("WEBVTT\n")
        self.assertIn("no subtitle cues", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
