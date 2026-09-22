import unittest

from srtlint.parser import Timestamp, SubtitleError, parse


class TimestampTests(unittest.TestCase):
    def test_parse_valid(self):
        ts = Timestamp.parse("01:02:03,456", line=1)
        self.assertEqual((ts.hours, ts.minutes, ts.seconds, ts.millis), (1, 2, 3, 456))

    def test_to_ms(self):
        ts = Timestamp.parse("00:01:01,500", line=1)
        self.assertEqual(ts.to_ms(), 61500)

    def test_format_zero_pads(self):
        ts = Timestamp(hours=1, minutes=2, seconds=3, millis=4)
        self.assertEqual(ts.format(), "01:02:03,004")

    def test_rejects_wrong_separator(self):
        with self.assertRaises(SubtitleError):
            Timestamp.parse("00:00:00.000", line=1)

    def test_rejects_missing_millis(self):
        with self.assertRaises(SubtitleError):
            Timestamp.parse("00:00:00", line=1)

    def test_rejects_out_of_range_minutes(self):
        with self.assertRaises(SubtitleError):
            Timestamp.parse("00:60:00,000", line=1)

    def test_rejects_out_of_range_seconds(self):
        with self.assertRaises(SubtitleError):
            Timestamp.parse("00:00:60,000", line=1)

    def test_two_digit_hours_are_the_max_supported(self):
        # TIMESTAMP_RE caps hours at \d{1,2}, so a three-digit hour field
        # doesn't match at all rather than parsing as a large hour value.
        with self.assertRaises(SubtitleError):
            Timestamp.parse("123:00:00,000", line=1)


class ParseValidTests(unittest.TestCase):
    def test_single_cue(self):
        content = "1\n00:00:01,000 --> 00:00:04,000\nHello there.\n"
        cues = parse(content)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].index, 1)
        self.assertEqual(cues[0].start.to_ms(), 1000)
        self.assertEqual(cues[0].end.to_ms(), 4000)
        self.assertEqual(cues[0].text, "Hello there.")

    def test_multiple_cues_back_to_back(self):
        content = (
            "1\n00:00:01,000 --> 00:00:04,000\nHello there.\n"
            "\n"
            "2\n00:00:04,000 --> 00:00:06,000\nGeneral Kenobi.\n"
        )
        cues = parse(content)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[1].start.to_ms(), cues[0].end.to_ms())

    def test_multiline_cue_text_preserved(self):
        content = "1\n00:00:01,000 --> 00:00:04,000\nLine one\nLine two\n"
        cues = parse(content)
        self.assertEqual(cues[0].lines, ["Line one", "Line two"])
        self.assertEqual(cues[0].text, "Line one\nLine two")

    def test_crlf_line_endings(self):
        content = "1\r\n00:00:01,000 --> 00:00:04,000\r\nHello there.\r\n"
        cues = parse(content)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "Hello there.")

    def test_positioning_hint_after_end_timestamp_is_ignored(self):
        content = "1\n00:00:01,000 --> 00:00:04,000 X1:100 X2:200 Y1:0 Y2:50\nHello there.\n"
        cues = parse(content)
        self.assertEqual(cues[0].end.to_ms(), 4000)

    def test_zero_start_time_is_not_treated_as_overlap(self):
        # last_end_ms starts at -1 specifically so a cue starting at 0 is
        # allowed as the first cue in the file.
        content = "1\n00:00:00,000 --> 00:00:01,000\nHello.\n"
        cues = parse(content)
        self.assertEqual(cues[0].start.to_ms(), 0)


class ParseErrorTests(unittest.TestCase):
    def test_empty_file(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("")
        self.assertEqual(cm.exception.line, 1)

    def test_whitespace_only_file(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("\n\n\n")
        self.assertEqual(cm.exception.line, 1)

    def test_block_missing_timing_line(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("1\n\n")
        self.assertEqual(cm.exception.line, 1)
        self.assertIn("no timing line", str(cm.exception))

    def test_non_integer_index(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("one\n00:00:01,000 --> 00:00:04,000\ntext\n")
        self.assertEqual(cm.exception.line, 1)
        self.assertIn("cue number", str(cm.exception))

    def test_timing_line_missing_arrow(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("1\n00:00:01,000 - 00:00:04,000\ntext\n")
        self.assertEqual(cm.exception.line, 2)
        self.assertIn("timing line", str(cm.exception))

    def test_malformed_start_timestamp(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("1\nnot-a-time --> 00:00:04,000\ntext\n")
        self.assertEqual(cm.exception.line, 2)

    def test_malformed_end_timestamp(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("1\n00:00:01,000 --> not-a-time\ntext\n")
        self.assertEqual(cm.exception.line, 2)

    def test_end_equal_to_start(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("1\n00:00:05,000 --> 00:00:05,000\ntext\n")
        self.assertIn("not after its start", str(cm.exception))

    def test_end_before_start(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("1\n00:00:05,000 --> 00:00:01,000\ntext\n")
        self.assertIn("not after its start", str(cm.exception))

    def test_cue_starts_before_previous_ends(self):
        content = (
            "1\n00:00:00,000 --> 00:00:05,000\nHello.\n"
            "\n"
            "2\n00:00:04,000 --> 00:00:06,000\nWorld.\n"
        )
        with self.assertRaises(SubtitleError) as cm:
            parse(content)
        self.assertEqual(cm.exception.line, 6)
        self.assertIn("starts before the previous cue ends", str(cm.exception))

    def test_cue_with_no_text(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("1\n00:00:01,000 --> 00:00:04,000\n\n")
        self.assertEqual(cm.exception.line, 1)
        self.assertIn("no text", str(cm.exception))

    def test_error_message_includes_line_prefix(self):
        with self.assertRaises(SubtitleError) as cm:
            parse("one\n00:00:01,000 --> 00:00:04,000\ntext\n")
        self.assertTrue(str(cm.exception).startswith("line 1:"))


if __name__ == "__main__":
    unittest.main()
