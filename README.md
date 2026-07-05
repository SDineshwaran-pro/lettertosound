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
- **🔊 Voice Preview:** Instantly hear a short sample with your current voice/pitch/speed/tone settings before converting your full text
- **Stronger Pitch Control:** Wider, more audible range — Very Low (‑80Hz) → Very High (+80Hz)
- **Stronger Speed Control:** Slow (‑35%) → Very Fast (+60%)
- **Voice Tone:** Friendly, Professional, Assistant, Storytelling
- **🧠 AI Emotion-Adaptive Voice:** Automatically analyzes the emotional tone of *each sentence* — locally, offline, no API key — and dynamically raises/lowers pitch & speed per sentence (happy/excited lines sound brighter and faster, sad lines sound lower and slower, angry lines get sharper emphasis, surprised lines lift in pitch). Produces noticeably more expressive, human-sounding narration instead of one flat monotone. Toggle on/off in the sidebar; view the detected emotion for every sentence after conversion.
- **Voice Simulation:** Child, Young Adult, Adult, Mature age-voice effects
- **Audio Output:** MP3 generation, in-browser player preview, one-click download
- **Session History:** Revisit and re-download previously generated clips
- **Automatic Engine Fallback:** edge-tts (emotion-adaptive) → edge-tts (flat) → gTTS → pyttsx3, so it always works even if one engine is unavailable
- **Modern, Responsive UI:** Mobile and desktop friendly, sidebar settings panel
- **Progress Bar & Loading States** during audio generation, with live per-sentence status
- **Automatic Temp File Cleanup** (files older than 1 hour are purged)

---

## 🆓 100% Free Stack — No API Keys, Ever

| Component  | Type                        | Notes                                                                  |
|------------|-----------------------------|-------------------------------------------------------------------------|
| `edge-tts` | Free neural TTS (primary)   | Uses Microsoft Edge's public "Read Aloud" voices, no key required       |
| `gTTS`     | Free TTS (fallback #1)      | Uses Google Translate's public TTS endpoint, no key required            |
| `pyttsx3`  | Offline TTS (fallback #2)   | Fully offline, uses your OS's installed voices, works with no internet  |
| Emotion engine | Local NLP heuristics    | Pure-Python keyword lexicon + punctuation rules, ships with the app — no internet call, no model download |

There is **no OpenAI, ElevenLabs, Google Cloud, or Azure API used anywhere** in this project.

### 🧠 About the "AI Emotion-Adaptive Voice"

A genuine LLM/RAG sentiment pipeline would mean calling a hosted AI API — which requires an API key and, in nearly every real-world case, a paid usage tier. Since this project's hard requirement is **zero API keys and zero paid services**, the emotion engine is built as **local, offline NLP logic** instead:

1. Input text is split into sentences.
2. Each sentence is scored against a small **emotion keyword lexicon** (happy, excited, sad, angry, fear, surprise) plus **punctuation/capitalization cues** (`!`, `?`, `...`, ALL CAPS).
3. The dominant detected emotion maps to a pitch/speed adjustment, layered on top of your manual pitch/speed/tone sliders for that sentence only.
4. Each sentence is synthesized individually by `edge-tts` at its own tuned pitch/rate, then stitched back together with short natural pauses using `pydub`.

This runs entirely on your machine/server (aside from the TTS engines' own free public endpoints) with no external AI API calls. It works best on English text since the keyword lexicon is English-only; other languages still benefit from the punctuation-based cues. You can turn it off anytime with the sidebar toggle to get flat, uniform narration instead.

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
`pydub` (used for the emotion-adaptive sentence stitching and voice-simulation pitch effects) requires **ffmpeg**, and `pyttsx3` on Linux requires **espeak/espeak-ng**.

- **Windows:** Download ffmpeg from https://ffmpeg.org/download.html and add it to PATH. `pyttsx3` uses SAPI5 out of the box — no extra install needed.
- **macOS:** `brew install ffmpeg` (pyttsx3 uses the built-in NSSpeechSynthesizer)
- **Linux (Debian/Ubuntu):** `sudo apt-get install ffmpeg espeak-ng`

> If ffmpeg is not installed, the app still works — it will simply skip the pitch/stitching effects and concatenate raw audio instead.

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
2. Adjust **Pitch**, **Speed**, **Tone**, and **Voice Simulation**, then click **🔊 Preview Voice** to hear a quick sample.
3. Toggle **AI Emotion-Adaptive Voice** on (default) for expressive, sentence-aware narration, or off for flat, uniform speech.
4. Type or paste text into the text box (or upload a `.txt` file).
5. Click **🎧 Convert to MP3**.
6. Preview the full audio, expand **🧠 View Detected Emotion Per Sentence** to see how each line was interpreted, then **⬇️ Download MP3**.
7. All generated clips are saved in the **History** section for the duration of your session.

---

## 🛠️ Tech Stack

- [Streamlit](https://streamlit.io/) — Web UI framework
- [edge-tts](https://github.com/rany2/edge-tts) — Free neural TTS engine
- [gTTS](https://github.com/pndurette/gTTS) — Free Google Translate TTS
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3) — Offline TTS engine
- [pydub](https://github.com/jiaaro/pydub) — Audio post-processing & sentence stitching

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

This project relies on free, publicly available TTS services (`edge-tts`'s access to Microsoft's Read Aloud voices, and `gTTS`'s access to Google Translate's TTS endpoint). These are unofficial, community-maintained wrappers around public services and not official paid APIs — availability may vary based on network conditions and upstream service changes. No account, API key, or payment is required to use them. The emotion-detection logic is a simple local heuristic, not a trained sentiment model — treat its labels as approximate.

---

## 📄 License

MIT License — free to use, modify, and distribute.
