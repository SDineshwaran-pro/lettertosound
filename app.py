"""
🎙 Free Indian Voice Text To MP3 Converter
--------------------------------------------
A 100% free, API-key-free, subscription-free Text-to-Speech web app built
entirely with Python + Streamlit.

Engines used (all free, no API keys required):
    1. edge-tts  -> High quality neural Indian voices (primary engine)
    2. gTTS      -> Google Translate TTS (automatic fallback)
    3. pyttsx3   -> Fully offline TTS (last-resort fallback)

NEW in this version:
    - Wider, stronger pitch/speed range for more dramatic voice control
    - Local, offline "AI-style" emotion analysis (lexicon + punctuation based
      NLP heuristics -- NOT a paid LLM/API) that automatically detects the
      emotional tone of each sentence and dynamically re-tunes pitch/speed
      per sentence, so the output sounds more expressive and human, rather
      than flat and robotic. This keeps the app 100% free and offline --
      a real hosted LLM/RAG pipeline would require a paid API key, which
      contradicts the "no API key / no paid service" requirement, so this
      app implements the same *effect* (context-aware prosody) using free,
      local NLP logic instead.
    - "🔊 Preview Voice" button to instantly hear a short sample of the
      selected voice/pitch/speed/tone before converting your full text.

Author: Generated for GitHub-ready deployment (Streamlit Cloud + local)
License: MIT
"""

import os
import re
import time
import uuid
import asyncio
import datetime
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Optional imports are wrapped so the app never hard-crashes if one engine
# is unavailable on a given platform (e.g. pyttsx3 has no audio driver on
# some cloud containers). We degrade gracefully instead.
# ---------------------------------------------------------------------------
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants & configuration
# ---------------------------------------------------------------------------
APP_TITLE = "🎙 Free Indian Voice Text To MP3 Converter"
TEMP_DIR = Path(__file__).parent / "temp_audio"
TEMP_DIR.mkdir(exist_ok=True)

MAX_CHARS = 5000              # soft limit shown to the user
FILE_MAX_AGE_SECONDS = 3600   # auto-cleanup files older than 1 hour
SENTENCE_GAP_MS = 160         # natural pause inserted between sentences

LANGUAGES = {
    "English (India)": "en",
    "Hindi": "hi",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Kannada": "kn",
    "Bengali": "bn",
}

# Native neural voices provided free by Microsoft Edge Read Aloud service
# (accessed via the open-source edge-tts library -- no API key required).
EDGE_VOICES = {
    "en": {"Indian Female": "en-IN-NeerjaNeural",   "Indian Male": "en-IN-PrabhatNeural"},
    "hi": {"Indian Female": "hi-IN-SwaraNeural",    "Indian Male": "hi-IN-MadhurNeural"},
    "ta": {"Indian Female": "ta-IN-PallaviNeural",  "Indian Male": "ta-IN-ValluvarNeural"},
    "te": {"Indian Female": "te-IN-ShrutiNeural",   "Indian Male": "te-IN-MohanNeural"},
    "ml": {"Indian Female": "ml-IN-SobhanaNeural",  "Indian Male": "ml-IN-MidhunNeural"},
    "kn": {"Indian Female": "kn-IN-SapnaNeural",    "Indian Male": "kn-IN-GaganNeural"},
    "bn": {"Indian Female": "bn-IN-TanishaaNeural", "Indian Male": "bn-IN-BashkarNeural"},
}

GTTS_LANG_MAP = {code: code for code in LANGUAGES.values()}

PREVIEW_TEXTS = {
    "en": "Hello! This is a quick preview of the selected voice.",
    "hi": "नमस्ते! यह चयनित आवाज़ का एक त्वरित पूर्वावलोकन है।",
    "ta": "வணக்கம்! இது தேர்ந்தெடுக்கப்பட்ட குரலின் விரைவு முன்னோட்டம்.",
    "te": "నమస్కారం! ఇది ఎంచుకున్న స్వరం యొక్క శీఘ్ర ప్రివ్యూ.",
    "ml": "നമസ്കാരം! ഇത് തിരഞ്ഞെടുത്ത ശബ്ദത്തിന്റെ ഒരു ദ്രുത പ്രിവ്യൂ ആണ്.",
    "kn": "ನಮಸ್ಕಾರ! ಇದು ಆಯ್ಕೆಮಾಡಿದ ಧ್ವನಿಯ ತ್ವರಿತ ಮುನ್ನೋಟ.",
    "bn": "নমস্কার! এটি নির্বাচিত ভয়েসের একটি দ্রুত প্রিভিউ।",
}

