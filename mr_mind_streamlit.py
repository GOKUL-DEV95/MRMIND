"""
MR.MIND — Streamlit edition (Google Gemini + voice input + text-to-speech)
Run with: streamlit run mr_mind_streamlit.py
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
MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-3.1-flash-lite"

LANG_NAMES = {"ta": "Tamil", "hi": "Hindi", "te": "Telugu", "en": "English"}
SR_LOCALES = {"ta": "ta-IN", "hi": "hi-IN", "te": "te-IN", "en": "en-US"}
TTS_CODES = {"ta": "ta", "hi": "hi", "te": "te", "en": "en"}

st.set_page_config(page_title="MR.MIND", page_icon="🧠", layout="centered")

# ----------------------------------------------------------------------
# Styling (same as before)
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(135deg, #0f172a, #1e2937); color: #e2e8f0; }
    #MainMenu, header, footer {visibility: hidden;}
    .mm-title { text-align: center; color: #60a5fa; font-size: 2.8rem; font-weight: 800; margin-bottom: 0; }
    .mm-subtitle { text-align: center; color: #94a3b8; margin-bottom: 4px; }
    .mm-badge { text-align: center; color: #34d399; font-size: 0.8rem; letter-spacing: 0.05em; margin-bottom: 24px; }
    .stButton > button { background: #3b82f6 !important; color: white !important; border: none !important; border-radius: 9999px !important; padding: 0.5rem 1.4rem !important; font-weight: 600 !important; }
    .mm-card { background: #1e2937; padding: 20px; margin: 12px 0; border-radius: 16px; }
    .mm-answer { background: #1e2937; padding: 20px; border-radius: 16px; line-height: 1.7; }
    .mm-translation { margin-top: 12px; padding: 14px; background: #111827; border-left: 3px solid #8b5cf6; border-radius: 8px; font-style: italic; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Load API Key from Secrets / Environment
# ----------------------------------------------------------------------
def get_api_key():
    # First priority: Streamlit Cloud Secrets
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    # Second priority: Environment variable
    return os.environ.get("GEMINI_API_KEY", "")

API_KEY = get_api_key()

# ----------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------
def load_memories():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_memories(memories):
    DATA_FILE.write_text(json.dumps(memories, indent=2, ensure_ascii=False), encoding="utf-8")

if "memories" not in st.session_state:
    st.session_state.memories = load_memories()
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None
if "translations" not in st.session_state:
    st.session_state.translations = {}
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None
if "welcomed" not in st.session_state:
    st.session_state.welcomed = False
if "journal_input" not in st.session_state:
    st.session_state.journal_input = ""
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None

# ----------------------------------------------------------------------
# AI Helper
# ----------------------------------------------------------------------
def get_client():
    if not API_KEY:
        return None
    return genai.Client(api_key=API_KEY)

def call_gemini(system_prompt: str, user_message: str) -> str:
    client = get_client()
    if client is None:
        raise RuntimeError("NO_API_KEY")
    
    models_to_try = [MODEL, FALLBACK_MODEL]
    for model in models_to_try:
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=1000,
                ),
            )
            return response.text.strip()
        except Exception:
            continue
    raise RuntimeError("Model call failed")

# ----------------------------------------------------------------------
# Voice Helpers (same)
# ----------------------------------------------------------------------
def transcribe_audio(audio_bytes: bytes, lang_code: str) -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio_data = recognizer.record(source)
    return recognizer.recognize_google(audio_data, language=SR_LOCALES.get(lang_code, "en-US"))

def speak(text: str, lang_code: str):
    try:
        tts = gTTS(text=text, lang=TTS_CODES.get(lang_code, "en"))
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        st.audio(buf, format="audio/mp3", autoplay=True)
    except Exception:
        st.caption("(Voice unavailable)")

# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.markdown('<div class="mm-title">🧠 MR.MIND</div>', unsafe_allow_html=True)
st.markdown('<div class="mm-subtitle">Your Personal Intelligent Memory Companion</div>', unsafe_allow_html=True)
st.markdown('<div class="mm-badge">✨ Powered by real AI reasoning over your memories</div>', unsafe_allow_html=True)

lang_label_to_code = {
    "தமிழ் - Tamil": "ta", "हिन्दी - Hindi": "hi",
    "తెలుగు - Telugu": "te", "English": "en"
}
lang_label = st.selectbox("🌐 Target Language", list(lang_label_to_code.keys()))
target_lang = lang_label_to_code[lang_label]
lang_name = LANG_NAMES[target_lang]

if not st.session_state.welcomed:
    st.session_state.welcomed = True
    speak("Welcome to your Mind Palace, Sir.", target_lang)

# Only 3 tabs now (Settings removed)
tab0, tab1, tab2 = st.tabs(["📝 New Memory", "🔎 Ask AI", "🔖 All Memories"])

# Tab 0 - New Memory (same as before)
with tab0:
    st.caption("🎙️ Record a memory, or type one below.")
    audio = mic_recorder(start_prompt="🎙️ Start Recording", stop_prompt="⏹️ Stop Recording", format="wav", key="recorder")
    
    if audio is not None:
        audio_hash = hash(audio["bytes"])
        if st.session_state.last_audio_hash != audio_hash:
            st.session_state.last_audio_hash = audio_hash
            with st.spinner("Transcribing..."):
                try:
                    text = transcribe_audio(audio["bytes"], target_lang)
                    st.session_state.journal_input = text
                    st.rerun()
                except Exception as e:
                    st.error(f"Transcription failed: {e}")

    journal_text = st.text_area("What happened today, Sir?", height=200, key="journal_input")
    
    if st.button("💾 Save Memory"):
        text = journal_text.strip()
        if text:
            st.session_state.memories.insert(0, {
                "id": str(datetime.now().timestamp()),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "content": text,
            })
            save_memories(st.session_state.memories)
            st.success("Memory saved!")
            speak("Done, Sir.", target_lang)
            if "journal_input" in st.session_state:
                del st.session_state.journal_input
            st.rerun()
        else:
            st.warning("Write something first.")

# Tab 1 - Ask AI
with tab1:
    if not API_KEY:
        st.error("⚠️ Gemini API key is missing. Please add it in Streamlit Cloud Secrets.")
        st.stop()
    
    query = st.text_input("Ask anything about your memories", key="ask_query")
    
    if st.button("🔎 Ask AI"):
        if query.strip():
            with st.spinner("Reasoning over your memories..."):
                memories = st.session_state.memories
                memory_context = "\n---\n".join(f"[{m['date']}] {m['content']}" for m in memories) if memories else "(No memories yet.)"
                
                system_prompt = (
                    "You are Mr. Mind, a warm, thoughtful personal memory assistant. "
                    "Answer using ONLY the memories provided. Be concise and conversational. "
                    f"Respond in {lang_name}.\n\nMEMORIES:\n{memory_context}"
                )
                try:
                    answer = call_gemini(system_prompt, query)
                    st.session_state.last_answer = answer
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    if st.session_state.get("last_answer"):
        st.markdown(f'<div class="mm-answer"><strong>🧠 Mr. Mind:</strong><br><br>{st.session_state.last_answer}</div>', unsafe_allow_html=True)
        if st.button("🔊 Read this answer aloud"):
            speak(st.session_state.last_answer, target_lang)

# Tab 2 - All Memories (same as before, shortened for brevity)
with tab2:
    if st.button("🔄 Refresh"):
        st.session_state.memories = load_memories()
        st.rerun()
    
    if not st.session_state.memories:
        st.info("No memories yet.")
    else:
        for m in st.session_state.memories:
            mid = m["id"]
            st.markdown('<div class="mm-card">', unsafe_allow_html=True)
            st.markdown(f'<span class="mm-date">{m["date"]}</span>', unsafe_allow_html=True)
            st.write(m["content"])
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("✏️ Edit", key=f"edit_{mid}"):
                    st.session_state.editing_id = mid
                    st.rerun()
            with c2:
                if st.button("🔊 Listen", key=f"listen_{mid}"):
                    speak(m["content"], target_lang)
            with c3:
                if st.button("🗑️ Delete", key=f"del_{mid}"):
                    st.session_state.memories = [x for x in st.session_state.memories if x["id"] != mid]
                    save_memories(st.session_state.memories)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
