import unittest
from core.models import (
    parse_timestamp_to_seconds,
    format_seconds_to_timestamp,
    HighlightItem,
    AnalysisResult
)


class TestModels(unittest.TestCase):
    def test_parse_timestamp_to_seconds(self):
        self.assertEqual(parse_timestamp_to_seconds("00:00:15"), 15.0)
        self.assertEqual(parse_timestamp_to_seconds("01:30"), 90.0)
        self.assertEqual(parse_timestamp_to_seconds("01:05:20"), 3920.0)
        self.assertEqual(parse_timestamp_to_seconds("00:01:23.500"), 83.5)
        self.assertEqual(parse_timestamp_to_seconds("invalid"), 0.0)

    def test_format_seconds_to_timestamp(self):
        self.assertEqual(format_seconds_to_timestamp(15), "00:00:15")
        self.assertEqual(format_seconds_to_timestamp(90), "00:01:30")
        self.assertEqual(format_seconds_to_timestamp(3920), "01:05:20")

    def test_highlight_item_properties(self):
        item = HighlightItem(
            title="Cara Cepat Kaya",
            start_time="00:02:10",
            end_time="00:03:25",
            hook_text="Jangan pernah simpan uangmu di bank sebelum dengar ini!",
            virality_score=9,
            reason="Provokatif dan aplikatif"
        )
        self.assertEqual(item.start_seconds, 130.0)
        self.assertEqual(item.end_seconds, 205.0)
        self.assertEqual(item.duration_seconds, 75.0)

    def test_analysis_result_validation(self):
        data = {
            "video_summary": "Diskusi mendalam tentang masa depan AI dan otomatisasi.",
            "highlights": [
                {
                    "title": "Masa Depan AI",
                    "start_time": "00:10:00",
                    "end_time": "00:11:15",
                    "hook_text": "AI akan mengubah 80 persen pekerjaan dalam 3 tahun.",
                    "virality_score": 10,
                    "reason": "Statistik mengejutkan"
                }
            ]
        }
        result = AnalysisResult(**data)
        self.assertEqual(len(result.highlights), 1)
        self.assertEqual(result.highlights[0].virality_score, 10)
        self.assertEqual(result.highlights[0].duration_seconds, 75.0)


if __name__ == "__main__":
    unittest.main()
