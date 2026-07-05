"""
🎙 Free Indian Voice Text To MP3 Converter
--------------------------------------------
A 100% free, API-key-free, subscription-free Text-to-Speech web app built
entirely with Python + Streamlit.

Engines used (all free, no API keys required):
    1. edge-tts  -> High quality neural Indian voices (primary engine)
    2. gTTS      -> Google Translate TTS (automatic fallback)
    3. pyttsx3   -> Fully offline TTS (last-resort fallback)

Author: Generated for GitHub-ready deployment (Streamlit Cloud + local)
License: MIT
"""

import os
import io
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

MAX_CHARS = 5000          # soft limit shown to the user
FILE_MAX_AGE_SECONDS = 3600  # auto-cleanup files older than 1 hour

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

# gTTS uses the same short language codes for all of the above.
GTTS_LANG_MAP = {code: code for code in LANGUAGES.values()}

PITCH_MAP = {"Very Low": -50, "Low": -25, "Normal": 0, "High": 25, "Very High": 50}
RATE_MAP = {"Slow": -25, "Normal": 0, "Fast": 25, "Very Fast": 50}

# Tone presets nudge rate/pitch slightly to emulate a "style" since the
# free engines used here don't expose SSML speaking-styles.
TONE_ADJUST = {
    "Friendly":     {"rate": 5,   "pitch": 8},
    "Professional": {"rate": -5,  "pitch": -5},
    "Assistant":    {"rate": 0,   "pitch": 0},
    "Storytelling": {"rate": -10, "pitch": 10},
}

# Age / voice-simulation presets: applied as a post-processing pitch+speed
# transform on the generated audio using pydub (frame-rate resampling).
AGE_EFFECTS = {
    "Child Voice":  1.35,
    "Young Adult":  1.12,
    "Adult":        1.00,
    "Mature":       0.85,
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def cleanup_old_files():
    """Delete temp audio files older than FILE_MAX_AGE_SECONDS."""
    now = time.time()
    for f in TEMP_DIR.glob("*.mp3"):
        try:
            if now - f.stat().st_mtime > FILE_MAX_AGE_SECONDS:
                f.unlink(missing_ok=True)
        except Exception:
            pass


def build_rate_pitch_strings(speed_label, pitch_label, tone_label):
    """Combine speed + pitch + tone selections into edge-tts rate/pitch strings."""
    rate_val = RATE_MAP[speed_label] + TONE_ADJUST[tone_label]["rate"]
    pitch_val = PITCH_MAP[pitch_label] + TONE_ADJUST[tone_label]["pitch"]
    # clamp to sane bounds
    rate_val = max(-90, min(100, rate_val))
    pitch_val = max(-100, min(100, pitch_val))
    rate_str = f"{rate_val:+d}%"
    pitch_str = f"{pitch_val:+d}Hz"
    return rate_str, pitch_str


async def _edge_tts_save(text, voice, rate_str, pitch_str, output_path):
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate_str, pitch=pitch_str)
    await communicate.save(str(output_path))


def generate_with_edge_tts(text, voice, rate_str, pitch_str, output_path):
    if not EDGE_TTS_AVAILABLE:
        raise RuntimeError("edge-tts is not installed")
    asyncio.run(_edge_tts_save(text, voice, rate_str, pitch_str, output_path))
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("edge-tts produced an empty file")
    return "edge-tts"


def generate_with_gtts(text, lang_code, output_path):
    if not GTTS_AVAILABLE:
        raise RuntimeError("gTTS is not installed")
    tts = gTTS(text=text, lang=lang_code, slow=False)
    tts.save(str(output_path))
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("gTTS produced an empty file")
    return "gTTS"


def generate_with_pyttsx3(text, output_path):
    """Offline fallback. Works best for English; quality/language support
    depends entirely on voices installed on the host OS."""
    if not PYTTSX3_AVAILABLE:
        raise RuntimeError("pyttsx3 is not installed")
    wav_path = output_path.with_suffix(".wav")
    engine = pyttsx3.init()
    engine.save_to_file(text, str(wav_path))
    engine.runAndWait()
    if not wav_path.exists() or wav_path.stat().st_size == 0:
        raise RuntimeError("pyttsx3 produced an empty file")
    # Convert wav -> mp3 if pydub/ffmpeg available, else keep wav.
    if PYDUB_AVAILABLE:
        try:
            sound = AudioSegment.from_wav(str(wav_path))
            sound.export(str(output_path), format="mp3")
            wav_path.unlink(missing_ok=True)
            return "pyttsx3"
        except Exception:
            pass
    # Could not convert - rename wav to the expected output name's stem.
    output_path.write_bytes(wav_path.read_bytes())
    wav_path.unlink(missing_ok=True)
    return "pyttsx3 (wav)"


