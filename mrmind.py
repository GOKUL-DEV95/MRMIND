"""
MR.MIND — Streamlit edition (Google Gemini + voice input + text-to-speech)

Run with:   streamlit run mr_mind_streamlit.py

Requires:
    pip install streamlit google-genai streamlit-mic-recorder SpeechRecognition gTTS
"""

import io
import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder
import speech_recognition as sr
from gtts import gTTS

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
DATA_FILE = Path(__file__).parent / "mr_mind_memories.json"
MODEL = "gemini-2.5-flash"   # or "gemini-2.5-pro" for stronger (slower/costlier) reasoning

LANG_NAMES = {
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "en": "English",
}
# Speech-recognition locale codes (for listening) and gTTS codes (for speaking)
SR_LOCALES = {"ta": "ta-IN", "hi": "hi-IN", "te": "te-IN", "en": "en-US"}
TTS_CODES = {"ta": "ta", "hi": "hi", "te": "te", "en": "en"}

st.set_page_config(page_title="MR.MIND", page_icon="🧠", layout="centered")

# ----------------------------------------------------------------------
# Styling — replicates the original dark gradient / pill-button design
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a, #1e2937);
        color: #e2e8f0;
    }
    #MainMenu, header, footer {visibility: hidden;}

    .mm-title {
        text-align: center;
        color: #60a5fa;
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 0;
    }
    .mm-subtitle {
        text-align: center;
        color: #94a3b8;
        margin-bottom: 4px;
    }
    .mm-badge {
        text-align: center;
        color: #34d399;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
        margin-bottom: 24px;
    }

    .stButton > button {
        background: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 9999px !important;
        padding: 0.5rem 1.4rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.03);
        box-shadow: 0 15px 20px -5px rgba(59,130,246,0.6) !important;
    }

    div[data-testid="stHorizontalBlock"] .stButton > button {
        width: 100%;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #1e2937;
        border-radius: 9999px;
        padding: 10px 22px;
        color: #e2e8f0;
    }
    .stTabs [aria-selected="true"] {
        background: #3b82f6 !important;
        color: white !important;
    }

    .mm-card {
        background: #1e2937;
        padding: 20px;
        margin: 12px 0;
        border-radius: 16px;
        transition: all 0.2s ease;
    }
    .mm-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 15px 20px -5px rgba(0,0,0,0.3);
    }
    .mm-date {
        color: #60a5fa;
        font-weight: 700;
    }
    .mm-translation {
        margin-top: 12px;
        padding: 14px;
        background: #111827;
        border-left: 3px solid #8b5cf6;
        border-radius: 8px;
        font-style: italic;
    }
    .mm-answer {
        background: #1e2937;
        padding: 20px;
        border-radius: 16px;
        line-height: 1.7;
    }

    textarea, input {
        background: #1e2937 !important;
        color: white !important;
        border-radius: 12px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Persistence — a local JSON file next to the script
# ----------------------------------------------------------------------
def load_memories():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_memories(memories):
    DATA_FILE.write_text(json.dumps(memories, indent=2), encoding="utf-8")


if "memories" not in st.session_state:
    st.session_state.memories = load_memories()
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None
if "translations" not in st.session_state:
    st.session_state.translations = {}
if "api_key" not in st.session_state:
    st.session_state.api_key = os.environ.get("GEMINI_API_KEY", "")
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None
if "welcomed" not in st.session_state:
    st.session_state.welcomed = False
if "pending_audio" not in st.session_state:
    st.session_state.pending_audio = None


# ----------------------------------------------------------------------
# AI helper
# ----------------------------------------------------------------------
def get_client():
    key = st.session_state.api_key
    if not key:
        return None
    return genai.Client(api_key=key)


def call_gemini(system_prompt: str, user_message: str) -> str:
    client = get_client()
    if client is None:
        raise RuntimeError("NO_API_KEY")
    response = client.models.generate_content(
        model=MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=1000,
        ),
    )
    return response.text.strip()


