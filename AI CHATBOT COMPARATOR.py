import streamlit as st
import ollama
from datetime import datetime
import time

# Page Configuration
st.set_page_config(
    page_title="AI CHATBOT COMPARATOR",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {padding: 2rem;}
    .stButton>button {width: 100%; height: 3rem; font-size: 16px;}
    .response-box {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #1e1e1e;
        border: 1px solid #333;
        margin-bottom: 1rem;
    }
    .metric-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #2a2a2a;
        text-align: center;
        border: 1px solid #444;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🔍AI CHATBOT COMPARATOR")
st.markdown("**Lightweight LLM Comparison Tool**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    mode = st.radio("Mode", ["Side-by-Side Comparison", "Single Model View"], index=0)
    
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.05)
    max_tokens = st.slider("Max Tokens", 512, 2048, 1200, 64)
    
    st.divider()
    st.caption("**AI CHATBOT**")
    st.caption("• qwen2.5:3b\n• deepseek-r1:1.5b")

# Models
MODELS = {
    "Qwen": "qwen2.5:3b",
    "DeepSeek": "deepseek-r1:1.5b"
}

prompt = st.text_area(
    "Enter your prompt:", 
    height=160, 
    placeholder="Explain the difference between lists and tuples in Python with examples...",
    key="prompt_input"
)

# Generate Button
if st.button("🚀 Generate Responses", type="primary", use_container_width=True):
    if not prompt.strip():
        st.error("⚠️ Please enter a prompt!")
    else:
        responses = {}
        times = {}
        
        # Create columns
        if mode == "Side-by-Side Comparison":
            col1, col2 = st.columns(2)
        else:
            col1 = col2 = st.container()

        for model_name, model_id in MODELS.items():
            start_time = time.time()
            
            with st.spinner(f"🤖 Generating from {model_name}..."):
                try:
                    response = ollama.chat(
                        model=model_id,
                        messages=[{"role": "user", "content": prompt}],
                        options={
                            "temperature": temperature,
                            "num_predict": max_tokens,
                            "num_ctx": 2048
                        }
                    )
                    responses[model_name] = response['message']['content']
                except Exception as e:
                    responses[model_name] = f"❌ Error: {str(e)}"
            
            end_time = time.time()
            times[model_name] = round(end_time - start_time, 2)  # Time in seconds

        # Display Responses with Performance Metrics
        for model_name, col in zip(["Qwen", "DeepSeek"], [col1, col2]):
            with col:
                st.subheader(f"🟦 {model_name}")
                
                # Performance Metric Box
                st.markdown(f"""
                <div class="metric-box">
                    ⏱️ <strong>Response Time:</strong> {times.get(model_name, 0)} seconds
                </div>
                """, unsafe_allow_html=True)
                
                # Response
                st.markdown(f"<div class='response-box'>{responses.get(model_name, 'No response')}</div>", 
                           unsafe_allow_html=True)

        # Export Section
        st.divider()
        st.subheader("💾 Export Results")
        
        comparison_text = f"""# Qwen vs DeepSeek Comparison
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Prompt:
{prompt}

## Qwen Response:
{responses.get('Qwen', 'No response')}

⏱️ Time Taken: {times.get('Qwen', 0)} seconds

## DeepSeek Response:
{responses.get('DeepSeek', 'No response')}

⏱️ Time Taken: {times.get('DeepSeek', 0)} seconds
"""

        col_a, col_b = st.columns(2)
        
        with col_a:
            st.download_button(
                label="📄 Download as TXT",
                data=comparison_text,
                file_name=f"llm_comparison_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )
        
        with col_b:
            st.download_button(
                label="📝 Download as Markdown",
                data=comparison_text,
                file_name=f"llm_comparison_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown"
            )

# History (optional)
if "history" not in st.session_state:
    st.session_state.history = []

if st.button("💾 Save to History"):
    if responses:
        st.session_state.history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "prompt": prompt[:100],
            "qwen_time": times.get("Qwen"),
            "deepseek_time": times.get("DeepSeek")
        })
        st.success("Saved to history!")