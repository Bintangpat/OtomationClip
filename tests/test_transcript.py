import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from core.transcript_extractor import parse_vtt_file, format_cues_into_timestamped_transcript, clean_vtt_line

SAMPLE_VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.500
<c>Welcome</c> to the podcast everyone.

00:00:03.500 --> 00:00:06.000
Welcome to the podcast everyone. Today we are talking about

00:00:06.000 --> 00:00:09.200
Today we are talking about artificial intelligence and money.

00:00:25.000 --> 00:00:28.000
The biggest secret is that most people give up

00:00:28.000 --> 00:00:31.000
right before they achieve their breakthrough.
"""


class TestTranscript(unittest.TestCase):
    def test_clean_vtt_line(self):
        line = "<c>Hello</c> <font color='red'>world</font>"
        self.assertEqual(clean_vtt_line(line), "Hello world")

    def test_parse_vtt_and_deduplicate(self):
        with TemporaryDirectory() as tmp_dir:
            vtt_file = Path(tmp_dir) / "sample.vtt"
            vtt_file.write_text(SAMPLE_VTT, encoding="utf-8")

            cues = parse_vtt_file(vtt_file)
            self.assertGreater(len(cues), 0)

            # Test formatting
            formatted = format_cues_into_timestamped_transcript(cues, group_interval_seconds=15)
            self.assertIn("[00:00:01]", formatted)
            self.assertIn("Welcome to the podcast everyone", formatted)
            self.assertIn("breakthrough", formatted)


if __name__ == "__main__":
    unittest.main()
