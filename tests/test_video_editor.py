import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile
from core.video_editor import VideoEditor, get_ffmpeg_command, get_ffprobe_command


class TestVideoEditor(unittest.TestCase):
    def test_binary_commands(self):
        cmd = get_ffmpeg_command()
        self.assertTrue(isinstance(cmd, str) and len(cmd) > 0)

    def test_file_size_mb(self):
        with NamedTemporaryFile(delete=False) as f:
            f.write(b"0" * 1024 * 1024 * 2)  # 2 Megabytes
            path = Path(f.name)

        try:
            size_mb = VideoEditor.get_file_size_mb(path)
            self.assertAlmostEqual(size_mb, 2.0, places=1)
        finally:
            path.unlink(missing_ok=True)

    def test_silence_regex_parsing(self):
        mock_output = """
        [silencedetect @ 0x55d045d62980] silence_start: 12.45
        [silencedetect @ 0x55d045d62980] silence_end: 15.20 | silence_duration: 2.75
        [silencedetect @ 0x55d045d62980] silence_start: 45.10
        [silencedetect @ 0x55d045d62980] silence_end: 47.90 | silence_duration: 2.80
        """
        import re
        start_pattern = re.compile(r"silence_start:\s*([0-9.]+)")
        end_pattern = re.compile(r"silence_end:\s*([0-9.]+)")

        starts = [float(m) for m in start_pattern.findall(mock_output)]
        ends = [float(m) for m in end_pattern.findall(mock_output)]

        self.assertEqual(starts, [12.45, 45.10])
        self.assertEqual(ends, [15.20, 47.90])


if __name__ == "__main__":
    unittest.main()