# --- Wider / stronger ranges than before, per user request ---
PITCH_MAP = {"Very Low": -80, "Low": -40, "Normal": 0, "High": 40, "Very High": 80}
RATE_MAP = {"Slow": -35, "Normal": 0, "Fast": 30, "Very Fast": 60}

# Tone presets nudge rate/pitch to emulate a "speaking style" since the
# free engines used here don't expose SSML speaking-styles.
TONE_ADJUST = {
    "Friendly":     {"rate": 8,   "pitch": 12},
    "Professional": {"rate": -8,  "pitch": -8},
    "Assistant":    {"rate": 0,   "pitch": 0},
    "Storytelling": {"rate": -12, "pitch": 15},
}

# Age / voice-simulation presets: applied as a post-processing pitch+speed
# transform on the generated audio using pydub (frame-rate resampling).
AGE_EFFECTS = {
    "Child Voice":  1.35,
    "Young Adult":  1.12,
    "Adult":        1.00,
    "Mature":       0.85,
}

PITCH_CLAMP = (-150, 150)
RATE_CLAMP = (-90, 100)

# ---------------------------------------------------------------------------
# Local, offline "AI-style" emotion detection engine
# (lexicon + punctuation heuristics -- free, no API key, no internet needed)
# ---------------------------------------------------------------------------
EMOTION_KEYWORDS = {
    "Happy":    ["happy", "glad", "joy", "wonderful", "great", "love", "amazing",
                 "delighted", "fantastic", "pleased", "awesome", "smile", "blessed"],
    "Excited":  ["excited", "thrilled", "can't wait", "yay", "woohoo", "amazing",
                 "incredible", "let's go", "finally"],
    "Sad":      ["sad", "sorry", "unfortunately", "miss", "lonely", "cry", "upset",
                 "heartbroken", "regret", "hurt", "disappointed", "grief"],
    "Angry":    ["angry", "furious", "hate", "annoyed", "mad", "rage", "frustrat",
                 "unacceptable", "outrageous", "disgust"],
    "Fear":     ["afraid", "scared", "worried", "nervous", "fear", "anxious",
                 "terrified", "panic", "danger", "threat"],
    "Surprise": ["wow", "surprised", "shocking", "unbelievable", "suddenly",
                 "astonishing", "no way", "really?"],
}

EMOTION_ADJUST = {
    "Happy":    {"pitch": 18,  "rate": 10},
    "Excited":  {"pitch": 28,  "rate": 18},
    "Sad":      {"pitch": -20, "rate": -15},
    "Angry":    {"pitch": -10, "rate": 15},
    "Fear":     {"pitch": 15,  "rate": 12},
    "Surprise": {"pitch": 30,  "rate": 8},
    "Neutral":  {"pitch": 0,   "rate": 0},
}

EMOTION_EMOJI = {
    "Happy": "😊", "Excited": "🤩", "Sad": "😢",
    "Angry": "😠", "Fear": "😨", "Surprise": "😲", "Neutral": "🙂",
}


def split_sentences(text):
    """Lightweight sentence splitter that keeps end punctuation for
    emotion cues (works reasonably across all supported languages,
    since Indic scripts also use '.', '!', '?', '।' as terminators)."""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r'(?<=[.!?।])\s+|\n+', text)
    return [p.strip() for p in parts if p.strip()]


