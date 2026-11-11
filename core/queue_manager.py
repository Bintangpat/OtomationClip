import asyncio
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

from aiogram import Bot
from aiogram.types import FSInputFile

from core.config import Config
from core.downloader import Downloader
from core.gemini_rotator import GeminiRotator
from core.models import ProcessingJob, JobStatus, AnalysisResult
from core.video_editor import VideoEditor

logger = logging.getLogger(__name__)


class QueueManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.queue: asyncio.Queue[ProcessingJob] = asyncio.Queue()
        self.rotator = GeminiRotator()
        self.is_running = False
        self._worker_task: Optional[asyncio.Task] = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Auto-Clipper Queue Worker started.")

    async def stop(self):
        self.is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            logger.info("Auto-Clipper Queue Worker stopped.")

    async def enqueue(self, chat_id: int, url: str) -> ProcessingJob:
        job = ProcessingJob(
            job_id=str(uuid.uuid4())[:8],
            chat_id=chat_id,
            url=url,
            status=JobStatus.QUEUED
        )
        await self.queue.put(job)
        logger.info(f"Enqueued job {job.job_id} for chat {chat_id} (Queue size: {self.queue.qsize()})")
        return job

    async def _update_status(self, job: ProcessingJob, text: str):
        if job.status_message_id:
            try:
                await self.bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=job.status_message_id,
                    text=text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.debug(f"Could not update status message: {e}")

    async def _worker_loop(self):
        while self.is_running:
            job = await self.queue.get()
            job_dir = Config.TEMP_DIR / job.job_id
            output_dir = Config.OUTPUT_DIR / job.job_id

            try:
                job.status = JobStatus.FETCHING_INFO
                await self._update_status(
                    job,
                    f"📥 *[1/4] Mengunduh Transkrip & Metadata YouTube...*\n"
                    f"🔗 `{job.url}`\n"
                    f"_Mohon tunggu beberapa detik..._"
                )

                # 1. Fetch transcript or audio
                metadata, transcript, audio_path = await Downloader.fetch_info_and_transcript(job.url, job_dir)
                job.video_title = metadata.get("title", "Video YouTube")

                # 2. AI Analysis via Gemini Rotator
                job.status = JobStatus.ANALYZING_AI
                await self._update_status(
                    job,
                    f"🧠 *[2/4] AI Gemini Menganalisis Momen Emas...*\n"
                    f"🎬 *{job.video_title[:60]}...*\n"
                    f"_Mencari 1-{Config.MAX_HIGHLIGHTS} momen dengan retensi & hook tertinggi..._"
                )

                if transcript:
                    analysis = await self.rotator.analyze_transcript(job.video_title, transcript)
                else:
                    # If transcript wasn't found but audio was extracted
                    raise RuntimeError("Transkrip/subtitle video tidak tersedia untuk video ini.")

                job.analysis = analysis

                if not analysis.highlights:
                    raise RuntimeError("Gemini tidak menemukan segmen highlight yang memenuhi syarat durasi.")

                # 3. Download & Cut Highlights (Method B: Full source download + local fast cut)
                job.status = JobStatus.CUTTING_VIDEO
                total_clips = len(analysis.highlights)
                try:
                    output_dir.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    pass
                downloaded_clips = []

                # Step 3a: Download full source video via native yt-dlp (Bypasses FFmpeg 403 Forbidden)
                await self._update_status(
                    job,
                    f"📥 *[3/4] Mengunduh Video Sumber ({Config.PREFERRED_RESOLUTION}p)...*\n"
                    f"⚡ _Memanfaatkan kecepatan tinggi VPS & bebas 403 Forbidden..._"
                )
                source_video_path = job_dir / f"source_{job.job_id}.mp4"
                await Downloader.download_source_video(
                    url=job.url,
                    output_file=source_video_path,
                    resolution=Config.PREFERRED_RESOLUTION
                )

                # Step 3b: Cut clips locally via FFmpeg (instant, 0-risk of remote 403)
                for idx, hl in enumerate(analysis.highlights, start=1):
                    await self._update_status(
                        job,
                        f"✂️ *[3/4] Memotong Klip Highlight ({idx}/{total_clips})...*\n"
                        f"📌 *{hl.title}*\n"
                        f"⏱️ `{hl.start_time}` ➔ `{hl.end_time}` ({int(hl.duration_seconds)} detik)"
                    )

                    clip_filename = f"clip_{idx}_{job.job_id}.mp4"
                    clip_path = output_dir / clip_filename

                    # Add 1-second safety buffer for seamless dialogue cut
                    buffered_start = max(0.0, hl.start_seconds - 1.0)
                    duration = (hl.end_seconds + 1.0) - buffered_start

                    await VideoEditor.cut_clip_fast(
                        input_path=source_video_path,
                        output_path=clip_path,
                        start_seconds=buffered_start,
                        duration_seconds=duration
                    )

                    # Ensure <= 50MB for Telegram
                    final_clip_path = await VideoEditor.ensure_telegram_size_limit(clip_path)

                    # Generate preview thumbnail
                    thumb_path = output_dir / f"thumb_{idx}_{job.job_id}.jpg"
                    await VideoEditor.generate_thumbnail(final_clip_path, thumb_path)

                    downloaded_clips.append((hl, final_clip_path, thumb_path))

                # Immediately delete source video to conserve NVMe disk space
                if source_video_path.exists():
                    source_video_path.unlink(missing_ok=True)
                    logger.info(f"Cleaned up source video: {source_video_path.name}")

                # 4. Delivery to Telegram
                job.status = JobStatus.SENDING
                await self._update_status(
                    job,
                    f"🚀 *[4/4] Mengirimkan {len(downloaded_clips)} Klip Highlight ke Telegram...*"
                )

                for idx, (hl, clip_path, thumb_path) in enumerate(downloaded_clips, start=1):
                    caption = (
                        f"🎬 *KLIP #{idx}: {hl.title}*\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"⏱️ *Timestamp:* `{hl.start_time}` - `{hl.end_time}` ({int(hl.duration_seconds)}s)\n"
                        f"🔥 *Virality Score:* {hl.virality_score}/10\n"
                        f"🪝 *Hook 3 Detik:* \"_{hl.hook_text}_\"\n\n"
                        f"💡 *Alasan Menarik:* {hl.reason}\n\n"
                        f"📲 _Klip raw siap diimpor ke CapCut Pro untuk dijadikan format 9:16 vertical & auto-caption!_"
                    )

                    video_input = FSInputFile(str(clip_path))
                    thumb_input = FSInputFile(str(thumb_path)) if thumb_path.exists() else None

                    await self.bot.send_video(
                        chat_id=job.chat_id,
                        video=video_input,
                        thumbnail=thumb_input,
                        caption=caption,
                        parse_mode="Markdown"
                    )

                # Send completion message with summary
                summary_text = (
                    f"✅ *SELESAI! Semua klip berhasil diproses!*\n\n"
                    f"📋 *Ringkasan Podcast:*\n{analysis.video_summary}\n\n"
                    f"💡 *Langkah Finishing di Laptop (CapCut):*\n"
                    f"1. Download video di atas ke Laptop\n"
                    f"2. Buka CapCut, ubah Rasio ke 9:16 (Vertikal)\n"
                    f"3. Pasang Auto-Caption (English/Indo) & Sound Effect pada hook\n"
                    f"4. Ekspor dan upload ke YouTube Shorts / TikTok US!"
                )
                await self.bot.send_message(chat_id=job.chat_id, text=summary_text, parse_mode="Markdown")

                job.status = JobStatus.COMPLETED

            except Exception as e:
                logger.error(f"Error processing job {job.job_id}: {e}", exc_info=True)
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                error_alert = (
                    f"❌ *Gagal Memproses Video*\n\n"
                    f"⚠️ *Kendala:* `{str(e)[:300]}`\n\n"
                    f"🔍 *Tips:*\n"
                    f"• Pastikan video memiliki subtitle/transkrip publik di YouTube.\n"
                    f"• Jika video terlalu baru, YouTube mungkin belum selesai memproses auto-subtitlenya."
                )
                await self._update_status(job, error_alert)

            finally:
                # Cleanup temp & output files to protect 40 GB NVMe VPS
                shutil.rmtree(job_dir, ignore_errors=True)
                shutil.rmtree(output_dir, ignore_errors=True)
                self.queue.task_done()
                logger.info(f"Cleaned up directories for job {job.job_id}")