def apply_age_effect(input_path, output_path, age_label):
    """Post-process pitch/speed to simulate different age voices."""
    factor = AGE_EFFECTS.get(age_label, 1.0)
    if factor == 1.0 or not PYDUB_AVAILABLE:
        if input_path != output_path:
            output_path.write_bytes(input_path.read_bytes())
        return False
    try:
        sound = AudioSegment.from_file(str(input_path), format="mp3")
        altered = sound._spawn(
            sound.raw_data,
            overrides={"frame_rate": int(sound.frame_rate * factor)},
        )
        altered = altered.set_frame_rate(44100)
        altered.export(str(output_path), format="mp3")
        return True
    except Exception:
        if input_path != output_path:
            output_path.write_bytes(input_path.read_bytes())
        return False


def convert_text_to_speech(text, lang_code, gender, speed_label, pitch_label,
                            tone_label, age_label, engine_choice, progress_cb=None):
    """
    Master conversion pipeline with automatic engine fallback:
    edge-tts -> gTTS -> pyttsx3
    Returns (final_path, engine_used, warnings:list)
    """
    warnings = []
    uid = uuid.uuid4().hex[:10]
    raw_path = TEMP_DIR / f"raw_{uid}.mp3"
    final_path = TEMP_DIR / f"tts_{uid}.mp3"
    engine_used = None

    rate_str, pitch_str = build_rate_pitch_strings(speed_label, pitch_label, tone_label)
    voice = EDGE_VOICES.get(lang_code, {}).get(gender)

    engines_to_try = []
    if engine_choice == "Auto (Recommended)":
        engines_to_try = ["edge-tts", "gTTS", "pyttsx3"]
    else:
        engines_to_try = [engine_choice]

    if progress_cb:
        progress_cb(10, "Preparing text...")

    for eng in engines_to_try:
        try:
            if eng == "edge-tts":
                if progress_cb:
                    progress_cb(30, "Synthesizing with edge-tts neural voice...")
                engine_used = generate_with_edge_tts(text, voice, rate_str, pitch_str, raw_path)
                break
            elif eng == "gTTS":
                if progress_cb:
                    progress_cb(30, "Synthesizing with gTTS (fallback)...")
                engine_used = generate_with_gtts(text, GTTS_LANG_MAP.get(lang_code, "en"), raw_path)
                warnings.append("Used gTTS fallback: pitch/speed/tone controls are limited with this engine.")
                break
            elif eng == "pyttsx3":
                if progress_cb:
                    progress_cb(30, "Synthesizing offline with pyttsx3 (fallback)...")
                engine_used = generate_with_pyttsx3(text, raw_path)
                warnings.append("Used pyttsx3 offline fallback: language support limited to installed system voices.")
                break
        except Exception as e:
            warnings.append(f"{eng} failed: {e}")
            continue

    if engine_used is None:
        raise RuntimeError("All available TTS engines failed. " + " | ".join(warnings))

    if progress_cb:
        progress_cb(70, "Applying voice simulation effects...")
    apply_age_effect(raw_path, final_path, age_label)
    raw_path.unlink(missing_ok=True)

    if progress_cb:
        progress_cb(100, "Done!")

    return final_path, engine_used, warnings


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Free Indian Voice Text To MP3 Converter",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Minimal responsive / mobile-friendly styling ---
st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1100px; }
    textarea { font-size: 16px !important; }
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
    }
    .char-counter { color: #888; font-size: 0.85rem; text-align: right; }
    .history-card {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
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
    st.session_state.history = []  # list of dicts

cleanup_old_files()

st.title(APP_TITLE)
st.caption(
    "100% Free • No API Key • No Subscription • Runs Locally & on Streamlit Cloud — "
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
        "Auto mode tries **edge-tts** first (best quality, full pitch/speed control), "
        "then falls back to **gTTS**, then **pyttsx3** if needed."
    )

    if not PYDUB_AVAILABLE:
        st.warning("pydub/ffmpeg not detected — voice-simulation pitch effects will be skipped.", icon="⚠️")

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
            content = uploaded_file.read().decode("utf-8", errors="ignore")
            st.session_state.text_input = content
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
            progress_bar.progress(pct, text=msg)
            status_placeholder.info(f"⏳ {msg}")

        try:
            with st.spinner("Generating audio, please wait..."):
                final_path, engine_used, warns = convert_text_to_speech(
                    clean_text, lang_code, gender, speed_label, pitch_label,
                    tone_label, age_label, engine_choice, progress_cb=progress_cb,
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

            # Save to history
            st.session_state.history.insert(0, {
                "text_snippet": clean_text[:80] + ("..." if len(clean_text) > 80 else ""),
                "file_path": str(final_path),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "language": language_label,
                "voice": gender,
                "engine": engine_used,
            })
            st.session_state.history = st.session_state.history[:15]  # keep last 15

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
    "no paid services, 100% free and open source."
)
