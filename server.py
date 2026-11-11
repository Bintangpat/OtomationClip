import asyncio
import logging
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.config import Config
from core.downloader import Downloader
from core.gemini_rotator import GeminiRotator
from core.models import AnalysisResult, HighlightItem
from core.video_editor import VideoEditor

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AutoClipperWeb")

app = FastAPI(title="Auto-Clipper Web API", version="1.0.0")

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Rotator with configured keys
rotator = GeminiRotator()

# In-memory job store
jobs: Dict[str, Dict[str, Any]] = {}


class ProcessRequest(BaseModel):
    url: str
    resolution: int = 720


class JobStatusResponse(BaseModel):
    job_id: str
    url: str
    status: str
    progress: int
    current_step: str
    title: Optional[str] = None
    summary: Optional[str] = None
    highlights: List[Dict[str, Any]] = []
    clips: List[Dict[str, Any]] = []
    error: Optional[str] = None


async def run_pipeline_task(job_id: str, url: str, resolution: int):
    job = jobs[job_id]
    job_temp_dir = Config.TEMP_DIR / job_id
    output_dir = Config.OUTPUT_DIR

    try:
        job_temp_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        pass

    try:
        # Step 1: Subtitles & Metadata (15%)
        job["status"] = "processing"
        job["progress"] = 15
        job["current_step"] = "Mengambil Metadata & Subtitle YouTube..."
        logger.info(f"[{job_id}] Step 1: Fetching info & transcript for {url}")

        metadata, transcript, audio_fallback = await Downloader.fetch_info_and_transcript(url, job_temp_dir)
        video_title = metadata.get("title", "YouTube Video")
        video_duration = metadata.get("duration", 0)
        job["title"] = video_title

        if not transcript and not audio_fallback:
            raise RuntimeError("Transkrip/subtitle video tidak tersedia untuk video ini.")

        # Step 2: Gemini AI Analysis (40%)
        job["progress"] = 40
        job["current_step"] = "Menganalisis Momen Viral dengan Gemini AI..."
        logger.info(f"[{job_id}] Step 2: Gemini analysis")

        if transcript:
            analysis = await rotator.analyze_transcript_for_highlights(
                transcript_text=transcript,
                video_title=video_title,
                video_duration_seconds=video_duration
            )
        else:
            analysis = await rotator.analyze_audio_for_highlights(
                audio_path=audio_fallback,
                video_title=video_title,
                video_duration_seconds=video_duration
            )

        if not analysis.highlights:
            raise RuntimeError("Gemini tidak menemukan segmen highlight yang memenuhi syarat durasi.")

        job["summary"] = analysis.video_summary
        job["highlights"] = [hl.model_dump() for hl in analysis.highlights]

        # Step 3: Download Source Video via Native yt-dlp (65%)
        job["progress"] = 65
        job["current_step"] = f"Mengunduh Video Sumber ({resolution}p) secara Lokal..."
        logger.info(f"[{job_id}] Step 3: Downloading source video at {resolution}p")

        source_video_path = job_temp_dir / f"source_{job_id}.mp4"
        await Downloader.download_source_video(
            url=url,
            output_file=source_video_path,
            resolution=resolution
        )

        # Step 4: Cut Clips Locally via FFmpeg (85%)
        job["progress"] = 85
        total_clips = len(analysis.highlights)
        clips_data = []

        for idx, hl in enumerate(analysis.highlights, start=1):
            job["current_step"] = f"Memotong Klip #{idx} dari {total_clips}: {hl.title}..."
            logger.info(f"[{job_id}] Step 4: Cutting clip {idx}/{total_clips}")

            clip_filename = f"clip_{idx}_{job_id}.mp4"
            clip_path = output_dir / clip_filename

            # 1-second safety buffer
            buffered_start = max(0.0, hl.start_seconds - 1.0)
            duration = (hl.end_seconds + 1.0) - buffered_start

            await VideoEditor.cut_clip_fast(
                input_path=source_video_path,
                output_path=clip_path,
                start_seconds=buffered_start,
                duration_seconds=duration
            )

            # Ensure <= 48MB
            final_clip_path = await VideoEditor.ensure_telegram_size_limit(clip_path)

            # Generate preview thumbnail
            thumb_filename = f"thumb_{idx}_{job_id}.jpg"
            thumb_path = output_dir / thumb_filename
            await VideoEditor.generate_thumbnail(final_clip_path, thumb_path)

            file_size_mb = VideoEditor.get_file_size_mb(final_clip_path)

            clips_data.append({
                "clip_index": idx,
                "title": hl.title,
                "start_time": hl.start_time,
                "end_time": hl.end_time,
                "duration_seconds": hl.duration_seconds,
                "virality_score": hl.virality_score,
                "hook_text": hl.hook_text,
                "reason": hl.reason,
                "video_url": f"/api/media/{final_clip_path.name}",
                "thumbnail_url": f"/api/media/{thumb_filename}" if thumb_path.exists() else None,
                "filename": final_clip_path.name,
                "file_size_mb": round(file_size_mb, 2)
            })

        job["clips"] = clips_data

        # Delete source video immediately to free disk space
        if source_video_path.exists():
            source_video_path.unlink(missing_ok=True)

        job["status"] = "completed"
        job["progress"] = 100
        job["current_step"] = "Selesai! Klip siap ditonton & diimpor ke CapCut Pro."
        logger.info(f"[{job_id}] Pipeline completed successfully with {len(clips_data)} clips")

    except Exception as e:
        logger.exception(f"[{job_id}] Error in pipeline: {e}")
        job["status"] = "failed"
        job["error"] = str(e)
        job["current_step"] = f"Gagal: {str(e)[:150]}"
    finally:
        # Cleanup temporary files
        shutil.rmtree(job_temp_dir, ignore_errors=True)


