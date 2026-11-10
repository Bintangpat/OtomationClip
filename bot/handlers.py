import re
import logging
from aiogram import Router, types
from aiogram.filters import Command

from core.queue_manager import QueueManager

logger = logging.getLogger(__name__)
router = Router(name="main_router")

# Global reference assigned during bot setup
queue_manager: QueueManager = None

YOUTUBE_URL_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|live\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)


def set_queue_manager(qm: QueueManager):
    global queue_manager
    queue_manager = qm


@router.message(Command("start"))
async def handle_start(message: types.Message):
    welcome_text = (
        "🤖 *Selamat Datang di Auto-Clipper Bot!* 🎬\n\n"
        "Saya adalah asisten otomatis pemotong video podcast & YouTube panjang menjadi *viral highlight clips* "
        "siap edit untuk YouTube Shorts, TikTok, dan Instagram Reels.\n\n"
        "✨ *Keunggulan Sistem:*\n"
        "• 🧠 *AI Gemini Rotator:* Mendeteksi hook 3 detik & momen paling berharga.\n"
        "• ⚡ *Smart Section Cutter:* Mengunduh langsung potongan klip terbaik tanpa boros kuota.\n"
        "• 🚀 *Telegram Delivery:* Klip dikirim langsung ke chat ini.\n\n"
        "📌 *Cara Penggunaan:*\n"
        "Cukup kirimkan tautan YouTube (contoh: podcast Joe Rogan, Lex Fridman, Deddy Corbuzier, dll) ke chat ini!"
    )
    await message.answer(welcome_text, parse_mode="Markdown")


@router.message(Command("help"))
async def handle_help(message: types.Message):
    help_text = (
        "📖 *Panduan Penggunaan Auto-Clipper Bot*\n\n"
        "1️⃣ **Kirim Link:** Kirim link video YouTube berdurasi minimal 5 menit.\n"
        "2️⃣ **Tunggu Notifikasi:** Bot akan memproses video melalui 4 tahap (Metadata ➔ Analisis AI ➔ Pemotongan ➔ Pengiriman).\n"
        "3️⃣ **Finishing di CapCut:** Buka klip yang dikirimkan di laptop, ubah ke rasio 9:16 vertikal, dan tambahkan auto-caption.\n\n"
        "❓ *Kendala Umum:*\n"
        "• *'Transkrip tidak tersedia'*: Video YouTube harus memiliki subtitle (bisa auto-generated bahasa Inggris atau Indonesia).\n"
        "• *Durasi klip*: Rata-rata 30-90 detik per highlight."
    )
    await message.answer(help_text, parse_mode="Markdown")


@router.message()
async def handle_incoming_message(message: types.Message):
    text = (message.text or "").strip()
    match = YOUTUBE_URL_REGEX.search(text)

    if not match:
        await message.answer(
            "⚠️ *Tautan tidak valid.*\n\nSilakan kirimkan tautan video YouTube yang sah (contoh: `https://www.youtube.com/watch?v=...` atau `https://youtu.be/...`).",
            parse_mode="Markdown"
        )
        return

    youtube_url = match.group(0)

    if not queue_manager:
        await message.answer("❌ Sistem antrean sedang tidak aktif. Coba beberapa saat lagi.")
        return

    status_msg = await message.answer(
        "⏳ *Tautan diterima! Menambahkan tugas ke antrean...*\n"
        f"🔗 `{youtube_url}`",
        parse_mode="Markdown"
    )

    job = await queue_manager.enqueue(chat_id=message.chat.id, url=youtube_url)
    job.status_message_id = status_msg.message_id
