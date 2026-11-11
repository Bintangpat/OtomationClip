import asyncio
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from core.config import Config
from core.transcript_extractor import parse_vtt_file, format_cues_into_timestamped_transcript

logger = logging.getLogger(__name__)

BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def get_ytdlp_command() -> list:
    """
    Returns command list to invoke yt-dlp.
    Prioritizes python module in virtualenv (sys.executable -m yt_dlp)
    to prevent invoking obsolete system packages (e.g. apt yt-dlp from 2022).
    """
    return [sys.executable, "-m", "yt_dlp"]


class Downloader:
    @staticmethod
    def _get_base_ytdlp_args() -> list:
        args = [
            "--no-warnings",
            "--no-playlist",
            "--no-check-certificates",
            "--user-agent", BROWSER_USER_AGENT,
            "--socket-timeout", "30",
        ]
        cookies_file = Config.get_cookies_path()
        if cookies_file and os.path.exists(cookies_file):
            args.extend(["--cookies", cookies_file])
        return args

    @classmethod
    async def fetch_info_and_transcript(cls, url: str, job_dir: Path) -> Tuple[Dict[str, Any], Optional[str], Optional[Path]]:
        """
        Fetches video metadata and downloads subtitles using a 2-step process:
        Step 1: Dump JSON metadata.
        Step 2: Download subtitle files to disk (without --dump-json so files are actually written).
        Returns:
            (metadata_dict, transcript_text, audio_fallback_path)
        """
        try:
            job_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass
        base_cmd = get_ytdlp_command()
        
        # 1. Fetch JSON metadata
        meta_cmd = [
            *base_cmd,
            *cls._get_base_ytdlp_args(),
            "--skip-download",
            "--ignore-no-formats-error",
            "--dump-json",
            url
        ]

        logger.info(f"Fetching metadata for {url}")
        meta_proc = await asyncio.create_subprocess_exec(
            *meta_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await meta_proc.communicate()

        if meta_proc.returncode != 0:
            err_msg = stderr.decode(errors="ignore").strip()
            logger.error(f"yt-dlp failed to fetch info: {err_msg}")
            raise RuntimeError(f"Gagal membaca video YouTube: {err_msg[:200]}")

        # Parse JSON from stdout
        metadata = {}
        for line in stdout.decode(errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    metadata = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if not metadata:
            raise RuntimeError("Gagal memproses metadata video dari YouTube.")

        # 2. Download subtitles to disk (Separate command without --dump-json)
        sub_cmd = [
            *base_cmd,
            *cls._get_base_ytdlp_args(),
            "--skip-download",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "id,id-orig,en,en-orig",
            "--sub-format", "vtt",
            "-o", str(job_dir / "%(id)s.%(ext)s"),
            url
        ]

        logger.info(f"Downloading subtitles for {url}")
        sub_proc = await asyncio.create_subprocess_exec(
            *sub_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await sub_proc.communicate()

        # 3. Check for downloaded VTT files
        vtt_files = list(job_dir.glob("*.vtt"))
        transcript_text = None

        if vtt_files:
            # Sort by file size descending (largest file is usually the most complete)
            vtt_files.sort(key=lambda p: p.stat().st_size, reverse=True)
            selected_vtt = vtt_files[0]

            # Prefer Indonesian or English native
            for vtt in vtt_files:
                name_lower = vtt.name.lower()
                if ".id." in name_lower or ".id-orig." in name_lower:
                    selected_vtt = vtt
                    break
                elif ".en." in name_lower or ".en-orig." in name_lower:
                    selected_vtt = vtt
            
            logger.info(f"Found {len(vtt_files)} subtitle file(s). Selected: {selected_vtt.name} ({selected_vtt.stat().st_size} bytes)")
            cues = parse_vtt_file(selected_vtt)
            transcript_text = format_cues_into_timestamped_transcript(cues)

        # 4. Fallback: If no subtitles exist, download lightweight audio
        audio_path = None
        if not transcript_text:
            logger.info("No subtitles found. Downloading lightweight audio for AI analysis fallback...")
            audio_cmd = [
                *base_cmd,
                *cls._get_base_ytdlp_args(),
                "-f", "ba/b",
                "-x",
                "--audio-format", "m4a",
                "-o", str(job_dir / "audio.%(ext)s"),
                url
            ]
            audio_proc = await asyncio.create_subprocess_exec(
                *audio_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await audio_proc.communicate()

            created_audios = list(job_dir.glob("audio.*"))
            if created_audios:
                audio_path = created_audios[0]
            else:
                logger.warning("Could not download audio fallback.")
                audio_path = None

        return metadata, transcript_text, audio_path

    @classmethod
    async def download_section(
        cls,
        url: str,
        start_sec: float,
        end_sec: float,
        output_file: Path,
        resolution: int = 720
    ) -> Path:
        """
        Downloads ONLY the specific highlight section using yt-dlp --download-sections.
        """
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass
        base_cmd = get_ytdlp_command()

        # Add 1 second buffer before and after for clean cut
        buffered_start = max(0.0, start_sec - 1.0)
        buffered_end = end_sec + 1.0

        section_arg = f"*{buffered_start:.1f}-{buffered_end:.1f}"

        format_spec = (
            f"bestvideo[height<={resolution}]+bestaudio/"
            f"best[height<={resolution}]/"
            f"best"
        )

        cmd = [
            *base_cmd,
            *cls._get_base_ytdlp_args(),
            "--download-sections", section_arg,
            "-f", format_spec,
            "--merge-output-format", "mp4",
            "--force-keyframes-at-cuts",
            "-o", str(output_file),
            url
        ]

        logger.info(f"Downloading section {section_arg} to {output_file.name}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode != 0 or not output_file.exists():
            err_msg = stderr.decode(errors="ignore").strip()
            logger.error(f"Failed to download section: {err_msg}")
            raise RuntimeError(f"Gagal mengunduh klip video: {err_msg[:200]}")

        return output_file