# ----------------------------------------------------------------------
# Voice helpers
# ----------------------------------------------------------------------
def transcribe_audio(audio_bytes: bytes, lang_code: str) -> str:
    """Uses the free Google Web Speech API via SpeechRecognition (no API key needed)."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio_data = recognizer.record(source)
    return recognizer.recognize_google(audio_data, language=SR_LOCALES.get(lang_code, "en-US"))


def speak(text: str, lang_code: str):
    """Generates speech with gTTS and plays it back automatically."""
    try:
        tts = gTTS(text=text, lang=TTS_CODES.get(lang_code, "en"))
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        st.audio(buf, format="audio/mp3", autoplay=True)
    except Exception as e:
        st.caption(f"(voice unavailable: {e})")


# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.markdown('<div class="mm-title">🧠 MR.MIND</div>', unsafe_allow_html=True)
st.markdown('<div class="mm-subtitle">Your Personal Intelligent Memory Companion</div>', unsafe_allow_html=True)
st.markdown('<div class="mm-badge">✨ Powered by real AI reasoning over your memories</div>', unsafe_allow_html=True)

lang_label_to_code = {"தமிழ் - Tamil": "ta", "हिन्दी - Hindi": "hi", "తెలుగు - Telugu": "te", "English": "en"}
lang_label = st.selectbox("🌐 Target Language", list(lang_label_to_code.keys()))
target_lang = lang_label_to_code[lang_label]
lang_name = LANG_NAMES[target_lang]

if not st.session_state.welcomed:
    st.session_state.welcomed = True
    speak("Welcome to your Mind Palace, Sir.", target_lang)

tab0, tab1, tab2, tab3 = st.tabs(["📝 New Memory", "🔎 Ask AI", "🔖 All Memories", "⚙️ Settings"])

# ----------------------------------------------------------------------
# Tab 0 — New Memory (with voice input)
# ----------------------------------------------------------------------
with tab0:
    st.caption("🎙️ Record a memory, or type one below.")
    audio = mic_recorder(
        start_prompt="🎙️ Start Recording",
        stop_prompt="⏹️ Stop Recording",
        format="wav",
        key="recorder",
    )

    if audio is not None:
        audio_hash = hash(audio["bytes"])
        if st.session_state.last_audio_hash != audio_hash:
            st.session_state.last_audio_hash = audio_hash
            with st.spinner("Transcribing..."):
                try:
                    text = transcribe_audio(audio["bytes"], target_lang)
                    st.session_state.journal_input = text
                    st.rerun()
                except sr.UnknownValueError:
                    st.warning("Couldn't understand the audio — please try again.")
                except Exception as e:
                    st.error(f"Transcription failed: {e}")

    journal_text = st.text_area("What happened today, Sir?", height=200, key="journal_input")

    if st.button("💾 Save Memory"):
        text = journal_text.strip()
        if not text:
            st.warning("Write something first.")
        else:
            st.session_state.memories.insert(0, {
                "id": str(datetime.now().timestamp()),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "content": text,
            })
            save_memories(st.session_state.memories)
            st.success("Memory saved!")
            speak("Done, Sir.", target_lang)
            st.session_state.journal_input = ""
            st.rerun()

# ----------------------------------------------------------------------
# Tab 1 — Ask AI
# ----------------------------------------------------------------------
with tab1:
    query = st.text_input("Ask anything about your memories", key="ask_query")
    if st.button("🔎 Ask AI"):
        if not query.strip():
            st.warning("Type a question first.")
        elif not st.session_state.api_key:
            st.error("Please add your Gemini API key in the Settings tab first.")
        else:
            with st.spinner("Reasoning over your memories..."):
                memories = st.session_state.memories
                memory_context = (
                    "\n---\n".join(f"[{m['date']}] {m['content']}" for m in memories)
                    if memories else "(No memories have been recorded yet.)"
                )
                system_prompt = (
                    "You are Mr. Mind, a warm, thoughtful personal memory assistant. "
                    "You are given a list of the user's personal journal entries (memories), "
                    "each dated. Answer the user's question using ONLY information that can "
                    "reasonably be inferred from these memories. If the memories don't contain "
                    "relevant information, say so honestly rather than making things up. Be "
                    "conversational, concise, and refer to specific dates when helpful. "
                    f"Respond in {lang_name}.\n\nMEMORIES:\n{memory_context}"
                )
                try:
                    answer = call_gemini(system_prompt, query)
                    st.markdown(
                        f'<div class="mm-answer"><strong>🧠 Mr. Mind:</strong><br><br>'
                        f'{answer}</div>',
                        unsafe_allow_html=True,
                    )
                    st.session_state["last_answer"] = answer
                except RuntimeError:
                    st.error("Please add your Gemini API key in the Settings tab first.")
                except Exception as e:
                    st.error(f"Something went wrong reaching the AI: {e}")

    if st.session_state.get("last_answer"):
        if st.button("🔊 Read this answer aloud"):
            speak(st.session_state["last_answer"], target_lang)

# ----------------------------------------------------------------------
# Tab 2 — All Memories
# ----------------------------------------------------------------------
with tab2:
    if st.button("🔄 Refresh"):
        st.session_state.memories = load_memories()
        st.rerun()

    if not st.session_state.memories:
        st.info("No memories yet.")

    for m in st.session_state.memories:
        mid = m["id"]
        st.markdown('<div class="mm-card">', unsafe_allow_html=True)
        st.markdown(f'<span class="mm-date">{m["date"]}</span>', unsafe_allow_html=True)

        if st.session_state.editing_id == mid:
            new_text = st.text_area("Edit memory", value=m["content"], key=f"edit_{mid}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Save changes", key=f"save_{mid}"):
                    m["content"] = new_text.strip()
                    save_memories(st.session_state.memories)
                    st.session_state.editing_id = None
                    st.rerun()
            with c2:
                if st.button("✖️ Cancel", key=f"cancel_{mid}"):
                    st.session_state.editing_id = None
                    st.rerun()
        else:
            st.write(m["content"])
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("✏️ Edit", key=f"editbtn_{mid}"):
                    st.session_state.editing_id = mid
                    st.rerun()
            with c2:
                if st.button("🌐 Translate", key=f"translate_{mid}"):
                    if not st.session_state.api_key:
                        st.error("Add your API key in Settings first.")
                    else:
                        with st.spinner("Translating..."):
                            try:
                                system_prompt = (
                                    f"You are a precise translator. Translate the user's text "
                                    f"into {lang_name}. Respond with ONLY the translated text, "
                                    f"no explanations, no quotes."
                                )
                                translated = call_gemini(system_prompt, m["content"])
                                st.session_state.translations[mid] = translated
                            except Exception as e:
                                st.error(f"Translation failed: {e}")
            with c3:
                if st.button("🔊 Listen", key=f"listen_{mid}"):
                    speak(m["content"], target_lang)
            with c4:
                if st.button("🗑️ Delete", key=f"delete_{mid}"):
                    st.session_state.memories = [
                        x for x in st.session_state.memories if x["id"] != mid
                    ]
                    save_memories(st.session_state.memories)
                    st.session_state.translations.pop(mid, None)
                    st.rerun()

            if mid in st.session_state.translations:
                st.markdown(
                    f'<div class="mm-translation">{st.session_state.translations[mid]}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Tab 3 — Settings
# ----------------------------------------------------------------------
with tab3:
    st.write(
        "Ask AI and Translate call the Google Gemini API using your own key. "
        "The key is kept only in this session's memory (and, optionally, "
        "the `GEMINI_API_KEY` environment variable) — it is never written "
        "to the memories file."
    )
    key_input = st.text_input(
        "Gemini API key", value=st.session_state.api_key, type="password",
        placeholder="sk-ant-..."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔑 Save Key"):
            st.session_state.api_key = key_input.strip()
            st.success("Key saved for this session.")
    with c2:
        if st.button("🗑️ Remove Key"):
            st.session_state.api_key = ""
            st.success("Key removed.")
    st.caption("Get a free key at aistudio.google.com → Get API key.")
    st.divider()
    st.write(
        "Voice input uses Google's free web speech-recognition endpoint via the "
        "`SpeechRecognition` library — no extra key needed, but it does require "
        "an internet connection. Text-to-speech uses `gTTS`, also free."
    )
