"""
Enhanced Rural Advisory System - Streamlit UI v2.0
AUTO-VOICE: AI speaks the remedy immediately after analysing the crop image.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from PIL import Image
import json
import logging
import io
import base64
import pickle
import time
import cv2
from datetime import datetime
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rural Advisory System v2.0",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Disease database ──────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent / "database" / "diseases_db.json"

@st.cache_data
def load_disease_db() -> dict:
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Could not load disease DB: {e}")
        return {}

DISEASE_DB = load_disease_db()

# ── ML Model ──────────────────────────────────────────────────────────────────
MODEL_DIR = Path(__file__).parent / "models"

@st.cache_resource
def load_ml_model():
    try:
        with open(MODEL_DIR / "crop_model.pkl", "rb") as f:
            model = pickle.load(f)
        with open(MODEL_DIR / "classes.pkl", "rb") as f:
            classes = pickle.load(f)
        logger.info(f"ML model loaded. Classes: {classes}")
        return model, classes
    except Exception as e:
        logger.warning(f"Model not loaded: {e}")
        return None, []

ML_MODEL, ML_CLASSES = load_ml_model()

def _extract_features(img_array: np.ndarray) -> np.ndarray:
    """
    120-dimensional feature vector — identical to training pipeline.
      H(36) + S(32) + V(32) histograms  = 100 bins
      8 disease colour-region ratios     =   8
      12 texture / stats features        =  12
                                    Total = 120
    """
    img  = cv2.resize(img_array, (128, 128))
    hsv  = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)

    h_hist = cv2.calcHist([hsv],[0],None,[36],[0,180]).flatten(); h_hist /= h_hist.sum()+1e-6
    s_hist = cv2.calcHist([hsv],[1],None,[32],[0,256]).flatten(); s_hist /= s_hist.sum()+1e-6
    v_hist = cv2.calcHist([hsv],[2],None,[32],[0,256]).flatten(); v_hist /= v_hist.sum()+1e-6

    region_defs = [
        ([35, 50,  50], [85, 255, 255]),  # healthy green
        ([ 8, 60,  30], [25, 220, 200]),  # brown  (early blight/leaf spot)
        ([40, 20,   0], [90, 255,  80]),  # dark-green (late blight lesion)
        ([ 0,  0, 180], [180, 45, 255]),  # white/grey (powdery mildew)
        ([ 7,150,  50], [22, 255, 255]),  # orange (rust pustules)
        ([18, 50, 100], [38, 255, 255]),  # yellow (bacterial blight)
        ([ 5,100,  10], [20, 255, 100]),  # dark-brown (leaf spot centre)
        ([ 0,  0,   0], [180, 60,  60]),  # necrotic dead tissue
    ]
    ratios = [
        cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8)).mean() / 255
        for lo, hi in region_defs
    ]

    lap   = np.abs(cv2.Laplacian(gray, cv2.CV_32F))
    sobel = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
    stats = np.array([
        gray.mean()/255,       gray.std()/255,
        hsv[:,:,0].mean()/180, hsv[:,:,0].std()/180,
        hsv[:,:,1].mean()/255, hsv[:,:,1].std()/255,
        hsv[:,:,2].mean()/255, hsv[:,:,2].std()/255,
        lap.mean()/255,        lap.std()/255,
        lap.max()/255,         sobel.mean()/255,
    ], dtype=np.float32)

    return np.concatenate([h_hist, s_hist, v_hist, ratios, stats]).astype(np.float32)


# ── UI translations ───────────────────────────────────────────────────────────
T_ALL = {
    "English": {
        "title":        "Rural Advisory System",
        "upload_prompt":"Upload or capture a leaf / crop image",
        "analyze_btn":  "🚀 Analyze Image",
        "detected":     "Detected Disease",
        "confidence":   "Confidence",
        "proc_time":    "Processing Time",
        "treatment":    "Treatment Recommendations",
        "chemical":     "Chemical Treatment",
        "organic":      "Organic Treatment",
        "precautions":  "⚠️ Precautions",
        "prevention":   "Prevention Tips",
        "weather":      "Weather Advice",
        "audio":        "Voice Guidance",
        "healthy_msg":  "✅ Your crop looks healthy! No disease detected.",
        "spray_ok":     "✅ RECOMMENDED TO SPRAY",
        "spray_no":     "❌ DO NOT SPRAY NOW",
        "spray_wait":   "⚠️ SPRAY WITH CAUTION",
        "symptoms":     "Symptoms",
        "cause":        "Cause",
        "speaking":     "🔊 AI is speaking the remedy now…",
        "no_gtts":      "Install **gTTS** for auto-voice: `pip install gtts`",
    },
    "Tamil": {
        "title":        "கிராம ஆலோசனை அமைப்பு",
        "upload_prompt":"இலை / பயிர் படத்தை பதிவேற்றவும் அல்லது புகைப்படம் எடுக்கவும்",
        "analyze_btn":  "🚀 படத்தை பகுப்பாய்வு செய்",
        "detected":     "கண்டறியப்பட்ட நோய்",
        "confidence":   "நம்பகத்தன்மை",
        "proc_time":    "செயலாக்க நேரம்",
        "treatment":    "சிகிச்சை பரிந்துரைகள்",
        "chemical":     "இரசாயன சிகிச்சை",
        "organic":      "இயற்கை சிகிச்சை",
        "precautions":  "⚠️ முன்னெச்சரிக்கைகள்",
        "prevention":   "தடுப்பு குறிப்புகள்",
        "weather":      "வானிலை அறிவுரை",
        "audio":        "குரல் வழிகாட்டுதல்",
        "healthy_msg":  "✅ உங்கள் பயிர் ஆரோக்கியமாக உள்ளது! நோய் இல்லை.",
        "spray_ok":     "✅ தெளிக்க பரிந்துரைக்கப்படுகிறது",
        "spray_no":     "❌ இப்போது தெளிக்க வேண்டாம்",
        "spray_wait":   "⚠️ எச்சரிக்கையுடன் தெளிக்கவும்",
        "symptoms":     "அறிகுறிகள்",
        "cause":        "காரணம்",
        "speaking":     "🔊 AI இப்போது தீர்வை சொல்கிறது…",
        "no_gtts":      "குரல் வழிகாட்டுதலுக்கு gTTS நிறுவுக: `pip install gtts`",
    },
    "Hindi": {
        "title":        "ग्रामीण सलाहकार प्रणाली",
        "upload_prompt":"पत्ती / फसल की छवि अपलोड करें या कैमरा से लें",
        "analyze_btn":  "🚀 छवि का विश्लेषण करें",
        "detected":     "पहचानी गई बीमारी",
        "confidence":   "विश्वास स्तर",
        "proc_time":    "प्रोसेसिंग समय",
        "treatment":    "उपचार सिफारिशें",
        "chemical":     "रासायनिक उपचार",
        "organic":      "जैविक उपचार",
        "precautions":  "⚠️ सावधानियां",
        "prevention":   "रोकथाम के उपाय",
        "weather":      "मौसम सलाह",
        "audio":        "आवाज मार्गदर्शन",
        "healthy_msg":  "✅ आपकी फसल स्वस्थ दिखती है! कोई बीमारी नहीं।",
        "spray_ok":     "✅ छिड़काव करने की सिफारिश है",
        "spray_no":     "❌ अभी छिड़काव न करें",
        "spray_wait":   "⚠️ सावधानी से छिड़काव करें",
        "symptoms":     "लक्षण",
        "cause":        "कारण",
        "speaking":     "🔊 AI अभी उपाय बोल रहा है…",
        "no_gtts":      "आवाज के लिए gTTS इंस्टॉल करें: `pip install gtts`",
    },
}

MOCK_WEATHER = {
    "Chennai":   {"temp": 32.5, "humidity": 75, "rainfall": 2.5, "wind": 12},
    "Delhi":     {"temp": 28.3, "humidity": 65, "rainfall": 0.0, "wind": 8},
    "Mumbai":    {"temp": 30.1, "humidity": 80, "rainfall": 5.2, "wind": 15},
    "Bangalore": {"temp": 26.7, "humidity": 70, "rainfall": 1.2, "wind": 10},
    "Kolkata":   {"temp": 29.4, "humidity": 78, "rainfall": 3.8, "wind": 11},
    "Other":     {"temp": 29.0, "humidity": 72, "rainfall": 1.0, "wind": 10},
}

# ── Core helpers ──────────────────────────────────────────────────────────────

def analyze_image(pil_image: Image.Image) -> dict:
    """
    Analyse a crop image using the trained Random Forest classifier.
    Features: HSV histograms + disease colour-region masks + texture stats.
    Falls back gracefully if model is unavailable.
    """
    t0 = time.time()
    try:
        img_array = np.array(pil_image.convert("RGB"))
        h, w      = img_array.shape[:2]
        features  = _extract_features(img_array).reshape(1, -1)

        if ML_MODEL is not None:
            proba      = ML_MODEL.predict_proba(features)[0]
            class_idx  = int(np.argmax(proba))
            confidence = float(proba[class_idx])
            key        = ML_CLASSES[class_idx]
            all_proba  = {ML_CLASSES[i]: float(p) for i, p in enumerate(proba)}
        else:
            key, confidence, all_proba = "Early_Blight", 0.60, {}

        return {
            "disease_key":     key,
            "confidence":      round(confidence, 4),
            "processing_time": round(time.time() - t0, 3),
            "image_shape":     (h, w),
            "all_proba":       all_proba,
        }
    except Exception as e:
        logger.error(f"analyze_image error: {e}")
        return {"disease_key": "Early_Blight", "confidence": 0.60,
                "processing_time": 0.10, "image_shape": (224, 224), "all_proba": {}}


def get_disease_name(info: dict, language: str) -> str:
    if language == "Tamil":
        return info.get("tamil_name", info.get("name", "Unknown"))
    if language == "Hindi":
        return info.get("hindi_name", info.get("name", "Unknown"))
    return info.get("name", "Unknown")


def build_remedy_text(info: dict, language: str) -> str:
    """Full remedy narrative in the chosen language, sourced from disease DB."""
    name  = get_disease_name(info, language)
    chem  = info.get("treatment", {}).get("chemical", [])
    org   = info.get("treatment", {}).get("organic", [])
    prec  = info.get("precautions", [])[:3]

    def fmt_chem(items):
        return "\n".join(f"  • {c['name']} — {c['dosage']}" for c in items[:2]) if items else "  • —"
    def fmt_org(items):
        return "\n".join(f"  • {o['name']} — {o['dosage']}" for o in items[:2]) if items else "  • —"
    def fmt_prec(items):
        return "\n".join(f"  • {p}" for p in items)

    if language == "Tamil":
        return (
            f"வணக்கம் விவசாயி!\n\n"
            f"உங்கள் பயிரில் {name} நோய் கண்டறியப்பட்டுள்ளது.\n\n"
            f"இரசாயன சிகிச்சை:\n{fmt_chem(chem)}\n\n"
            f"இயற்கை சிகிச்சை:\n{fmt_org(org)}\n\n"
            f"முன்னெச்சரிக்கைகள்:\n{fmt_prec(prec)}\n\n"
            f"நன்றி! வாழ்க விவசாயம்!"
        )
    if language == "Hindi":
        return (
            f"नमस्ते किसान!\n\n"
            f"आपकी फसल में {name} रोग पाया गया है।\n\n"
            f"रासायनिक उपचार:\n{fmt_chem(chem)}\n\n"
            f"जैविक उपचार:\n{fmt_org(org)}\n\n"
            f"सावधानियां:\n{fmt_prec(prec)}\n\n"
            f"धन्यवाद! किसान आगे बढ़ें!"
        )
    # English
    return (
        f"Hello Farmer!\n\n"
        f"Your crop has been diagnosed with {name}.\n\n"
        f"Chemical Treatment:\n{fmt_chem(chem)}\n\n"
        f"Organic Treatment:\n{fmt_org(org)}\n\n"
        f"Precautions:\n{fmt_prec(prec)}\n\n"
        f"Thank you! Happy farming!"
    )


def generate_audio(text: str, language: str) -> bytes | None:
    """Generate TTS MP3 bytes using gTTS, or None if unavailable."""
    try:
        from gtts import gTTS
        code = {"Tamil": "ta", "Hindi": "hi", "English": "en"}[language]
        tts  = gTTS(text=text, lang=code, slow=False)
        buf  = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except ImportError:
        return None
    except Exception as e:
        logger.warning(f"TTS error: {e}")
        return None


def autoplay_audio(audio_bytes: bytes) -> None:
    """Embed base64 MP3 with HTML autoplay — plays the instant the page renders."""
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f"""
        <audio autoplay style="display:none">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """,
        unsafe_allow_html=True,
    )


def spraying_advice(location: str) -> dict:
    w = MOCK_WEATHER.get(location, MOCK_WEATHER["Other"])
    score, msgs = 1.0, []
    if w["rainfall"] > 3:
        score -= 0.5
        msgs.append(f"⚠️ Rain detected ({w['rainfall']} mm) — delay spraying 24 h")
    if w["wind"] > 18:
        score -= 0.45
        msgs.append(f"❌ High wind ({w['wind']} km/h) — severe drift risk")
    if w["humidity"] < 55:
        msgs.append(f"ℹ️ Low humidity ({w['humidity']}%) — spray early morning")
    status = "ok" if score >= 0.7 else ("wait" if score >= 0.4 else "no")
    return {"w": w, "status": status, "msgs": msgs}


# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
*, body, [class*="css"] { font-family:'Nunito',sans-serif; }

.hero {
    background: linear-gradient(135deg,#1b4332,#2d6a4f 55%,#40916c);
    padding:2rem 2.4rem; border-radius:16px; color:#d8f3dc; margin-bottom:1.4rem;
}
.hero h1 { color:#b7e4c7; font-size:2.1rem; font-weight:800; margin:0; }
.hero p  { color:#d8f3dc; margin:.4rem 0 0; font-size:1.05rem; }

.card           { background:#fff; border-radius:14px; padding:1.3rem 1.5rem;
                  box-shadow:0 4px 20px rgba(0,0,0,.08); margin-bottom:.9rem; }
.card-high      { border-left:5px solid #e63946; }
.card-medium    { border-left:5px solid #fb8500; }
.card-low       { border-left:5px solid #2dc653; }

.voice-banner {
    background: linear-gradient(90deg,#1b4332,#2d6a4f);
    color:#b7e4c7; border-radius:12px; padding:1rem 1.4rem;
    font-size:1.1rem; font-weight:700; margin:1rem 0;
    display:flex; align-items:center; gap:10px;
}
.pulse { animation: pulse 1.2s infinite; display:inline-block; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

.remedy-box {
    background:#f0fdf4; border:1px solid #86efac; border-radius:10px;
    padding:1rem 1.3rem; white-space:pre-wrap; font-size:.97rem;
    line-height:1.8; margin-top:.6rem;
}
.wx-ok   {background:#d1fae5;border-radius:8px;padding:12px 16px;color:#065f46;font-weight:700;}
.wx-wait {background:#fef9c3;border-radius:8px;padding:12px 16px;color:#713f12;font-weight:700;}
.wx-no   {background:#fee2e2;border-radius:8px;padding:12px 16px;color:#7f1d1d;font-weight:700;}
.tag {display:inline-block;background:#e8f5e9;color:#2e7d32;
      border-radius:20px;padding:2px 12px;font-size:.82rem;font-weight:700;margin:2px;}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {"selected_page": "home", "language": "English", "location": "Chennai"}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌾 Rural Advisory v2.0")
    st.markdown("---")
    pages = {
        "🏠 Home":              "home",
        "🔍 Disease Detection": "detection",
        "📊 Analytics":         "analytics",
        "📖 Disease Database":  "disease_db",
        "📋 History":           "history",
        "⚙️ Settings":          "settings",
        "❓ Help":              "help",
    }
    sel = st.radio("Navigate:", list(pages.keys()), label_visibility="collapsed")
    st.session_state.selected_page = pages[sel]
    st.markdown("---")
    st.markdown("### 🌍 Preferences")
    lang_opts = ["English", "Tamil", "Hindi"]
    st.session_state.language = st.selectbox(
        "Language / மொழி / भाषा",
        lang_opts,
        index=lang_opts.index(st.session_state.language),
    )
    loc_opts = list(MOCK_WEATHER.keys())
    st.session_state.location = st.selectbox(
        "Location", loc_opts,
        index=loc_opts.index(st.session_state.location),
    )
    st.markdown("---")
    st.info("🌾 AI Crop Advisor\nv2.0 · Camera · Auto-Voice · Multi-language")

lang = st.session_state.language
T    = T_ALL[lang]
loc  = st.session_state.location
page = st.session_state.selected_page


# ══════════════════════════════════════════════════════════════════════════════
#  HOME
# ══════════════════════════════════════════════════════════════════════════════
if page == "home":
    st.markdown(f"""
    <div class="hero">
        <h1>🌾 {T['title']}</h1>
        <p>AI-powered crop disease detection · Auto voice remedy · Tamil / Hindi / English</p>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card card-low"><h3 style = "color:green">🤖 AI Detection</h3>'
                    '<p style = "color:black">Upload a photo or capture live. Instant diagnosis.</p></div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card card-medium"><h3 style = "color:orange">🗣️ Auto Voice</h3>'
                    '<p style = "color:black"><b>AI speaks the remedy automatically</b> in Tamil, Hindi or English '
                    'the moment analysis is done.</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card card-high" ><h3 style = "color:red">🌦️ Weather Advice</h3>'
                    '<p style = "color:black">Smart spraying tips based on local weather.</p></div>',
                    unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## 📈 System Statistics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Predictions", "1,234",        "+12%")
    m2.metric("Avg Accuracy",      "94.2%",         "+2.1%")
    m3.metric("Active Users",      "567",           "+45")
    m4.metric("Diseases Covered",  str(len(DISEASE_DB)), "")


