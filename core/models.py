from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


def parse_timestamp_to_seconds(ts: str) -> float:
    """Converts HH:MM:SS or MM:SS or SSS timestamp strings into float seconds."""
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    try:
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 1:
            return float(parts[0])
    except ValueError:
        return 0.0
    return 0.0


def format_seconds_to_timestamp(seconds: float) -> str:
    """Formats float seconds into HH:MM:SS format."""
    total_sec = int(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class HighlightItem(BaseModel):
    title: str = Field(..., description="Catchy title for the YouTube Shorts / TikTok clip")
    start_time: str = Field(..., description="Start timestamp in HH:MM:SS or MM:SS format")
    end_time: str = Field(..., description="End timestamp in HH:MM:SS or MM:SS format")
    hook_text: str = Field(..., description="First 3-5 seconds attention-grabbing hook sentence")
    virality_score: int = Field(default=8, ge=1, le=10, description="Estimated virality potential from 1 to 10")
    reason: str = Field(default="", description="Why this segment is engaging or shareable")

    @property
    def start_seconds(self) -> float:
        return parse_timestamp_to_seconds(self.start_time)

    @property
    def end_seconds(self) -> float:
        return parse_timestamp_to_seconds(self.end_time)

    @property
    def duration_seconds(self) -> float:
        dur = self.end_seconds - self.start_seconds
        return max(0.0, dur)


class AnalysisResult(BaseModel):
    video_title: str = Field(default="YouTube Video", description="Original video title")
    video_summary: str = Field(default="", description="Brief summary of the entire video content")
    highlights: List[HighlightItem] = Field(default_factory=list, description="Top viral highlights")


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    FETCHING_INFO = "FETCHING_INFO"
    ANALYZING_AI = "ANALYZING_AI"
    CUTTING_VIDEO = "CUTTING_VIDEO"
    SENDING = "SENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ProcessingJob(BaseModel):
    job_id: str
    chat_id: int
    url: str
    status: JobStatus = JobStatus.QUEUED
    status_message_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    video_title: str = ""
    analysis: Optional[AnalysisResult] = None
    output_files: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
