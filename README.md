# Auto-Clipper YouTube & Smart Summarizer Bot 🎬🤖

Sistem otomatis pemotong video YouTube panjang (podcast, webinar, wawancara) menjadi klip highlight pendek (*viral shorts/reels/TikTok*) berbasis Telegram Bot, didukung oleh rotasi multi-akun **Google Gemini API Free Tier** dan **FFmpeg Stream Optimization** untuk berjalan efisien pada **VPS Lite (2 vCPU, 3 GB RAM, 40 GB NVMe)**.

---

## 🚀 Fitur Utama & Keunggulan Arsitektur

1. **Transcript-First Smart Section Download:**
   * Alih-alih mengunduh video 2 jam penuh (berukuran 3–6 GB), sistem hanya mengunduh teks subtitle (~50 KB) dalam 1 detik.
   * AI Gemini menganalisis transkrip dan menentukan 1–3 timestamp momen paling potensial.
   * `yt-dlp` kemudian hanya mengunduh segmen 30–90 detik tersebut (~20 MB). **Menghemat 95% kuota VPS & waktu proses!**
2. **Multi-Key Gemini Failover:**
   * Mendukung hingga 3+ API Key Gemini gratis secara bergantian (*Round-Robin Failover*). Jika Key 1 terkena Rate Limit (429), sistem otomatis berpindah ke Key 2 dan Key 3.
3. **Zero A/V Desync & Anti-Batas Telegram (50 MB):**
   * Pemotongan presisi pada batas keyframe.
   * Pengecekan ukuran file otomatis: jika klip melebihi limit 50 MB Telegram, sistem menerapkan kompresi instan (*ultrafast preset*) agar tetap terkirim mulus ke chat pengguna.
4. **Asynchronous Task Queue:**
   * Menggunakan `asyncio.Queue` (Concurrency = 1) untuk menjaga CPU 2 vCPU VPS tetap stabil tanpa resiko *crash* saat menerima banyak link sekaligus.
   * Live message progress update di Telegram chat pengguna.
5. **Auto-Cleanup Lifecycle:**
   * File sementara di direktori `temp/` dan `output/` langsung dihapus setelah pengiriman selesai untuk menjaga NVMe 40 GB tetap lega.

---

## 📁 Struktur Direktori

```text
auto-clipper-bot/
├── core/
│   ├── config.py              # Konfigurasi Pydantic / dotenv (API Keys, limits)
│   ├── models.py              # Skema data (HighlightItem, AnalysisResult, JobStatus)
│   ├── downloader.py          # Wrapper yt-dlp (Transcript first + Smart section dl)
│   ├── transcript_extractor.py# Parser WebVTT & deduplikasi auto-caption YouTube
│   ├── gemini_rotator.py      # Multi-key failover manager dengan Gemini 2.0 / 1.5 Flash
│   ├── video_editor.py        # FFmpeg smart cutter, thumbnailer, dan file size optimizer
│   └── queue_manager.py       # Asynchronous queue worker & Telegram status updater
├── bot/
│   ├── handlers.py            # Handler /start, /help, dan YouTube URL regex listener
│   └── telegram_app.py        # Factory inisialisasi aiogram bot & dispatcher
├── tests/
│   ├── test_models.py         # Unit test validasi skema data & durasi
│   ├── test_transcript.py     # Unit test parser VTT & transkrip
│   ├── test_rotator.py        # Unit test rotasi key & fallback JSON
│   └── test_video_editor.py   # Unit test FFmpeg size & silence regex
├── temp/                      # Folder file sementara per job (auto-purge)
├── output/                    # Folder klip hasil potongan (auto-purge)
├── setup_vps.sh               # Skrip instalasi otomatis untuk server Ubuntu
├── auto-clipper.service       # Service unit Systemd untuk VPS 24/7
├── ecosystem.config.js        # Konfigurasi PM2 Process Manager
├── requirements.txt           # Dependensi Python
├── .env.example               # Template environment variables
└── main.py                    # Entry point aplikasi
```

---

## ⚙️ Panduan Instalasi di VPS (Ubuntu 22.04 / 24.04)

### 1. Jalankan Skrip Setup Otomatis
```bash
git clone <repo-anda> /root/Resilience
cd /root/Resilience
chmod +x setup_vps.sh
./setup_vps.sh
```

### 2. Konfigurasi Environment (`.env`)
Salin file template dan masukkan API Keys Anda:
```bash
cp .env.example .env
nano .env
```

Isi variabel berikut:
```ini
TELEGRAM_BOT_TOKEN=123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ
ALLOWED_USER_ID=123456789
GEMINI_KEY_1=AIzaSy...
GEMINI_KEY_2=AIzaSy...
GEMINI_KEY_3=AIzaSy...
```
*(Kunci API Gemini gratis dapat dibuat di [Google AI Studio](https://aistudio.google.com/)).*

### 3. Jalankan Aplikasi

**Opsi A: Menggunakan Systemd (Rekomendasi 24/7):**
```bash
sudo cp auto-clipper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable auto-clipper
sudo systemctl start auto-clipper
sudo systemctl status auto-clipper
```

**Opsi B: Menggunakan PM2:**
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

**Opsi C: Menjalankan Langsung (Testing):**
```bash
source .venv/bin/activate
python3 main.py
```

---

## 🧪 Menjalankan Unit Tests
Untuk memverifikasi fungsionalitas seluruh modul:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 🎨 Alur Kerja Finishing di Laptop (Node 2: CapCut Pro)

1. Kirim tautan video YouTube (podcast/wawancara) ke Telegram Bot Anda.
2. Bot akan mengirimkan 1–3 file video `.mp4` (durasi 30–90 detik) lengkap dengan hook teks 3 detik pertama dan skor viralitas.
3. Unduh video dari Telegram ke Laptop Anda.
4. Buka **CapCut Pro**:
   * Ubah rasio kanvas ke **9:16 (Vertikal)**.
   * Aktifkan **Auto-Caption** (Bahasa Inggris atau Indonesia) dengan animasi dinamis.
   * Tambahkan sound effect (whoosh/pop) pada kalimat *hook* 3 detik pertama.
5. Ekspor dan distribusikan ke YouTube Shorts, TikTok, dan Instagram Reels!