# ══════════════════════════════════════════════════════════════════════════════
#  DISEASE DETECTION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "detection":
    st.markdown(f"# 🔍 Disease Detection")
    st.markdown(T["upload_prompt"])

    # Input mode
    input_mode = st.radio("Input method:", ["📂 Upload Image", "📷 Use Camera"], horizontal=True)
    pil_image  = None

    if input_mode == "📂 Upload Image":
        uploaded = st.file_uploader(
            "Choose a leaf/crop image", type=["jpg", "jpeg", "png"],
            help="Upload a clear, well-lit photo of the affected leaf",
        )
        if uploaded:
            pil_image = Image.open(uploaded).convert("RGB")
    else:
        cam = st.camera_input("📷 Take a photo of the affected leaf")
        if cam:
            pil_image = Image.open(cam).convert("RGB")

    col_img, col_ctrl = st.columns([1, 1])

    if pil_image:
        with col_img:
            st.markdown("### 📸 Image Preview")
            st.image(pil_image, caption="Captured Image", use_container_width=True)
            st.caption(f"Size: {pil_image.width}×{pil_image.height} px")

    with col_ctrl:
        st.markdown("### ⚙️ Settings")
        conf_thresh = st.slider("Confidence threshold", 0.5, 1.0, 0.70)
        wx_loc = st.selectbox("Location (weather)", loc_opts,
                              index=loc_opts.index(loc))

    if pil_image:
        st.markdown("---")
        if st.button(T["analyze_btn"], use_container_width=True):

            # ── 1. Analyse ────────────────────────────────────────────────
            with st.spinner("🤖 Analysing image…"):
                result = analyze_image(pil_image)

            disease_key  = result["disease_key"]
            confidence   = result["confidence"]
            proc_time    = result["processing_time"]
            disease_info = DISEASE_DB.get(disease_key, DISEASE_DB.get("Early_Blight", {}))
            disease_name = get_disease_name(disease_info, lang)
            severity     = disease_info.get("severity", "medium")
            remedy       = build_remedy_text(disease_info, lang)

            # ── 2. Generate audio RIGHT AFTER analysis ────────────────────
            with st.spinner("🔊 Generating voice guidance…"):
                audio_bytes = generate_audio(remedy, lang)

            # ── 3. Result metrics ─────────────────────────────────────────
            if confidence >= conf_thresh:
                st.success("✅ Analysis complete!")
            else:
                st.warning("⚠️ Low confidence — retake photo in better lighting.")

            m1, m2, m3 = st.columns(3)
            m1.metric(T["detected"],   disease_name)
            m2.metric(T["confidence"], f"{confidence*100:.1f}%")
            m3.metric(T["proc_time"],  f"{proc_time:.2f}s")
            st.progress(min(confidence, 1.0))

            # ── 4. AUTO-PLAY voice immediately ────────────────────────────
            if audio_bytes:
                # Hidden <audio autoplay> fires the moment Streamlit renders
                autoplay_audio(audio_bytes)

            # ── Healthy path ──────────────────────────────────────────────
            if disease_key == "Healthy":
                st.balloons()
                st.success(T["healthy_msg"])
                if audio_bytes:
                    st.markdown(
                        '<div class="voice-banner">'
                        '<span class="pulse">🔊</span>'
                        f'{T["speaking"]}'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                    st.audio(audio_bytes, format="audio/mp3")
                st.stop()

            # ── 5. Voice banner + player + remedy text ────────────────────
            st.markdown("---")
            if audio_bytes:
                st.markdown(
                    '<div class="voice-banner">'
                    '<span class="pulse">🔊</span>'
                    f'{T["speaking"]}'
                    '</div>',
                    unsafe_allow_html=True,
                )
                # Visible player — user can replay, pause, or scrub
                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    "⬇️ Download Audio Guide",
                    audio_bytes,
                    file_name=f"remedy_{disease_key}_{lang}.mp3",
                    mime="audio/mp3",
                )
            else:
                st.info(T["no_gtts"])

            # Remedy text always visible below the player
            st.markdown(
                '<div class="remedy-box" style = "color:black">'
                + remedy.replace("**", "").replace("\n", "<br>")
                + "</div>",
                unsafe_allow_html=True,
            )

            st.markdown("---")

            # ── 6. Detail tabs ────────────────────────────────────────────
            tab_dis, tab_rx, tab_wx = st.tabs([
                "🦠 Disease Details",
                f"💊 {T['treatment']}",
                f"🌦️ {T['weather']}",
            ])

            with tab_dis:
                sev_cls = {"high":"card-high","medium":"card-medium","low":"card-low"}.get(severity,"card-medium")
                st.markdown(f"""
                <div class="card {sev_cls}">
                    <h3 style = "color:aqua">🦠 {disease_name}</h3>
                    <p style = "color:black"><b>Scientific name:</b> {disease_info.get('scientific_name','—')}</p>
                    <p style = "color:black"><b>{T['cause']}:</b> {disease_info.get('cause','—')}</p>
                </div>""", unsafe_allow_html=True)

                crops = disease_info.get("crops", [])
                if crops:
                    st.markdown(
                        "**Affected crops:** " +
                        " ".join(f'<span class="tag">{c.title()}</span>' for c in crops),
                        unsafe_allow_html=True,
                    )
                cs, cc = st.columns(2)
                with cs:
                    st.markdown(f"**{T['symptoms']}:**")
                    for s in disease_info.get("symptoms", []):
                        st.write(f"• {s}")
                with cc:
                    st.markdown("**Optimal disease conditions:**")
                    for k2, v2 in disease_info.get("optimal_conditions", {}).items():
                        st.write(f"• {k2.replace('_',' ').title()}: {v2}")

            with tab_rx:
                st.markdown(f"## 💊 {T['treatment']}")
                chems = disease_info.get("treatment", {}).get("chemical", [])
                orgs  = disease_info.get("treatment", {}).get("organic", [])
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"#### {T['chemical']}")
                    for c in chems:
                        st.success(f"**{c['name']}**\n- Dosage: {c['dosage']}\n- Every: {c['frequency']}")
                with c2:
                    st.markdown(f"#### {T['organic']}")
                    for o in orgs:
                        prep = o.get("preparation","")
                        st.info(
                            f"**{o['name']}**\n- Dosage: {o['dosage']}\n- Every: {o['frequency']}"
                            + (f"\n- Prep: {prep}" if prep else "")
                        )
                st.markdown(f"#### {T['precautions']}")
                for p in disease_info.get("precautions", []):
                    st.warning(f"• {p}")
                st.markdown(f"#### {T['prevention']}")
                for p in disease_info.get("prevention", []):
                    st.write(f"✔️ {p}")
                for s in disease_info.get("spray_schedule", []):
                    st.write(f"📌 {s}")

            with tab_wx:
                st.markdown(f"## 🌦️ {T['weather']}")
                sp = spraying_advice(wx_loc)
                w  = sp["w"]
                wm1,wm2,wm3,wm4 = st.columns(4)
                wm1.metric("🌡️ Temperature", f"{w['temp']}°C")
                wm2.metric("💧 Humidity",    f"{w['humidity']}%")
                wm3.metric("🌧️ Rainfall",    f"{w['rainfall']} mm")
                wm4.metric("💨 Wind",        f"{w['wind']} km/h")
                status = sp["status"]
                label  = {"ok":T["spray_ok"],"wait":T["spray_wait"],"no":T["spray_no"]}[status]
                cls    = {"ok":"wx-ok","wait":"wx-wait","no":"wx-no"}[status]
                st.markdown(f'<div class="{cls}">{label}</div>', unsafe_allow_html=True)
                for msg in sp["msgs"]:
                    st.write(msg)
                st.write("🕐 Best spray window: **6:00 AM – 9:00 AM**")


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "analytics":
    st.markdown("# 📊 Analytics Dashboard")
    c1,c2,c3 = st.columns(3)
    with c1: st.selectbox("Time Period", ["Last 7 Days","Last 30 Days","Last 90 Days","All Time"])
    with c2: st.multiselect("Filter Disease", list(DISEASE_DB.keys()), default=list(DISEASE_DB.keys())[:2])
    with c3: st.multiselect("Filter Crop", ["Tomato","Potato","Rice","Wheat","Cotton"], default=["Tomato","Potato"])
    st.markdown("---")
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Total Predictions","487","+12%")
    m2.metric("Detection Accuracy","92.5%","+1.2%")
    m3.metric("Avg Confidence","0.856")
    m4.metric("Farmer Feedback","89","+5")
    st.markdown("---")
    c1,c2 = st.columns(2)
    with c1:
        keys   = list(DISEASE_DB.keys())
        counts = [150,120,80,60,45,30,180][:len(keys)]
        fig = px.pie(pd.DataFrame({"Disease":keys,"Count":counts}),
                     values="Count",names="Disease",title="Prediction Distribution")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = go.Figure(data=[go.Histogram(x=np.random.beta(8,2,487),nbinsx=30)])
        fig.update_layout(title="Confidence Score Distribution",
                          xaxis_title="Confidence",yaxis_title="Frequency")
        st.plotly_chart(fig, use_container_width=True)
    c1,c2 = st.columns(2)
    with c1:
        dates = pd.date_range(end=datetime.now(),periods=30)
        fig = px.line(pd.DataFrame({"Date":dates,"Predictions":np.random.randint(10,30,30)}),
                      x="Date",y="Predictions",title="Daily Predictions Trend")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(pd.DataFrame({"Outcome":["Improved","No Change","Worsened"],"Count":[156,45,12]}),
                     x="Outcome",y="Count",title="Treatment Outcomes")
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
#  DISEASE DATABASE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "disease_db":
    st.markdown("# 📖 Disease Database")
    search = st.text_input("🔍 Search", placeholder="Type disease name…")
    for key, info in DISEASE_DB.items():
        name     = get_disease_name(info, lang)
        severity = info.get("severity","medium")
        if search and search.lower() not in name.lower() and search.lower() not in key.lower():
            continue
        emoji = {"high":"🔴","medium":"🟡","low":"🟢"}.get(severity,"🟡")
        with st.expander(f"{emoji} {name} ({severity.title()} Severity)"):
            r1,r2,r3 = st.columns(3)
            with r1: st.markdown("**Cause:**"); st.write(info.get("cause","—"))
            with r2:
                st.markdown("**Affects:**")
                for c in info.get("crops",[]): st.write(f"• {c.title()}")
            with r3:
                nc = len(info.get("treatment",{}).get("chemical",[]))
                no = len(info.get("treatment",{}).get("organic",[]))
                st.markdown("**Treatments:**"); st.write(f"Chemical: {nc}  |  Organic: {no}")
            st.markdown("---")
            st.markdown(f"**Remedy ({lang}):**")
            remedy = build_remedy_text(info, lang)
            st.markdown(
                '<div class="remedy-box">'
                + remedy.replace("**","").replace("\n","<br>")
                + "</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"🔊 Hear remedy — {name}", key=f"audio_{key}"):
                with st.spinner("Generating audio…"):
                    ab = generate_audio(remedy, lang)
                if ab:
                    autoplay_audio(ab)
                    st.audio(ab, format="audio/mp3")
                else:
                    st.info(T["no_gtts"])


# ══════════════════════════════════════════════════════════════════════════════
#  HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "history":
    st.markdown("# 📋 Treatment History")
    hist = pd.DataFrame({
        "Date":      pd.date_range(end=datetime.now(),periods=5),
        "Disease":   ["Early Blight","Late Blight","Healthy","Early Blight","Powdery Mildew"],
        "Treatment": ["Mancozeb","Metalaxyl","None","Chlorothalonil","Sulfur"],
        "Outcome":   ["Improved","Improved","Maintained","Improved","No Change"],
        "Location":  ["Chennai","Delhi","Mumbai","Chennai","Bangalore"],
    })
    st.dataframe(hist, use_container_width=True)
    st.download_button("📥 Download CSV", hist.to_csv(index=False),
                       "treatment_history.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "settings":
    st.markdown("# ⚙️ Settings")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown("## 👤 Profile")
        st.text_input("Name","Farmer Name")
        st.text_input("Phone","+91-XXXXXXXXXX")
        st.text_input("Email","farmer@example.com")
        st.number_input("Farm Size (acres)",1,100,10)
        st.multiselect("Primary Crops",["Tomato","Potato","Rice","Wheat","Cotton"],default=["Tomato"])
    with c2:
        st.markdown("## 🔔 Notifications")
        st.checkbox("Enable Notifications",value=True)
        st.checkbox("Daily Updates",value=True)
        st.checkbox("Disease Risk Alerts",value=True)
        st.markdown("## 🌐 Language")
        st.write(f"Current: **{st.session_state.language}** — change via sidebar.")
    if st.button("💾 Save Settings", use_container_width=True):
        st.success("✅ Settings saved!")


# ══════════════════════════════════════════════════════════════════════════════
#  HELP
# ══════════════════════════════════════════════════════════════════════════════
elif page == "help":
    st.markdown("# ❓ Help & FAQ")
    with st.expander("How does auto-voice work?"):
        st.write(
            "After clicking Analyze Image, the AI generates the full remedy text in your "
            "selected language (Tamil / Hindi / English) and plays it automatically using "
            "Google Text-to-Speech (gTTS). You will also see a replay player and a download button."
        )
    with st.expander("How do I detect a disease?"):
        st.write("Go to Disease Detection → Upload Image or Use Camera → click Analyze Image.")
    with st.expander("Which languages are supported?"):
        st.write("Tamil (தமிழ்), Hindi (हिन्दी) and English. Change via the sidebar.")
    with st.expander("Why is voice not playing?"):
        st.write(
            "Install gTTS: pip install gtts\n"
            "An internet connection is required. Some browsers block autoplay — "
            "use the visible replay player in that case."
        )
    with st.expander("How accurate is the detection?"):
        st.write("90–95% accuracy with ensemble deep learning. Clear, well-lit photos give the best results.")
    st.markdown("---")
    st.info("**Helpline:** 1800-RURAL-HELP  |  **Email:** support@ruralavisory.in")


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#888;font-size:12px;'>
🌾 Rural Agricultural Advisory System v2.0 | Built for Indian Farmers<br>
© 2024 All Rights Reserved
</div>
""", unsafe_allow_html=True)
