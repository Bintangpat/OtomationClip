Untuk mengeksekusi PRD tersebut melalui _code generator_ atau CLI dengan presisi tinggi, Anda membutuhkan **Technical Design Document (TDD)** atau **Spesifikasi Arsitektur Sistem**. Dokumen ini akan menjadi instruksi teknis mutlak (blueprint) bagi mesin atau developer untuk menulis kode tanpa menebak-nebak logika, struktur, atau perintah (command) spesifik yang digunakan.

Berikut adalah Dokumen Arsitektur Teknis detail yang bisa langsung Anda berikan ke sistem:

## **Technical Design Document (TDD): Auto-Clipper & Smart Summarizer**

### **1. Arsitektur Alur Data (Data Flow Architecture)**

Sistem berjalan secara _asynchronous_ untuk mencegah _blocking_ pada VPS 2 vCPU.

1. **Input Layer:** Telegram Bot menerima pesan berisi URL YouTube.
2. **Download Worker:** Sub-proses menjalankan `yt-dlp` untuk mengunduh media ke folder `/temp`.
3. **Analysis Layer:**

- Mengekstrak audio khusus untuk dianalisis.
- Modul Rotator API mengirim audio/transkrip ke Gemini API untuk deteksi momen penting.
- `ffmpeg silencedetect` berjalan di latar belakang untuk mendapatkan _timestamp_ jeda senyap.

4. **Processing Layer (The Hardcut Engine):** Python membuat file `concat.txt` berisi daftar _timestamp_ aktif, lalu FFmpeg mengeksekusi pemotongan dan penggabungan dengan parameter `-c copy`.
5. **Output Layer:** File hasil (.mp4) dikirim balik ke Telegram atau diunggah ke _cloud storage_, lalu folder `/temp` dibersihkan.

---

### **2. Struktur Direktori Proyek (File Tree)**

Sistem harus dibangun dengan struktur modular berikut:

```text
auto-clipper-bot/
├── core/
│   ├── downloader.py      # Wrapper untuk subprocess yt-dlp
│   ├── audio_analyzer.py  # Wrapper untuk subprocess FFmpeg silencedetect
│   ├── video_editor.py    # Wrapper untuk FFmpeg split & concat (-c copy)
│   └── gemini_rotator.py  # Logika array & try-catch untuk 3 API Key
├── bot/
│   └── telegram_app.py    # Handler pesan masuk & antrean (queue)
├── temp/                  # Folder I/O video mentah (auto-delete pasca proses)
├── output/                # Folder hasil potongan video
├── .env                   # Environment variables (API Keys, Bot Token)
├── requirements.txt       # Dependencies (aiogram, google-generativeai, dll)
└── main.py                # Entry point aplikasi

```

---

### **3. Spesifikasi Perintah Inti (Core Commands Subprocess)**

CLI/Developer wajib menggunakan argumen spesifik ini pada modul _backend_ untuk memastikan VPS tidak kelebihan beban (CPU tetap aman).

**A. yt-dlp Command (Download optimal)**
Unduh format MP4 atau resolusi maksimal 1080p agar kompatibel dengan editor CapCut.

```bash
yt-dlp -f "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best" --merge-output-format mp4 -o "temp/%(id)s.%(ext)s" "URL_YOUTUBE"

```

**B. FFmpeg Silence Detect (Deteksi Jeda Kosong)**
Memindai audio tanpa merender video. Ambang batas: -30dB, durasi di atas 1.5 detik.

```bash
ffmpeg -i input.mp4 -af silencedetect=noise=-30dB:d=1.5 -f null -

```

_(Backend Python bertugas melakukan Regex/Parsing pada output terminal (stdout) untuk menangkap angka `silence_start` dan `silence_end`)_.

**C. FFmpeg Hardcut & Concat (Zero Re-encoding)**
Karena menggunakan VPS 2 vCPU, dilarang keras menggunakan `filter_complex`. Pemotongan harus menggunakan `concat demuxer`.
_Langkah 1: Python membuat file `segments.txt` berdasarkan waktu yang ada suaranya:_

```text
file 'input.mp4'
inpoint 00:00:05.000
outpoint 00:01:20.000
file 'input.mp4'
inpoint 00:01:22.500
outpoint 00:05:00.000

```

_Langkah 2: Eksekusi FFmpeg:_

```bash
ffmpeg -f concat -safe 0 -i segments.txt -c copy output.mp4

```

---

### **4. Logika Multi-Key API Rotator (Gemini)**

Modul `gemini_rotator.py` harus menerapkan kelas atau fungsi dengan logika _Failover_ berikut:

1. Load `GEMINI_KEY_1`, `GEMINI_KEY_2`, `GEMINI_KEY_3` dari `.env` ke dalam sebuah array/list.
2. Simpan variabel `current_key_index = 0`.
3. Saat melakukan request (misal `model.generate_content`), bungkus dalam blok `try...except`.
4. Jika menangkap _Exception_ spesifik `ResourceExhausted` (Kode 429), lakukan iterasi:

- `current_key_index = (current_key_index + 1) % len(api_keys)`
- Konfigurasi ulang library dengan _key_ baru tersebut.
- Lakukan _retry_ request maksimal 3 kali sebelum melempar error _timeout_ ke user.

---

### **5. Lingkungan Eksekusi & Dependencies (VPS Setup)**

Untuk _deployment_ di server Ubuntu (VPS Lite Anda), spesifikasikan ini di terminal VPS:

- **System Binaries:** `sudo apt install ffmpeg yt-dlp python3-pip python3-venv`
- **Process Manager:** Wajib menggunakan `Systemd` atau `PM2` untuk menjaga `main.py` (Telegram Bot) menyala 24/7 dan _restart_ otomatis jika _crash_.
- **Python Dependencies (`requirements.txt`):**

```text
aiogram==3.*
google-generativeai
python-dotenv
asyncio

```

Gunakan dokumen teknis di atas dan gabungkan (copy-paste) bersama PRD sebelumnya saat Anda memberikan instruksi kepada AntiGravity CLI atau _coding assistant_ manapun. Spesifikasi detail (terutama di poin 3C dan 4) akan mencegah AI menulis kode yang salah atau terlalu membebani VPS Anda.
