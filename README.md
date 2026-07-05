# 🎙 Free Indian Voice Text To MP3 Converter

A **100% free**, **no API key**, **no subscription** Text-to-Speech web app built with **Python + Streamlit**.
Convert text into natural-sounding Indian-voice MP3 audio in English, Hindi, Tamil, Telugu, Malayalam, Kannada, and Bengali — right in your browser, running locally or free on Streamlit Cloud.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)
![License](https://img.shields.io/badge/License-MIT-green)
![Free](https://img.shields.io/badge/Cost-%240%20Forever-brightgreen)

---

## ✨ Features

- **Text Input:** Large text area, live character/word counter, clear button, `.txt` file upload
- **7 Languages:** English (India), Hindi, Tamil, Telugu, Malayalam, Kannada, Bengali
- **Voice Selection:** Indian Female / Indian Male neural voices
- **Pitch Control:** Very Low → Very High
- **Speed Control:** Slow → Very Fast
- **Voice Tone:** Friendly, Professional, Assistant, Storytelling
- **Voice Simulation:** Child, Young Adult, Adult, Mature voice effects
- **Audio Output:** MP3 generation, in-browser player preview, one-click download
- **Session History:** Revisit and re-download previously generated clips
- **Automatic Engine Fallback:** edge-tts → gTTS → pyttsx3, so it always works even if one engine is unavailable
- **Modern, Responsive UI:** Mobile and desktop friendly, sidebar settings panel
- **Progress Bar & Loading States** during audio generation
- **Automatic Temp File Cleanup** (files older than 1 hour are purged)

---

## 🆓 100% Free Stack — No API Keys, Ever

| Engine     | Type                       | Notes                                                              |
|------------|----------------------------|---------------------------------------------------------------------|
| `edge-tts` | Free neural TTS (primary)  | Uses Microsoft Edge's public "Read Aloud" voices, no key required   |
| `gTTS`     | Free TTS (fallback #1)     | Uses Google Translate's public TTS endpoint, no key required        |
| `pyttsx3`  | Offline TTS (fallback #2)  | Fully offline, uses your OS's installed voices, works with no internet |

There is **no OpenAI, ElevenLabs, Google Cloud, or Azure API used anywhere** in this project.

---

## 📁 Project Structure

```
TextToMP3/
│
├── app.py                # Main Streamlit application
├── requirements.txt       # Python dependencies
├── packages.txt           # System packages for Streamlit Cloud (ffmpeg, espeak-ng)
├── README.md               # This file
├── .gitignore
├── temp_audio/            # Generated MP3s (auto-cleaned, gitignored)
└── assets/                # Static assets (icons, screenshots, etc.)
```

---

## 🚀 Getting Started (Local)

### 1. Clone the repository
```bash
git clone https://github.com/username/TextToMP3.git
cd TextToMP3
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Install system dependencies
`pydub` (used for voice-simulation pitch effects) requires **ffmpeg**, and `pyttsx3` on Linux requires **espeak/espeak-ng**.

- **Windows:** Download ffmpeg from https://ffmpeg.org/download.html and add it to PATH. `pyttsx3` uses SAPI5 out of the box — no extra install needed.
- **macOS:** `brew install ffmpeg`  (pyttsx3 uses the built-in NSSpeechSynthesizer)
- **Linux (Debian/Ubuntu):** `sudo apt-get install ffmpeg espeak-ng`

> If ffmpeg is not installed, the app still works — it will simply skip the voice-simulation pitch effect and use the base generated audio.

### 5. Run the app
```bash
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

---

## ☁️ Deploying on Streamlit Cloud (Free)

1. Push this project to a **public GitHub repository** (see Git commands below).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, select your repository, branch (`main`), and set the main file path to `app.py`.
4. Click **Deploy**.

Streamlit Cloud automatically reads `requirements.txt` (Python packages) and `packages.txt` (system packages like `ffmpeg`/`espeak-ng`) — no extra configuration needed.

> **Note:** `pyttsx3` relies on OS-level speech engines. On Streamlit Cloud's Linux containers it will use `espeak-ng` (installed via `packages.txt`), which supports English well but has limited quality/support for Indian languages. This is why `edge-tts` is used as the primary engine and `pyttsx3` is only a last-resort fallback.

---

## 🖥️ How to Use

1. Select your **Language** and **Voice (Female/Male)** from the sidebar.
2. Adjust **Pitch**, **Speed**, **Tone**, and **Voice Simulation** to your liking.
3. Type or paste text into the text box (or upload a `.txt` file).
4. Click **🎧 Convert to MP3**.
5. Preview the audio in the built-in player, then **⬇️ Download MP3**.
6. All generated clips are saved in the **History** section for the duration of your session.

---

## 🛠️ Tech Stack

- [Streamlit](https://streamlit.io/) — Web UI framework
- [edge-tts](https://github.com/rany2/edge-tts) — Free neural TTS engine
- [gTTS](https://github.com/pndurette/gTTS) — Free Google Translate TTS
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3) — Offline TTS engine
- [pydub](https://github.com/jiaaro/pydub) — Audio post-processing (pitch/speed effects)

---

## 📦 Git Commands to Publish This Project

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/username/TextToMP3.git
git push -u origin main
```

Replace `username` with your GitHub username (and `TextToMP3` with your repo name, if different).

---

## ⚠️ Disclaimer

This project relies on free, publicly available TTS services (`edge-tts`'s access to Microsoft's Read Aloud voices, and `gTTS`'s access to Google Translate's TTS endpoint). These are unofficial, community-maintained wrappers around public services and not official paid APIs — availability may vary based on network conditions and upstream service changes. No account, API key, or payment is required to use them.

---

## 📄 License

MIT License — free to use, modify, and distribute.
