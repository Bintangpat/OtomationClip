import unittest
from core.gemini_rotator import GeminiRotator


class TestRotator(unittest.TestCase):
    def test_key_rotation(self):
        keys = ["KEY_A", "KEY_B", "KEY_C"]
        rotator = GeminiRotator(api_keys=keys)

        self.assertEqual(rotator.current_key, "KEY_A")
        rotator.rotate_key()
        self.assertEqual(rotator.current_key, "KEY_B")
        rotator.rotate_key()
        self.assertEqual(rotator.current_key, "KEY_C")
        rotator.rotate_key()
        self.assertEqual(rotator.current_key, "KEY_A")

    def test_clean_json_text(self):
        rotator = GeminiRotator(api_keys=["DUMMY"])
        markdown_wrapped = '```json\n{"video_summary": "Test", "highlights": []}\n```'
        cleaned = rotator._clean_json_text(markdown_wrapped)
        self.assertEqual(cleaned, '{"video_summary": "Test", "highlights": []}')

    def test_fallback_parse_highlights(self):
        rotator = GeminiRotator(api_keys=["DUMMY"])
        raw_text = 'Here is the result you requested:\n{"video_summary": "Good podcast", "highlights": [{"title": "Tip 1", "start_time": "00:01:00", "end_time": "00:01:45", "hook_text": "Look at this", "virality_score": 9, "reason": "Awesome"}]}\nHope this helps!'
        res = rotator._fallback_parse_highlights(raw_text, "My Podcast")
        self.assertEqual(res.video_title, "My Podcast")
        self.assertEqual(res.video_summary, "Good podcast")
        self.assertEqual(len(res.highlights), 1)
        self.assertEqual(res.highlights[0].title, "Tip 1")


if __name__ == "__main__":
    unittest.main()