def analyze_emotion(sentence):
    """Detect a dominant emotion for a sentence using free local heuristics:
    keyword lexicon matches + punctuation/capitalization cues. This mimics
    what an LLM sentiment pass would do, without needing any paid API."""
    lower = sentence.lower()
    scores = {emo: 0 for emo in EMOTION_ADJUST if emo != "Neutral"}

    for emo, words in EMOTION_KEYWORDS.items():
        for w in words:
            if w in lower:
                scores[emo] = scores.get(emo, 0) + 1

    exclam = sentence.count("!")
    quest = sentence.count("?")
    has_ellipsis = "..." in sentence or sentence.rstrip().endswith("..")
    words_only = re.sub(r'[^A-Za-z\s]', '', sentence)
    is_shout = len(words_only) > 4 and words_only.isupper()

    if exclam >= 1:
        scores["Excited"] += exclam
    if exclam >= 2 or is_shout:
        scores["Angry"] += 1
    if quest >= 1:
        scores["Surprise"] += 1
    if has_ellipsis:
        scores["Sad"] += 1

    best_emo = max(scores, key=scores.get)
    if scores[best_emo] == 0:
        return "Neutral"
    return best_emo


def combine_rate_pitch(base_rate, base_pitch, tone_label, emotion_label=None):
    """Combine base speed/pitch + tone preset + (optional) detected-emotion
    adjustment into final edge-tts rate/pitch strings, clamped to safe bounds."""
    rate_val = RATE_MAP[base_rate] + TONE_ADJUST[tone_label]["rate"]
    pitch_val = PITCH_MAP[base_pitch] + TONE_ADJUST[tone_label]["pitch"]

    if emotion_label and emotion_label in EMOTION_ADJUST:
        rate_val += EMOTION_ADJUST[emotion_label]["rate"]
        pitch_val += EMOTION_ADJUST[emotion_label]["pitch"]

    rate_val = max(RATE_CLAMP[0], min(RATE_CLAMP[1], rate_val))
    pitch_val = max(PITCH_CLAMP[0], min(PITCH_CLAMP[1], pitch_val))

    return f"{rate_val:+d}%", f"{pitch_val:+d}Hz"


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
def cleanup_old_files():
    now = time.time()
    for f in TEMP_DIR.glob("*.mp3"):
        try:
            if now - f.stat().st_mtime > FILE_MAX_AGE_SECONDS:
                f.unlink(missing_ok=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Core TTS engines
# ---------------------------------------------------------------------------
async def _edge_tts_save(text, voice, rate_str, pitch_str, output_path):
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate_str, pitch=pitch_str)
    await communicate.save(str(output_path))


def generate_with_edge_tts(text, voice, rate_str, pitch_str, output_path):
    if not EDGE_TTS_AVAILABLE:
        raise RuntimeError("edge-tts is not installed")
    asyncio.run(_edge_tts_save(text, voice, rate_str, pitch_str, output_path))
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("edge-tts produced an empty file")


def generate_with_gtts(text, lang_code, output_path):
    if not GTTS_AVAILABLE:
        raise RuntimeError("gTTS is not installed")
    tts = gTTS(text=text, lang=lang_code, slow=False)
    tts.save(str(output_path))
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("gTTS produced an empty file")


def generate_with_pyttsx3(text, output_path):
    if not PYTTSX3_AVAILABLE:
        raise RuntimeError("pyttsx3 is not installed")
    wav_path = output_path.with_suffix(".wav")
    engine = pyttsx3.init()
    engine.save_to_file(text, str(wav_path))
    engine.runAndWait()
    if not wav_path.exists() or wav_path.stat().st_size == 0:
        raise RuntimeError("pyttsx3 produced an empty file")
    if PYDUB_AVAILABLE:
        try:
            sound = AudioSegment.from_wav(str(wav_path))
            sound.export(str(output_path), format="mp3")
            wav_path.unlink(missing_ok=True)
            return
        except Exception:
            pass
    output_path.write_bytes(wav_path.read_bytes())
    wav_path.unlink(missing_ok=True)


