# Rangkuman & Eksekusi: Auto-Clipper YouTube & Smart Summarizer

Dokumen ini adalah panduan padat untuk membangun dan memonetisasi sistem pemotong video YouTube otomatis dengan alokasi sumber daya Hybrid (VPS Lite Rp70.000 + Laptop i5 Gen 11).

---

## 1. ROADMAP & BREAKDOWN PER TAHAP REALISTIS

Strategi ini membagi beban kerja secara efisien: **VPS bertugas 24/7 untuk kerja kasar (download, AI text, hardcut)**, sedangkan **Laptop bertugas untuk *finishing* (efek, caption, render).**

### Tahap 1: Setup Infrastruktur & Otomatisasi (Hari 1 - 3)
*Fokus: Membangun mesin pemotong otomatis (Backend) dengan sisa modal Rp72.000.*
*   **Beli VPS Lite (Rp70.000):** Spesifikasi 2 vCPU, 3 GB RAM, 40 GB NVMe.
*   **Setup Script Python di VPS:**
    *   Install `yt-dlp` untuk download video/audio.
    *   Install `FFmpeg` untuk deteksi senyap (*silencedetect*) dan potong instan (`-c copy`).
    *   Integrasikan **Google Gemini API** dengan logika *Multi-Key Rotation* (3 akun) agar gratis dan anti-limit.
*   **Output:** Telegram Bot yang menerima link YouTube dan mengirimkan kembali video *raw highlight* (potongan kasar tanpa jeda kosong).

### Tahap 2: Produksi & Monetisasi (Minggu 1 - 3)
*Fokus: Menghasilkan uang (Clipper Luar Negeri) dengan skill Video Editing (100/100).*
*   **Riset Niche:** Pilih podcast/streamer luar negeri dengan RPM/CPM tinggi (contoh: Finance, Self-Improvement, Tech Podcast).
*   **Finishing di Laptop (CapCut Pro):**
    *   Download *raw highlight* dari Telegram Bot.
    *   Ubah rasio ke 9:16 (Vertikal).
    *   Gunakan auto-caption bahasa Inggris, efek suara, dan *hook* 3 detik pertama.
*   **Distribusi:** Upload konsisten (2-3 klip/hari) ke YouTube Shorts, TikTok (US Region), dan IG Reels.
*   **Monetisasi:** YouTube Partner Program, Affiliate Marketing Luar Negeri, atau Clipper Program (Rumble/Kick).

### Tahap 3: Portofolio SaaS & Jasa Freelance (Minggu 4+)
*Fokus: Mengonversi script menjadi jasa layanan atau produk web.*
*   **Buka Jasa Clipper:** Jual jasa ekstrak video panjang di Fiverr/Upwork (harga $15 - $50 per podcast).
*   **Ekspansi Web App (Opsional):** Buat UI sederhana menggunakan Streamlit atau Vite/FastAPI untuk dijadikan portofolio *Web Dev* & *Backend Dev*.

---

## 2. PRODUCT REQUIREMENTS DOCUMENT (PRD) COMPACT

### Ringkasan Eksekutif
Sistem otomatis pencari momen dan pemotong jeda kosong (*silence removal*) pada video YouTube berdurasi panjang, dirancang berjalan efisien pada VPS *low-budget* dengan bantuan AI (Google Gemini API) secara gratis.

### Tujuan Utama
1.  **Otomatisasi Penuh:** Mengubah seleksi video manual menjadi hitungan menit via script.
2.  **Biaya Operasional Rp0 (setelah VPS):** Memanfaatkan rotasi 3 API Key Gemini bawaan akun gratis.
3.  **Kinerja Cepat:** Tanpa *re-encode* di VPS (murni *stream copy*).

### Spesifikasi Fitur Utama
1.  **YouTube Ingest:** Download konten via `yt-dlp`.
2.  **Gemini API Rotator:** Fungsi *Try-Catch* di Python untuk otomatis berpindah ke API Key 2 atau 3 jika Key 1 terkena *ResourceExhausted* (Rate Limit).
3.  **AI Moment Detector:** Ekstrak audio menjadi transkrip lengkap dengan *timestamp* untuk mendeteksi *viral moment/hook*.
4.  **FFmpeg Smart Hardcut:** Pemotongan klip cerdas dan pembuangan *blank/silence audio* (parameter `-c copy`).
5.  **Delivery System:** Pengiriman otomatis klip kasar ke pengguna melalui Telegram Bot.

### Tech Stack & Pembagian Resource
*   **Node 1: Server/Backend (VPS Lite 2vCPU, 3GB RAM)**
    *   *Tugas:* Downloader, LLM Caller, FFmpeg Cutter.
    *   *Teknologi:* Python, FastAPI, yt-dlp, FFmpeg, Gemini SDK.
*   **Node 2: Client/Frontend (Laptop i5 11th Gen + CapCut Pro)**
    *   *Tugas:* Rendering, transisi visual, teks dinamis.
    *   *Teknologi:* CapCut Pro (atau browser untuk web UI di masa depan).

### Batasan Teknis & Mitigasi Risiko
*   **Risiko:** VPS *Crash / Out of Memory* karena proses berat.
*   **Mitigasi 1:** **DILARANG** melakukan *re-encode/rendering* video di VPS. FFmpeg **wajib** menggunakan `-c copy`.
*   **Mitigasi 2:** Implementasi sistem antrean sederhana (*Queue*) pada Telegram Bot jika ada banyak request bersamaan.