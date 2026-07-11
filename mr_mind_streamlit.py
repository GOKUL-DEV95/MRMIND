"""
MR.MIND — Streamlit Edition (Final Clean Version)
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
DATA_FILE = Path("mr_mind_memories.json")
MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-3.1-flash-lite"

LANG_NAMES = {"ta": "Tamil", "hi": "Hindi", "te": "Telugu", "en": "English"}
SR_LOCALES = {"ta": "ta-IN", "hi": "hi-IN", "te": "te-IN", "en": "en-US"}
TTS_CODES = {"ta": "ta", "hi": "hi", "te": "te", "en": "en"}

st.set_page_config(page_title="MR.MIND", page_icon="🧠", layout="centered")

# ----------------------------------------------------------------------
# Hide Audio Player Bar
# ----------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(135deg, #0f172a, #1e2937); color: #e2e8f0; }
    #MainMenu, header, footer {visibility: hidden;}
    
    .mm-title { text-align: center; color: #60a5fa; font-size: 2.8rem; font-weight: 800; margin-bottom: 0; }
    .mm-subtitle { text-align: center; color: #94a3b8; margin-bottom: 4px; }
    .mm-badge { text-align: center; color: #34d399; font-size: 0.8rem; letter-spacing: 0.05em; margin-bottom: 24px; }

    /* Hide Audio Player */
    audio { display: none !important; }
    .stAudio { display: none !important; }

    /* Nice Tab & Button Style */
    .stTabs [data-baseweb="tab"] {
        background-color: #334155 !important;
        color: #e2e8f0 !important;
        border-radius: 9999px !important;
        padding: 12px 28px !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        transform: translateY(-6px) !important;
        box-shadow: 0 20px 25px -5px rgb(59 130 246 / 0.5) !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6, #60a5fa) !important;
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# Memory Functions
# ----------------------------------------------------------------------
def load_memories():
    try:
        if DATA_FILE.exists():
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except:
        pass
    return []

def save_memories(memories):
    try:
        DATA_FILE.write_text(json.dumps(memories, indent=2, ensure_ascii=False), encoding="utf-8")
    except:
        pass

# Session State
if "memories" not in st.session_state:
    st.session_state.memories = load_memories()
if "welcomed" not in st.session_state:
    st.session_state.welcomed = False
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None
if "translations" not in st.session_state:
    st.session_state.translations = {}
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    return os.environ.get("GEMINI_API_KEY", "")

API_KEY = get_api_key()

def get_client():
    if not API_KEY: return None
    return genai.Client(api_key=API_KEY)

def call_gemini(system_prompt: str, user_message: str) -> str:
    client = get_client()
    if not client: raise RuntimeError("NO_API_KEY")
    for model in [MODEL, FALLBACK_MODEL]:
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_message,
                config=types.GenerateContentConfig(system_instruction=system_prompt, max_output_tokens=1000)
            )
            return response.text.strip()
        except: continue
    raise RuntimeError("Model failed")

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
        st.audio(buf, format="audio/mp3", autoplay=True)  # Hidden by CSS
    except:
        pass

# ----------------------------------------------------------------------
# Auto Welcome
# ----------------------------------------------------------------------
if not st.session_state.welcomed:
    st.session_state.welcomed = True
    speak("Welcome to your Mind Palace, Sir.", "en")

# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
st.markdown('<div class="mm-title">🧠 MR.MIND</div>', unsafe_allow_html=True)
st.markdown('<div class="mm-subtitle">Your Personal Intelligent Memory Companion</div>', unsafe_allow_html=True)
st.markdown('<div class="mm-badge">✨ Powered by real AI reasoning over your memories</div>', unsafe_allow_html=True)

lang_label_to_code = {"தமிழ் - Tamil": "ta", "हिन्दी - Hindi": "hi", "తెలుగు - Telugu": "te", "English": "en"}
lang_label = st.selectbox("🌐 Target Language", list(lang_label_to_code.keys()))
target_lang = lang_label_to_code[lang_label]
lang_name = LANG_NAMES[target_lang]

tab0, tab1, tab2 = st.tabs(["📝 New Memory", "🔎 Ask AI", "📖 All Memories"])

# Tab 0: New Memory
with tab0:
    st.caption("🎙️ Record a memory or type below")
    audio = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹️ Stop Recording", format="wav", key="recorder")
    
    if audio is not None:
        if st.session_state.last_audio_hash != hash(audio["bytes"]):
            st.session_state.last_audio_hash = hash(audio["bytes"])
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
                "content": text
            })
            save_memories(st.session_state.memories)
            st.success("✅ Memory Saved!")
            speak("Done, Sir.", target_lang)
            if "journal_input" in st.session_state:
                del st.session_state.journal_input
            st.rerun()
        else:
            st.warning("Please write something first.")

# Tab 1: Ask AI
with tab1:
    if not API_KEY:
        st.error("⚠️ Please add GEMINI_API_KEY in Streamlit Secrets.")
        st.stop()
    
    query = st.text_input("Ask anything about your memories", key="ask_query")
    if st.button("🔎 Ask Mr. Mind"):
        if query.strip():
            with st.spinner("Reasoning..."):
                memory_context = "\n---\n".join(f"[{m['date']}] {m['content']}" for m in st.session_state.memories) if st.session_state.memories else "(No memories yet.)"
                system_prompt = f"You are Mr. Mind. Be warm and concise. Respond in {lang_name}.\n\nMEMORIES:\n{memory_context}"
                try:
                    answer = call_gemini(system_prompt, query)
                    st.session_state.last_answer = answer
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    
    if st.session_state.get("last_answer"):
        st.markdown(f'<div style="background:#1e2937;padding:20px;border-radius:16px;line-height:1.7;"><strong>🧠 Mr. Mind:</strong><br><br>{st.session_state.last_answer}</div>', unsafe_allow_html=True)
        if st.button("🔊 Read Aloud"):
            speak(st.session_state.last_answer, target_lang)

# Tab 2: All Memories
with tab2:
    if st.button("🔄 Refresh"):
        st.session_state.memories = load_memories()
        st.rerun()
    
    if not st.session_state.memories:
        st.info("No memories yet.")
    else:
        for m in st.session_state.memories:
            mid = m["id"]
            st.markdown('<div style="background:#1e2937;padding:20px;margin:12px 0;border-radius:16px;">', unsafe_allow_html=True)
            st.markdown(f'<span style="color:#60a5fa;font-weight:700;">{m["date"]}</span>', unsafe_allow_html=True)
            
            if st.session_state.editing_id == mid:
                new_text = st.text_area("Edit memory", value=m["content"], key=f"edit_{mid}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Save", key=f"save_{mid}"):
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
                        with st.spinner("Translating..."):
                            try:
                                translated = call_gemini(f"Translate to {lang_name}. Only return translation.", m["content"])
                                st.session_state.translations[mid] = translated
                                st.rerun()
                            except:
                                st.error("Translation failed")
                with c3:
                    if st.button("🔊 Listen", key=f"listen_{mid}"):
                        speak(m["content"], target_lang)
                with c4:
                    if st.button("🗑️ Delete", key=f"delete_{mid}"):
                        st.session_state.memories = [x for x in st.session_state.memories if x["id"] != mid]
                        save_memories(st.session_state.memories)
                        st.session_state.translations.pop(mid, None)
                        st.rerun()
            
            if mid in st.session_state.translations:
                st.markdown(f'<div style="margin-top:12px;padding:14px;background:#111827;border-left:3px solid #8b5cf6;border-radius:8px;font-style:italic;">{st.session_state.translations[mid]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
