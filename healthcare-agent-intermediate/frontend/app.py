import streamlit as st
import requests
import time

st.set_page_config(
    page_title="Multi-Specialist Consultation",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    .title-text {
        font-size: 2.75rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #2563EB, #7C3AED);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: -15px;
        padding-top: 1rem;
    }
    
    .subtitle-text {
        font-size: 1.15rem;
        color: #64748b;
        font-weight: 500;
        margin-bottom: 2rem;
    }
    
    .stTextArea textarea {
        border-radius: 12px !important;
        border: 1px solid #E2E8F0;
        padding: 1rem;
        font-size: 1rem;
        transition: border-color 0.2s;
        min-height: 180px !important;
    }
    
    .stTextArea textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 1px #3B82F6 !important;
    }
    
    .stButton>button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        height: 3rem;
        letter-spacing: 0.5px;
        background-color: #2563EB !important;
        color: white !important;
        border: none !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4) !important;
        background-color: #1D4ED8 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3.5rem;
        border-radius: 8px 8px 0 0;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        background-color: transparent;
        font-weight: 600 !important;
        color: #475569 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: rgba(59, 130, 246, 0.1) !important;
        border-bottom-color: #3B82F6 !important;
        color: #2563EB !important;
    }

    .stAlert {
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
    }
    
    /* Dark Theme Support */
    @media (prefers-color-scheme: dark) {
        .subtitle-text { color: #94a3b8; }
        .stTextArea textarea { 
            border-color: #334155; 
            background-color: #1E293B;
            color: #F1F5F9;
        }
        .stTabs [data-baseweb="tab"] {
            color: #94A3B8 !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: rgba(96, 165, 250, 0.1) !important;
            border-bottom-color: #60A5FA !important;
            color: #60A5FA !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.markdown('<div class="title-text">🏥 HealthAI Multi-Specialist</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-text">AI-driven multidisciplinary medical consultation. Input the patient case and get comprehensive insights from virtual specialists.</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Consultation Parameters")
    st.markdown("Configure how the AI routes and processes the case.")
    
    st.divider()
    
    top_k = st.slider(
        "Number of Specialists",
        min_value=1,
        max_value=20,
        value=3,
        help="Select how many top-matching specialists should evaluate this case."
    )
    
    st.divider()
    
    st.markdown("""
    <div style='font-size: 0.85rem; color: #64748b;'>
    <b>System Info:</b><br/>
    • Supervisor Agent Routing<br/>
    • Multi-Agent Analysis<br/>
    • Semantic Aggregator
    </div>
    """, unsafe_allow_html=True)

# Main Input Section
with st.container():
    st.markdown("##### 📝 Patient Case File")
    
    case_input = st.text_area(
        "Patient Case File",
        placeholder="Type patient symptoms, history, test results, etc. \n\nExample: Patient is a 55-year-old male presenting with chest pain, shortness of breath, and a history of Type 2 Diabetes...",
        height=180,
        label_visibility="collapsed"
    )

st.markdown("<br>", unsafe_allow_html=True)

# Submit Button Row
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    submit_clicked = st.button("🚀 INITIATE CONSULTATION", use_container_width=True)

st.divider()

if submit_clicked:
    if not case_input.strip():
        st.warning("⚠️ Please enter a case description to begin.")
    else:
        # Progress Tracking
        progress_container = st.container()
        with progress_container:
            status_text = st.empty()
            progress_bar = st.progress(0)
            
            # Simulated progress for UI feel
            status_text.markdown(f"**🤖 Supervisor Agent routing case to {top_k} best specialists...**")
            progress_bar.progress(15)
            
            try:
                time.sleep(0.5)
                progress_bar.progress(30)
                status_text.markdown("**🧬 Specialists are currently analyzing the case in parallel...**")
                
                response = requests.post(
                    "http://api:8000/analyze",
                    json={"case": case_input, "top_k": top_k},
                    timeout=300
                )
                
                progress_bar.progress(80)
                status_text.markdown("**📋 Aggregator Agent is synthesizing final multidisciplinary report...**")
                time.sleep(0.5)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    progress_bar.progress(100)
                    time.sleep(0.2)
                    
                    # Clear progress
                    status_text.empty()
                    progress_bar.empty()
                    
                    st.success(f"Multidisciplinary consultation completed with {data['selected_count']} specialists.", icon="✅")
                    
                    # Show selection reasoning nicely
                    if data.get("reasoning"):
                        st.info(f"**🧠 Selection Logic:** {data['reasoning']}")
                    
                    # Show selected specialists as chips or nice text
                    if data.get("selected_specialists"):
                        specialists_str = ", ".join([
                            s.replace("_", " ").title() 
                            for s in data['selected_specialists']
                        ])
                        st.caption(f"🎯 **Consulted Specialists:** {specialists_str}")
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Results Section - Summary
                    st.markdown("### 📋 Executive Summary")
                    st.info(data["final_summary"])
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Results Section - Specialists
                    st.markdown("### 🩺 Detailed Specialist Reports")
                    
                    if data["assessments"]:
                        tabs = st.tabs([f"👨‍⚕️ {a['specialist']}" for a in data["assessments"]])
                        for tab, assessment in zip(tabs, data["assessments"]):
                            with tab:
                                st.markdown("<br>", unsafe_allow_html=True)
                                st.markdown(assessment["assessment"])
                                
                else:
                    status_text.empty()
                    progress_bar.empty()
                    st.error(f"⚠️ API Error: {response.status_code}")
                    st.code(response.text)
                    
            except requests.exceptions.ConnectionError:
                status_text.empty()
                progress_bar.empty()
                st.error("❌ Cannot connect to the API container. Is it running?")
            except Exception as e:
                status_text.empty()
                progress_bar.empty()
                st.error(f"❌ An error occurred: {str(e)}")
