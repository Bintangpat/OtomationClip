import json
import logging
import re
from pathlib import Path
from typing import List, Optional

from core.config import Config
from core.models import AnalysisResult, HighlightItem

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an elite viral video editor and content strategist specializing in YouTube Shorts, TikTok, and Instagram Reels.
Your task is to analyze the provided video transcript (with timestamps) and identify the top most engaging, high-retention highlights suitable for 9:16 vertical video conversion.

CRITERIA FOR VIRAL CLIPS:
1. Strong Opening Hook (0-5s): A provocative question, controversial claim, shock factor, or intense curiosity gap.
2. High Value Density: Dense insights, personal revelations, intense debate, or actionable wisdom.
3. Coherent Narrative Arc: Must have a clear beginning and logical conclusion without cutting off mid-thought or mid-sentence.
4. Target Duration: Each clip duration must be between {min_duration} and {max_duration} seconds.

Output ONLY a raw valid JSON object (no markdown code blocks, no extra commentary) with this exact structure:
{{
  "video_summary": "Concise summary of the overall video theme",
  "highlights": [
    {{
      "title": "Short punchy title for TikTok/Shorts (max 6 words)",
      "start_time": "HH:MM:SS",
      "end_time": "HH:MM:SS",
      "hook_text": "Exact first sentence that hooks the viewer",
      "virality_score": 9,
      "reason": "Why this specific moment will capture attention"
    }}
  ]
}}
"""


class GeminiRotator:
    def __init__(self, api_keys: Optional[List[str]] = None, model_name: Optional[str] = None):
        self.api_keys = api_keys if api_keys is not None else Config.get_gemini_keys()
        self.model_name = model_name or Config.GEMINI_MODEL
        self.current_index = 0

    @property
    def current_key(self) -> str:
        if not self.api_keys:
            raise ValueError("No Gemini API keys found in configuration (.env).")
        return self.api_keys[self.current_index]

    def rotate_key(self):
        if not self.api_keys:
            return
        old_idx = self.current_index
        self.current_index = (self.current_index + 1) % len(self.api_keys)
        logger.warning(
            f"Rotated Gemini API Key from index {old_idx} to index {self.current_index} (total keys: {len(self.api_keys)})"
        )

    def _clean_json_text(self, text: str) -> str:
        """Removes markdown code block formatting (```json ... ```) if returned by LLM."""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()

    async def analyze_transcript(
        self,
        video_title: str,
        transcript_text: str,
        max_highlights: Optional[int] = None,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None
    ) -> AnalysisResult:
        """
        Sends transcript to Gemini with multi-key failover and parses structured highlights.
        """
        max_h = max_highlights or Config.MAX_HIGHLIGHTS
        min_d = min_duration or Config.MIN_CLIP_DURATION
        max_d = max_duration or Config.MAX_CLIP_DURATION

        prompt = (
            f"{SYSTEM_PROMPT.format(min_duration=min_d, max_duration=max_d)}\n\n"
            f"VIDEO TITLE: {video_title}\n"
            f"DESIRED NUMBER OF CLIPS: {max_h}\n\n"
            f"TIMESTAMPED TRANSCRIPT:\n{transcript_text}"
        )

        raw_response = await self._execute_with_rotation(prompt)
        cleaned_json = self._clean_json_text(raw_response)

        try:
            data = json.loads(cleaned_json)
            result = AnalysisResult(**data)
            result.video_title = video_title
            return result
        except Exception as e:
            logger.error(f"Failed to parse Gemini JSON output: {e}\nRaw output was:\n{raw_response}")
            # Fallback regex extraction if full JSON parsing fails
            return self._fallback_parse_highlights(cleaned_json, video_title)

    async def _execute_with_rotation(self, prompt: str) -> str:
        """
        Executes generation using available Gemini SDK (google-genai or google-generativeai)
        with automatic failover on 429 / ResourceExhausted errors.
        """
        attempts = 0
        max_attempts = max(3, len(self.api_keys))

        while attempts < max_attempts:
            key = self.current_key
            attempts += 1
            try:
                # 1. Try modern google-genai SDK
                try:
                    from google import genai
                    from google.genai import types

                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.3,
                            response_mime_type="application/json"
                        )
                    )
                    if response and response.text:
                        return response.text
                except ImportError:
                    pass

                # 2. Try legacy google-generativeai SDK
                import google.generativeai as legacy_genai

                legacy_genai.configure(api_key=key)
                model = legacy_genai.GenerativeModel(
                    self.model_name,
                    generation_config={"temperature": 0.3, "response_mime_type": "application/json"}
                )
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text

                raise RuntimeError("No response returned from Gemini API.")

            except Exception as e:
                err_str = str(e).lower()
                is_quota_error = (
                    "429" in err_str
                    or "resourceexhausted" in err_str
                    or "quota" in err_str
                    or "rate limit" in err_str
                    or "503" in err_str
                    or "unavailable" in err_str
                )
                logger.warning(f"Gemini API attempt {attempts} failed with key index {self.current_index}: {e}")

                if is_quota_error or len(self.api_keys) > 1:
                    self.rotate_key()
                else:
                    raise e

        raise RuntimeError(f"All Gemini API keys exhausted after {attempts} attempts.")

    def _fallback_parse_highlights(self, raw_text: str, video_title: str) -> AnalysisResult:
        """Tolerant parser in case LLM output has mild syntax formatting flaws."""
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                res = AnalysisResult(**data)
                res.video_title = video_title
                return res
            except Exception:
                pass

        # Return minimal safe placeholder if completely unparseable
        return AnalysisResult(
            video_title=video_title,
            video_summary="Highlight summary unavailable",
            highlights=[
                HighlightItem(
                    title="Featured Highlight",
                    start_time="00:01:00",
                    end_time="00:02:00",
                    hook_text="Check out this key moment from the podcast",
                    virality_score=8,
                    reason="Automated fallback segment"
                )
            ]
        )
