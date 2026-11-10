import re
from pathlib import Path
from typing import List, Dict, Tuple


def clean_vtt_line(line: str) -> str:
    """Removes HTML/styling tags from WebVTT lines."""
    line = re.sub(r"<[^>]+>", "", line)
    return line.strip()


def parse_vtt_file(vtt_path: Path) -> List[Dict[str, str]]:
    """
    Parses a WebVTT (.vtt) file into a list of cues:
    [{'start': '00:01:23.000', 'end': '00:01:25.000', 'text': '...'}]
    Handles YouTube rolling auto-captions by deduplicating adjacent cues.
    """
    if not vtt_path.exists():
        return []

    content = vtt_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()

    timestamp_regex = re.compile(
        r"(\d{2}:\d{2}(?::\d{2})?(?:\.\d{3})?)\s*-->\s*(\d{2}:\d{2}(?::\d{2})?(?:\.\d{3})?)"
    )

    cues: List[Dict[str, str]] = []
    current_start = ""
    current_end = ""
    current_text_lines = []

    for line in lines:
        match = timestamp_regex.search(line)
        if match:
            # Save previous cue if any
            if current_start and current_text_lines:
                combined_text = " ".join(current_text_lines).strip()
                if combined_text:
                    cues.append({
                        "start": current_start,
                        "end": current_end,
                        "text": combined_text
                    })
            current_start = match.group(1)
            current_end = match.group(2)
            current_text_lines = []
        elif current_start:
            cleaned = clean_vtt_line(line)
            # Filter out WebVTT header lines or empty lines
            if cleaned and not cleaned.startswith("WEBVTT") and not cleaned.startswith("Kind:") and not cleaned.startswith("Language:"):
                # Avoid exact duplicate of immediate previous line
                if not current_text_lines or current_text_lines[-1] != cleaned:
                    current_text_lines.append(cleaned)

    # Add last cue
    if current_start and current_text_lines:
        combined_text = " ".join(current_text_lines).strip()
        if combined_text:
            cues.append({
                "start": current_start,
                "end": current_end,
                "text": combined_text
            })

    return cues


def format_cues_into_timestamped_transcript(cues: List[Dict[str, str]], group_interval_seconds: int = 20) -> str:
    """
    Groups granular subtitle cues into compact timestamped paragraphs every ~20 seconds
    to prevent repetitive tokens and give LLM perfect context.
    Example output:
    [00:01:20] Hey everyone welcome back today we are discussing the future of AI.
    [00:01:40] And specifically why small models are beating the giants.
    """
    if not cues:
        return ""

    from core.models import parse_timestamp_to_seconds, format_seconds_to_timestamp

    grouped_blocks: List[str] = []
    current_block_start = cues[0]["start"]
    current_block_start_sec = parse_timestamp_to_seconds(current_block_start)
    current_block_words: List[str] = []
    seen_phrases = set()

    for cue in cues:
        cue_start_sec = parse_timestamp_to_seconds(cue["start"])
        text = cue["text"]

        # Deduplicate continuous rolling text from YouTube
        if text in seen_phrases:
            continue
        seen_phrases.add(text)

        current_block_words.append(text)

        if cue_start_sec - current_block_start_sec >= group_interval_seconds:
            ts_str = format_seconds_to_timestamp(current_block_start_sec)
            block_content = " ".join(current_block_words).strip()
            if block_content:
                grouped_blocks.append(f"[{ts_str}] {block_content}")
            
            # Reset for next interval
            current_block_start_sec = cue_start_sec
            current_block_words = []
            seen_phrases.clear()

    # Append any remaining words
    if current_block_words:
        ts_str = format_seconds_to_timestamp(current_block_start_sec)
        block_content = " ".join(current_block_words).strip()
        if block_content:
            grouped_blocks.append(f"[{ts_str}] {block_content}")

    return "\n".join(grouped_blocks)
