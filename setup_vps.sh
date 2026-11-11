#!/usr/bin/env bash
# ========================================================
# Auto-Clipper Setup Script for VPS Lite (Ubuntu 22.04/24.04)
# ========================================================

set -e

echo "🚀 Memulai Setup Auto-Clipper Server..."

# 1. Update package list & install system dependencies (termasuk nodejs untuk JS challenge YouTube)
echo "📦 Menginstall dependency sistem (ffmpeg, nodejs, python3-venv)..."
sudo apt update -y
sudo apt install -y ffmpeg python3-pip python3-venv git curl nodejs

# Hapus yt-dlp lama dari apt (jika pernah terinstall) agar tidak bentrok
sudo apt remove -y yt-dlp 2>/dev/null || true

# 2. Setup Virtual Environment
echo "🐍 Menyiapkan Virtual Environment Python & yt-dlp terbaru..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install --upgrade yt-dlp

# 3. Setup Direktori Kerja
echo "📁 Menyiapkan direktori temp & output..."
mkdir -p temp output

# 4. Cek file .env
if [ ! -f ".env" ]; then
    echo "⚠️ File .env belum ditemukan! Menyalin dari .env.example..."
    cp .env.example .env
    echo "👉 Harap edit file .env (nano .env) dan masukkan TELEGRAM_BOT_TOKEN serta GEMINI_KEY Anda."
fi

echo "========================================================"
echo "✅ Setup Selesai!"
echo "Untuk update library kapanpun di VPS: source .venv/bin/activate && pip install --upgrade yt-dlp"
echo "Untuk menjalankan manual: source .venv/bin/activate && python3 main.py"
echo "Untuk menjalankan 24/7 via Systemd: sudo systemctl restart auto-clipper"
echo "========================================================"