@app.post("/api/process")
async def start_process(req: ProcessRequest, background_tasks: BackgroundTasks):
    url = req.url.strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="URL YouTube tidak valid.")

    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {
        "job_id": job_id,
        "url": url,
        "status": "pending",
        "progress": 5,
        "current_step": "Memulai proses...",
        "title": None,
        "summary": None,
        "highlights": [],
        "clips": [],
        "error": None
    }

    background_tasks.add_task(run_pipeline_task, job_id, url, req.resolution)
    return {"job_id": job_id, "status": "enqueued"}


@app.get("/api/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")
    return jobs[job_id]


@app.get("/api/jobs")
async def list_jobs():
    return list(jobs.values())


@app.get("/api/media/{filename}")
async def get_media_file(filename: str):
    # Prevent directory traversal
    safe_filename = Path(filename).name
    file_path = Config.OUTPUT_DIR / safe_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File media tidak ditemukan.")
    
    media_type = "video/mp4" if safe_filename.endswith(".mp4") else "image/jpeg"
    return FileResponse(file_path, media_type=media_type, filename=safe_filename)


@app.post("/api/open-output-folder")
async def open_output_folder():
    """Opens the output directory in Windows File Explorer directly on the Laptop."""
    output_dir = str(Config.OUTPUT_DIR.resolve())
    if sys.platform == "win32":
        os.startfile(output_dir)
        return {"status": "opened", "path": output_dir}
    elif sys.platform == "darwin":
        subprocess.run(["open", output_dir])
        return {"status": "opened", "path": output_dir}
    else:
        subprocess.run(["xdg-open", output_dir])
        return {"status": "opened", "path": output_dir}


@app.get("/api/info")
async def get_system_info():
    keys = Config.get_gemini_keys()
    cookies_path = Config.get_cookies_path()
    return {
        "gemini_keys_count": len(keys),
        "cookies_detected": bool(cookies_path and os.path.exists(cookies_path)),
        "output_directory": str(Config.OUTPUT_DIR.resolve()),
        "preferred_resolution": Config.PREFERRED_RESOLUTION,
        "status": "online"
    }


# Mount Vite production frontend if built
dist_dir = Config.BASE_DIR / "web" / "dist"
if dist_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    logger.info("==================================================")
    logger.info("   AUTO-CLIPPER WEB UI & LOCAL PROCESSOR")
    logger.info("   Buka browser di: http://127.0.0.1:8000")
    logger.info("==================================================")
    uvicorn.run(app, host="127.0.0.1", port=8000)