def apply_age_effect(input_path, output_path, age_label):
    factor = AGE_EFFECTS.get(age_label, 1.0)
    if factor == 1.0 or not PYDUB_AVAILABLE:
        if input_path != output_path:
            output_path.write_bytes(input_path.read_bytes())
        return
    try:
        sound = AudioSegment.from_file(str(input_path), format="mp3")
        altered = sound._spawn(
            sound.raw_data,
            overrides={"frame_rate": int(sound.frame_rate * factor)},
        )
        altered = altered.set_frame_rate(44100)
        altered.export(str(output_path), format="mp3")
    except Exception:
        if input_path != output_path:
            output_path.write_bytes(input_path.read_bytes())


# ---------------------------------------------------------------------------
# Emotion-adaptive, per-sentence edge-tts synthesis (the "more human" path)
# ---------------------------------------------------------------------------
def generate_emotion_adaptive_edge_tts(text, voice, base_rate, base_pitch, tone_label,
                                        output_path, progress_cb=None):
    sentences = split_sentences(text)
    if not sentences:
        raise RuntimeError("No text to synthesize")

    seg_paths = []
    emotion_log = []
    total = len(sentences)

    for i, sentence in enumerate(sentences):
        emotion = analyze_emotion(sentence)
        emotion_log.append((sentence, emotion))
        rate_str, pitch_str = combine_rate_pitch(base_rate, base_pitch, tone_label, emotion)

        seg_path = TEMP_DIR / f"seg_{uuid.uuid4().hex[:8]}.mp3"
        generate_with_edge_tts(sentence, voice, rate_str, pitch_str, seg_path)
        seg_paths.append(seg_path)

        if progress_cb:
            pct = 20 + int(45 * (i + 1) / total)
            progress_cb(pct, f"Analyzing emotion & synthesizing sentence {i + 1}/{total} "
                              f"({EMOTION_EMOJI.get(emotion, '')} {emotion})...")

    # Stitch all sentence clips together
    if PYDUB_AVAILABLE:
        combined = AudioSegment.silent(duration=0)
        gap = AudioSegment.silent(duration=SENTENCE_GAP_MS)
        for sp in seg_paths:
            combined += AudioSegment.from_file(str(sp), format="mp3") + gap
        combined.export(str(output_path), format="mp3")
    else:
        with open(output_path, "wb") as out:
            for sp in seg_paths:
                out.write(Path(sp).read_bytes())

    for sp in seg_paths:
        Path(sp).unlink(missing_ok=True)

    return emotion_log


# ---------------------------------------------------------------------------
# Master conversion pipeline
# ---------------------------------------------------------------------------
def convert_text_to_speech(text, lang_code, gender, speed_label, pitch_label,
                            tone_label, age_label, engine_choice,
                            emotion_adaptive, progress_cb=None):
    """
    edge-tts (emotion-adaptive, per-sentence) -> edge-tts (flat) -> gTTS -> pyttsx3
    Returns (final_path, engine_used, warnings:list, emotion_log:list|None)
    """
    warnings = []
    uid = uuid.uuid4().hex[:10]
    raw_path = TEMP_DIR / f"raw_{uid}.mp3"
    final_path = TEMP_DIR / f"tts_{uid}.mp3"
    engine_used = None
    emotion_log = None

    voice = EDGE_VOICES.get(lang_code, {}).get(gender)
    base_rate_str, base_pitch_str = combine_rate_pitch(speed_label, pitch_label, tone_label)

    engines_to_try = ["edge-tts", "gTTS", "pyttsx3"] if engine_choice == "Auto (Recommended)" else [engine_choice]

    if progress_cb:
        progress_cb(8, "Preparing text...")

    for eng in engines_to_try:
        try:
            if eng == "edge-tts":
                if emotion_adaptive:
                    if progress_cb:
                        progress_cb(15, "Running local AI emotion analysis...")
                    emotion_log = generate_emotion_adaptive_edge_tts(
                        text, voice, speed_label, pitch_label, tone_label, raw_path, progress_cb
                    )
                    engine_used = "edge-tts (emotion-adaptive)"
                else:
                    if progress_cb:
                        progress_cb(35, "Synthesizing with edge-tts neural voice...")
                    generate_with_edge_tts(text, voice, base_rate_str, base_pitch_str, raw_path)
                    engine_used = "edge-tts"
                break
            elif eng == "gTTS":
                if progress_cb:
                    progress_cb(35, "Synthesizing with gTTS (fallback)...")
                generate_with_gtts(text, GTTS_LANG_MAP.get(lang_code, "en"), raw_path)
                engine_used = "gTTS"
                warnings.append("Used gTTS fallback: pitch/speed/tone/emotion controls are limited with this engine.")
                break
            elif eng == "pyttsx3":
                if progress_cb:
                    progress_cb(35, "Synthesizing offline with pyttsx3 (fallback)...")
                generate_with_pyttsx3(text, raw_path)
                engine_used = "pyttsx3"
                warnings.append("Used pyttsx3 offline fallback: language support limited to installed system voices.")
                break
        except Exception as e:
            warnings.append(f"{eng} failed: {e}")
            continue

    if engine_used is None:
        raise RuntimeError("All available TTS engines failed. " + " | ".join(warnings))

    if progress_cb:
        progress_cb(85, "Applying voice simulation effects...")
    apply_age_effect(raw_path, final_path, age_label)
    raw_path.unlink(missing_ok=True)

    if progress_cb:
        progress_cb(100, "Done!")

    return final_path, engine_used, warnings, emotion_log


