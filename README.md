# Rei Project: Gemma-Aura 🌸

Rei Project adalah asisten AI virtual berbasis desktop yang ditenagai oleh model bahasa **Gemma 3** (melalui Ollama), lengkap dengan integrasi **Live2D** untuk visualisasi karakter, **STT (Speech-to-Text)** untuk input suara, dan **TTS (Text-to-Speech)** untuk output suara.

## 🚀 Fitur Utama

- **Visual Karakter Live2D**: Karakter "Rei" yang responsif dengan animasi ekspresi otomatis berdasarkan konteks pembicaraan.
- **Local AI (Gemma 3)**: Pemrosesan bahasa dilakukan secara lokal menggunakan Ollama untuk privasi dan kecepatan.
- **Input Suara (STT)**: Menggunakan Faster-Whisper untuk pengenalan suara Bahasa Indonesia yang akurat.
- **Output Suara (TTS)**: Menggunakan Piper TTS untuk sintesis suara yang natural secara offline.
- **Komunikasi Real-time**: Menggunakan WebSocket untuk interaksi yang mulus antara frontend Electron dan backend FastAPI.

## 🛠️ Prasyarat

Sebelum menjalankan sistem ini, pastikan Anda telah menginstal:

1.  **Node.js** (v18 atau lebih baru) & **NPM**.
2.  **Python** (v3.10 atau v3.11 direkomendasikan).
3.  **Ollama**: [Unduh di sini](https://ollama.com/).
4.  **Model Gemma 3**: Jalankan `ollama pull gemma3:4b` di terminal Anda.

## 📂 Struktur Proyek

- `/backend`: Server FastAPI (LLM, STT, TTS logic).
- `/electron`: Kode utama aplikasi desktop Electron.
- `/src`: Frontend web (Vite + PixiJS untuk Live2D).
- `/assets`: Model Live2D dan aset pendukung.

## ⚙️ Cara Menjalankan

### 1. Persiapan Backend (Python)

Buka terminal di folder root proyek dan jalankan:

```bash
# Pindah ke direktori backend (opsional, bisa jalankan dari root)
cd backend

# Install dependensi Python
pip install -r requirements.txt

# Jalankan server backend
python main.py
```
*Catatan: Backend akan berjalan di `ws://127.0.0.1:8765/ws`.*

### 2. Persiapan Frontend & Electron (Node.js)

Buka terminal baru di folder root proyek:

```bash
# Install dependensi NPM
npm install

# Jalankan aplikasi dalam mode pengembangan
npm run electron:dev
```

## 📝 Catatan Penting

- **Ollama**: Pastikan service Ollama sudah berjalan sebelum menjalankan backend.
- **Model TTS**: Pastikan file model `.onnx` untuk Piper TTS tersedia di folder `assets/tts-models/` sesuai konfigurasi di `backend/config.py`.
- **Live2D**: Jika karakter tidak muncul, pastikan file model Live2D ada di dalam folder `assets/model/`.

---
**Dikembangkan oleh Fawwaz**