def generate_preview(lang_code, gender, speed_label, pitch_label, tone_label, age_label, engine_choice):
    """Quick, flat (non-emotion) sample so the user can instantly hear the
    selected voice/pitch/speed/tone combination before converting real text."""
    sample_text = PREVIEW_TEXTS.get(lang_code, PREVIEW_TEXTS["en"])
    uid = uuid.uuid4().hex[:8]
    raw_path = TEMP_DIR / f"preview_raw_{uid}.mp3"
    final_path = TEMP_DIR / f"preview_{uid}.mp3"

    voice = EDGE_VOICES.get(lang_code, {}).get(gender)
    rate_str, pitch_str = combine_rate_pitch(speed_label, pitch_label, tone_label)

    engines_to_try = ["edge-tts", "gTTS", "pyttsx3"] if engine_choice == "Auto (Recommended)" else [engine_choice]
    used = None
    for eng in engines_to_try:
        try:
            if eng == "edge-tts":
                generate_with_edge_tts(sample_text, voice, rate_str, pitch_str, raw_path)
            elif eng == "gTTS":
                generate_with_gtts(sample_text, GTTS_LANG_MAP.get(lang_code, "en"), raw_path)
            elif eng == "pyttsx3":
                generate_with_pyttsx3(sample_text, raw_path)
            used = eng
            break
        except Exception:
            continue

    if used is None:
        raise RuntimeError("Preview generation failed on all engines.")

    apply_age_effect(raw_path, final_path, age_label)
    raw_path.unlink(missing_ok=True)
    return final_path, used


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Free Indian Voice Text To MP3 Converter",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1100px; }
    textarea { font-size: 16px !important; }
    .stButton>button { border-radius: 10px; font-weight: 600; padding: 0.5rem 1.2rem; }
    .char-counter { color: #888; font-size: 0.85rem; text-align: right; }
    .history-card {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
    }
    .emo-tag {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        background: rgba(128,128,128,0.15);
        font-size: 0.8rem;
        margin-bottom: 4px;
    }
    @media (max-width: 640px) {
        .block-container { padding-left: 0.6rem; padding-right: 0.6rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "text_input" not in st.session_state:
    st.session_state.text_input = ""
if "history" not in st.session_state:
    st.session_state.history = []
if "preview_audio" not in st.session_state:
    st.session_state.preview_audio = None

cleanup_old_files()

st.title(APP_TITLE)
st.caption(
    "100% Free • No API Key • No Subscription • Local AI Emotion-Adaptive Voice — "
    "powered by edge-tts, gTTS and pyttsx3."
)

# ---------------------------------------------------------------------------
# Sidebar - settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Voice Settings")

    language_label = st.selectbox("🌐 Language", list(LANGUAGES.keys()), index=0)
    lang_code = LANGUAGES[language_label]

    gender = st.radio("🗣️ Voice", ["Indian Female", "Indian Male"], horizontal=True)

    st.subheader("🎚️ Pitch")
    pitch_label = st.select_slider(
        "Pitch level", options=list(PITCH_MAP.keys()), value="Normal", label_visibility="collapsed"
    )

    st.subheader("⏩ Speed")
    speed_label = st.select_slider(
        "Speed level", options=list(RATE_MAP.keys()), value="Normal", label_visibility="collapsed"
    )

    st.subheader("🎭 Voice Tone")
    tone_label = st.selectbox("Tone", list(TONE_ADJUST.keys()), index=2, label_visibility="collapsed")

    st.subheader("🧒 Voice Simulation")
    age_label = st.selectbox("Age effect", list(AGE_EFFECTS.keys()), index=2, label_visibility="collapsed")

    st.divider()
    st.subheader("🧠 AI Emotion-Adaptive Voice")
    emotion_adaptive = st.toggle(
        "Auto-detect emotion per sentence",
        value=True,
        help=(
            "Analyzes each sentence locally (keyword + punctuation based NLP — "
            "free, offline, no API key) and automatically raises/lowers pitch & "
            "speed to sound happy, sad, excited, angry, fearful or surprised, "
            "instead of one flat robotic tone. Works best with edge-tts and "
            "English text; other languages get punctuation-based cues."
        ),
    )

    st.divider()
    st.subheader("🔧 Engine")
    engine_options = ["Auto (Recommended)"]
    if EDGE_TTS_AVAILABLE:
        engine_options.append("edge-tts")
    if GTTS_AVAILABLE:
        engine_options.append("gTTS")
    if PYTTSX3_AVAILABLE:
        engine_options.append("pyttsx3")
    engine_choice = st.selectbox("TTS Engine", engine_options, index=0)

    st.caption(
        "Auto mode tries **edge-tts** first (best quality, full pitch/speed/emotion control), "
        "then falls back to **gTTS**, then **pyttsx3** if needed."
    )

    if not PYDUB_AVAILABLE:
        st.warning("pydub/ffmpeg not detected — pitch effects & sentence stitching quality will be reduced.", icon="⚠️")

    st.divider()
    if st.button("🔊 Preview Voice", use_container_width=True):
        try:
            with st.spinner("Generating preview..."):
                prev_path, used_eng = generate_preview(
                    lang_code, gender, speed_label, pitch_label, tone_label, age_label, engine_choice
                )
            st.session_state.preview_audio = prev_path.read_bytes()
            st.caption(f"Preview engine: {used_eng}")
        except Exception as e:
            st.error(f"Preview failed: {e}")

    if st.session_state.preview_audio:
        st.audio(st.session_state.preview_audio, format="audio/mp3")

# ---------------------------------------------------------------------------
# Main - text input
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([3, 1])
with col_left:
    st.subheader("📝 Enter Text")
with col_right:
    uploaded_file = st.file_uploader("📄 Upload .txt", type=["txt"], label_visibility="collapsed")
    if uploaded_file is not None:
        try:
            st.session_state.text_input = uploaded_file.read().decode("utf-8", errors="ignore")
        except Exception as e:
            st.error(f"Could not read file: {e}")

text_value = st.text_area(
    "Text to convert",
    value=st.session_state.text_input,
    height=220,
    max_chars=MAX_CHARS,
    placeholder="Type or paste your text here (English, Hindi, Tamil, Telugu, Malayalam, Kannada or Bengali)...",
    label_visibility="collapsed",
    key="main_text_area",
)
st.session_state.text_input = text_value

char_count = len(text_value)
word_count = len(text_value.split()) if text_value.strip() else 0

meta_col1, meta_col2, meta_col3 = st.columns([1, 1, 2])
with meta_col1:
    st.markdown(f"<div class='char-counter'>🔤 {char_count} / {MAX_CHARS} characters</div>", unsafe_allow_html=True)
with meta_col2:
    st.markdown(f"<div class='char-counter'>📖 {word_count} words</div>", unsafe_allow_html=True)
with meta_col3:
    if st.button("🗑️ Clear Text"):
        st.session_state.text_input = ""
        st.rerun()

st.divider()
convert_col, _ = st.columns([1, 3])
with convert_col:
    convert_clicked = st.button("🎧 Convert to MP3", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Conversion workflow
# ---------------------------------------------------------------------------
if convert_clicked:
    clean_text = st.session_state.text_input.strip()
    if not clean_text:
        st.error("Please enter some text or upload a .txt file before converting.")
    elif len(clean_text) > MAX_CHARS:
        st.error(f"Text is too long. Please keep it under {MAX_CHARS} characters.")
    else:
        progress_bar = st.progress(0, text="Starting conversion...")
        status_placeholder = st.empty()

        def progress_cb(pct, msg):
            progress_bar.progress(min(pct, 100), text=msg)
            status_placeholder.info(f"⏳ {msg}")

        try:
            with st.spinner("Generating audio, please wait..."):
                final_path, engine_used, warns, emotion_log = convert_text_to_speech(
                    clean_text, lang_code, gender, speed_label, pitch_label,
                    tone_label, age_label, engine_choice, emotion_adaptive,
                    progress_cb=progress_cb,
                )

            status_placeholder.empty()
            progress_bar.empty()
            st.success(f"✅ Conversion complete using **{engine_used}**!")

            for w in warns:
                st.warning(w, icon="⚠️")

            audio_bytes = final_path.read_bytes()
            st.audio(audio_bytes, format="audio/mp3")

            st.download_button(
                label="⬇️ Download MP3",
                data=audio_bytes,
                file_name=f"tts_{lang_code}_{int(time.time())}.mp3",
                mime="audio/mp3",
                use_container_width=True,
            )

            if emotion_log:
                with st.expander("🧠 View Detected Emotion Per Sentence"):
                    for sent, emo in emotion_log:
                        st.markdown(
                            f"<span class='emo-tag'>{EMOTION_EMOJI.get(emo, '')} {emo}</span> {sent}",
                            unsafe_allow_html=True,
                        )

            st.session_state.history.insert(0, {
                "text_snippet": clean_text[:80] + ("..." if len(clean_text) > 80 else ""),
                "file_path": str(final_path),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "language": language_label,
                "voice": gender,
                "engine": engine_used,
            })
            st.session_state.history = st.session_state.history[:15]

        except Exception as e:
            status_placeholder.empty()
            progress_bar.empty()
            st.error(f"❌ Conversion failed: {e}")

# ---------------------------------------------------------------------------
# History section
# ---------------------------------------------------------------------------
st.divider()
hist_header_col, hist_clear_col = st.columns([3, 1])
with hist_header_col:
    st.subheader("🕘 Generated Audio History")
with hist_clear_col:
    if st.session_state.history and st.button("🧹 Clear History"):
        for item in st.session_state.history:
            try:
                Path(item["file_path"]).unlink(missing_ok=True)
            except Exception:
                pass
        st.session_state.history = []
        st.rerun()

if not st.session_state.history:
    st.caption("No audio generated yet in this session.")
else:
    for idx, item in enumerate(st.session_state.history):
        fpath = Path(item["file_path"])
        with st.container():
            st.markdown("<div class='history-card'>", unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(
                    f"**{item['timestamp']}** &nbsp;|&nbsp; {item['language']} &nbsp;|&nbsp; "
                    f"{item['voice']} &nbsp;|&nbsp; _{item['engine']}_"
                )
                st.caption(f"“{item['text_snippet']}”")
                if fpath.exists():
                    st.audio(fpath.read_bytes(), format="audio/mp3")
                else:
                    st.caption("⚠️ File expired / cleaned up.")
            with c2:
                if fpath.exists():
                    st.download_button(
                        "⬇️ Download",
                        data=fpath.read_bytes(),
                        file_name=fpath.name,
                        mime="audio/mp3",
                        key=f"dl_{idx}",
                        use_container_width=True,
                    )
            st.markdown("</div>", unsafe_allow_html=True)

st.divider()
st.caption(
    "Built with ❤️ using Streamlit, edge-tts, gTTS and pyttsx3 — no API keys, "
    "no paid services, 100% free and open source. Emotion analysis runs fully "
    "locally using free NLP heuristics — no LLM API calls are made."
)
