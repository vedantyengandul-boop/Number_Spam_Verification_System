import os

import re

import json

import sqlite3

from datetime import datetime

import joblib

import pandas as pd

import requests

import streamlit as st

from dotenv import load_dotenv

st.set_page_config(

    page_title="Number Spam Verification System",

    page_icon="📞",

    layout="wide",

    initial_sidebar_state="collapsed",

)

load_dotenv()

# App view state: keep the landing hero and verification results on separate views.
if "app_page" not in st.session_state:
    st.session_state["app_page"] = "home"
if "submitted_number" not in st.session_state:
    st.session_state["submitted_number"] = ""

API_KEY = os.getenv("ABSTRACT_API_KEY", "").strip()

DB_PATH = "data/database/spam_database.db"

MODEL_PATH = "data/models/spam_model.pkl"

API_URL = "https://phoneintelligence.abstractapi.com/v1"
HLR_API_KEY = os.getenv("HLR_API_KEY", "").strip()
HLR_API_SECRET = os.getenv("HLR_API_SECRET", "").strip()
# Treat untouched setup placeholders as missing credentials.
if HLR_API_KEY.upper() in {"YOUR_HLR_API_KEY", "PASTE_HLR_API_KEY_HERE"}:
    HLR_API_KEY = ""
if HLR_API_SECRET.upper() in {"YOUR_HLR_API_SECRET", "PASTE_HLR_API_SECRET_HERE"}:
    HLR_API_SECRET = ""
HLR_API_URL = "https://api.hlrlookup.com/apiv2/hlr"
VERIPHONE_API_KEY = os.getenv("VERIPHONE_API_KEY", "").strip()
VERIPHONE_API_URL = "https://api.veriphone.io/v3/verify"

# Exact SIM/subscriber existence verification is mandatory.
# Abstract API is used only for enrichment after HLR verification.
EXACT_NUMBER_VERIFICATION_REQUIRED = True

# Abstract API quota is exhausted. The project uses Veriphone as the free phone-intelligence provider.
# If Veriphone is not configured, the app safely falls back to local DB + ML mode.
USE_ABSTRACT_API = False

# Local reputation entries used by the project.

KNOWN_SPAM_NUMBERS = {"8037392213"}

# If Abstract API reaches its quota/rate limit or becomes unavailable,

# the project switches to local verification for the rest of the session.

# This prevents repeated failed API calls and keeps the application running.

if "api_unavailable" not in st.session_state:

    st.session_state["api_unavailable"] = False

if "api_unavailable_reason" not in st.session_state:

    st.session_state["api_unavailable_reason"] = ""

# =========================================================

# FUTURISTIC SPAMSHIELD STYLE

# =========================================================

st.markdown(

    """

    <style>

    /* Hide Streamlit website chrome so the WebView looks like an app. */
    header[data-testid="stHeader"] {
        display: none !important;
    }

    [data-testid="stToolbar"] {
        display: none !important;
    }

    footer {
        display: none !important;
    }

    .stAppViewContainer > .main {
        background: transparent !important;
    }

    .stApp {

        background:

            radial-gradient(

                circle at 10% 20%,

                rgba(0, 220, 255, 0.08),

                transparent 28%

            ),

            radial-gradient(

                circle at 90% 80%,

                rgba(0, 255, 170, 0.06),

                transparent 30%

            ),

            linear-gradient(

                135deg,

                #020607 0%,

                #05080b 50%,

                #020304 100%

            );

        color: #f5f7fa;

    }

    .block-container {

        max-width: 1100px;

        padding-top: 3rem;

        padding-bottom: 4rem;

    }

    h1 {

        text-align: center !important;

        font-size: 3.1rem !important;

        font-weight: 800 !important;

        letter-spacing: -1px !important;

        background: linear-gradient(

            90deg,

            #19e6ff,

            #00f5d4,

            #35d9ff

        );

        -webkit-background-clip: text;

        -webkit-text-fill-color: transparent;

        text-shadow:

            0 0 20px rgba(0, 230, 255, 0.20),

            0 0 45px rgba(0, 230, 255, 0.08);

        margin-bottom: 0.25rem !important;

    }

    .hero-subtitle {

        text-align: center;

        color: #8f9ba8;

        font-size: 1rem;

        margin-bottom: 2rem;

        letter-spacing: 0.2px;

    }

    div[data-testid="stTextInput"] {

        margin-top: 0.3rem;

    }

    div[data-testid="stTextInput"] input {

        background: #10161d !important;

        color: #f5f7fa !important;

        border: 1px solid #26333d !important;

        border-radius: 12px !important;

        height: 52px !important;

        padding: 0 18px !important;

        font-size: 1rem !important;

        box-shadow:

            inset 0 0 12px rgba(0, 0, 0, 0.25),

            0 0 0 rgba(0, 230, 255, 0);

    }

    div[data-testid="stTextInput"] input:focus {

        border-color: #00d9ff !important;

        box-shadow:

            0 0 0 1px #00d9ff,

            0 0 22px rgba(0, 217, 255, 0.18) !important;

    }

    div[data-testid="stTextInput"] label {

        color: #aab5c0 !important;

        font-weight: 600 !important;

    }

    div.stButton > button {

        background: linear-gradient(

            135deg,

            #ffffff,

            #dfe8ed

        ) !important;

        color: #071014 !important;

        border: none !important;

        border-radius: 12px !important;

        min-height: 52px !important;

        padding: 0 24px !important;

        font-weight: 750 !important;

        font-size: 0.95rem !important;

        transition: all 0.2s ease !important;

    }

    div.stButton > button:hover {

        transform: translateY(-2px);

        box-shadow:

            0 8px 25px rgba(0, 220, 255, 0.20) !important;

    }

    div[data-testid="stVerticalBlockBorderWrapper"] {

        background:

            linear-gradient(

                145deg,

                rgba(17, 25, 32, 0.94),

                rgba(8, 13, 18, 0.94)

            ) !important;

        border: 1px solid #25333d !important;

        border-radius: 16px !important;

        box-shadow:

            0 10px 35px rgba(0, 0, 0, 0.30),

            inset 0 1px 0 rgba(255,255,255,0.025);

        transition: all 0.25s ease;

    }

    div[data-testid="stVerticalBlockBorderWrapper"]:hover {

        border-color: rgba(0, 220, 255, 0.38) !important;

        box-shadow:

            0 12px 40px rgba(0, 0, 0, 0.40),

            0 0 22px rgba(0, 220, 255, 0.06);

    }

    h3 {

        color: #f5f7fa !important;

        font-weight: 750 !important;

    }

    .big-value {

        color: #ffffff;

        font-size: 1.05rem;

        font-weight: 700;

    }

    .small-label {

        color: #788692;

        font-size: 0.82rem;

    }

    div[data-testid="stAlert"] {

        border-radius: 12px !important;

    }

    [data-testid="stMetricValue"] {

        color: #19e6ff !important;

        font-weight: 800 !important;

    }

    div[data-testid="stAlert"][kind="info"] {

        border-left: 3px solid #19e6ff !important;

    }

    h2 {

        font-weight: 750 !important;

        color: #f4f7fa !important;

    }

    /* =====================================================
       MOBILE / RESPONSIVE APP DESIGN
       ===================================================== */

    @media (max-width: 768px) {

        .block-container {
            max-width: 100% !important;
            padding: 1.25rem 0.9rem 2.25rem !important;
        }

        h1 {
            font-size: 2rem !important;
            line-height: 1.12 !important;
            letter-spacing: -0.6px !important;
            margin-bottom: 0.45rem !important;
        }

        .hero-subtitle {
            font-size: 0.92rem !important;
            line-height: 1.45 !important;
            margin: 0 auto 1.55rem !important;
            max-width: 330px;
        }

        div[data-testid="stTextInput"] {
            margin-top: 0 !important;
            margin-bottom: 0.55rem !important;
        }

        div[data-testid="stTextInput"] label {
            font-size: 0.9rem !important;
            margin-bottom: 0.35rem !important;
        }

        div[data-testid="stTextInput"] input {
            height: 56px !important;
            min-height: 56px !important;
            border-radius: 14px !important;
            padding: 0 16px !important;
            font-size: 1rem !important;
            box-sizing: border-box !important;
        }

        div.stButton {
            width: 100% !important;
            margin: 0.35rem 0 0.8rem !important;
        }

        div.stButton > button {
            width: 100% !important;
            min-height: 56px !important;
            border-radius: 14px !important;
            font-size: 1rem !important;
            padding: 0 18px !important;
        }

        /* Streamlit columns stack naturally on small screens;
           give each result card comfortable spacing. */
        div[data-testid="column"] {
            margin-bottom: 0.8rem !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px !important;
            padding: 0.1rem !important;
        }

        h2 {
            font-size: 1.35rem !important;
            margin-top: 0.9rem !important;
        }

        h3 {
            font-size: 1.08rem !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.7rem !important;
        }

        div[data-testid="stAlert"] {
            border-radius: 12px !important;
            font-size: 0.9rem !important;
        }

        /* Cleaner Streamlit chrome when the app is opened in the
           Android WebView. */
        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        div[data-testid="stToolbar"] {
            visibility: hidden !important;
        }

    }


    /* App background: keep the lower viewport navy rather than showing a black bar. */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background:#111b52 !important;
    }
    [data-testid="stMain"] > div { padding-top:0 !important; }
    .block-container { max-width:100% !important; padding:0 !important; }
    body:has(.st-key-ns-home-page) { overflow:hidden !important; }
    body:has(.st-key-ns-home-page) [data-testid="stAppViewContainer"],
    body:has(.st-key-ns-home-page) [data-testid="stMain"] {
        height:100vh !important; max-height:100vh !important; overflow:hidden !important;
    }
    .st-key-ns-home-page {
        height:100vh !important; max-height:100vh !important; overflow:hidden !important;
        display:flex; flex-direction:column; gap:0 !important;
        background:#111b52 !important;
    }
    .st-key-ns-home-page > div[data-testid="stVerticalBlock"] { gap:0 !important; }
    .st-key-ns-home-page .ns-hero {
        height:calc(100vh - 165px); min-height:550px; max-height:700px;
    }
    /* Clean, professional results header */
    .st-key-ns-results-page [data-testid="stHorizontalBlock"]:first-child {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        width: 100%;
        box-sizing: border-box;
        padding: 12px clamp(16px, 3vw, 40px) !important;
        margin: 0 0 16px !important;
        background: linear-gradient(120deg, #ffffff, #f3f7ff) !important;
        border: 1px solid #e0e7f7;
        border-radius: 0 0 14px 14px;
        box-shadow: 0 5px 18px rgba(5, 15, 55, 0.12);
    }

    .st-key-ns-results-page
    [data-testid="stHorizontalBlock"]:first-child
    > [data-testid="column"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-width: 0 !important;
    }

    .ns-results-top {
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 8px 0;
        box-sizing: border-box;
    }

    .ns-results-brand {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        color: #17214c;
        font-size: clamp(1rem, 1.5vw, 1.3rem);
        font-weight: 800;
        letter-spacing: 0.1px;
        line-height: 1.3;
        text-align: center;
    }

    /* No extra decorative square or pseudo-element */
    .st-key-ns-results-page .ns-results-brand::before { content: none !important; display: none !important; }

    .st-key-ns-results-page
    [data-testid="stHorizontalBlock"]:first-child
    [data-testid="stButton"] {
        width: 100%;
        display: flex;
        justify-content: flex-end;
    }

    .st-key-ns-results-page
    [data-testid="stHorizontalBlock"]:first-child
    [data-testid="stButton"] button {
        width: auto !important;
        min-width: 105px;
        min-height: 42px !important;
        padding: 0 18px !important;
        border-radius: 24px !important;
        background: linear-gradient(135deg, #17245d, #2d4388) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
    }

    .st-key-ns-verification-heading {
        width: 100% !important;
        text-align: center !important;
    }

    .st-key-ns-verification-heading h3 {
        width: 100% !important;
        margin: 12px 0 18px !important;
        color: #ffffff !important;
        font-size: clamp(1.5rem, 2.2vw, 2rem) !important;
        font-weight: 850 !important;
        text-align: center !important;
    }

    @media (max-width: 600px) {
        .st-key-ns-results-page
        [data-testid="stHorizontalBlock"]:first-child {
            gap: 5px !important;
            padding: 8px 10px !important;
        }

        .ns-results-brand {
            gap: 6px;
            font-size: 0.88rem;
        }

        .st-key-ns-results-page
        [data-testid="stHorizontalBlock"]:first-child
        [data-testid="stButton"] button {
            min-width: 0;
            padding: 0 10px !important;
            font-size: 0.8rem !important;
        }
    }

    body:has(.st-key-ns-results-page) { overflow:hidden !important; }
    body:has(.st-key-ns-results-page) [data-testid="stAppViewContainer"],
    body:has(.st-key-ns-results-page) [data-testid="stMain"] {
        height:100vh !important; max-height:100vh !important; overflow:hidden !important;
    }
    .st-key-ns-results-page { padding:0 !important; }
    .st-key-ns-verification-heading h3 { text-align:center !important; width:100% !important; }
    .st-key-ns-results-page > div[data-testid="stVerticalBlock"] { gap:.45rem !important; }
    body:has(.st-key-ns-results-page) h2 { margin:.35rem 0 .5rem !important; font-size:1.25rem !important; }
    body:has(.st-key-ns-results-page) [data-testid="stVerticalBlockBorderWrapper"] { padding:8px !important; }
    body:has(.st-key-ns-results-page) [data-testid="stTabs"] {
        padding:0 clamp(14px,3vw,42px) 12px !important;
    }
    body:has(.st-key-ns-results-page) [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap:8px; border-bottom:1px solid rgba(255,255,255,.14);
    }
    body:has(.st-key-ns-results-page) [data-testid="stTabs"] button[role="tab"] {
        color:#dbe5ff !important; font-weight:750 !important; padding:10px 18px !important;
    }
    body:has(.st-key-ns-results-page) [data-testid="stTabs"] button[aria-selected="true"] {
        color:#fff !important; border-bottom-color:#57d9b5 !important;
    }
    body:has(.st-key-ns-results-page) [data-baseweb="tab-panel"] {
        max-height:calc(100vh - 190px); overflow:auto; padding-top:10px;
    }
    body:has(.st-key-ns-results-page) [data-testid="stVerticalBlockBorderWrapper"] {
        border-color:rgba(185,202,255,.24) !important;
        background:rgba(19,31,85,.72) !important;
    }
    body:has(.st-key-ns-results-page) [data-testid="stDataFrame"] { max-height:280px; overflow:auto; }
    .st-key-ns-results-page div.stButton > button {
        border-radius:22px !important; font-weight:750 !important;
    }
    /* HLR Lookup-inspired full-width telecom hero */
    .block-container { max-width: 100% !important; padding: 0 !important; }
    .ns-topbar {
        height: 82px; width: 100%; display:flex; align-items:center; justify-content:space-between;
        padding: 0 clamp(24px, 7vw, 110px); background:#fff; color:#14204d;
        box-sizing:border-box; position:relative; z-index:3;
    }
    .ns-brand { display:flex; align-items:center; gap:12px; font-weight:800; letter-spacing:.2px; color:#17214c; font-size:1.02rem; }
    .ns-brand-mark { width:25px; height:25px; display:inline-block; background:#ff3157; clip-path:polygon(0 24%,100% 0,70% 100%,49% 61%,24% 83%,34% 50%); }
    .ns-nav-links { display:flex; align-items:center; gap:clamp(12px,2.1vw,32px); color:#3c456a; font-size:.64rem; font-weight:800; letter-spacing:.45px; white-space:nowrap; }
    .ns-top-pill { border:0; border-radius:30px; background:#57d9b5; color:#fff; font-weight:800; font-size:.76rem; letter-spacing:.8px; padding:14px 27px; }
    .ns-hero {
        position:relative; width:100%; box-sizing:border-box; min-height:550px; overflow:hidden;
        display:grid; grid-template-columns:minmax(350px,.9fr) minmax(460px,1.1fr); align-items:center;
        gap:2rem; padding:56px clamp(36px, 9vw, 145px) 88px; margin:0;
        color:#fff; background:
          radial-gradient(ellipse at 19% 68%,rgba(77,104,184,.40),transparent 44%),
          linear-gradient(112deg,#252e69 0%,#17215b 45%,#0b1246 100%);
    }
    .ns-hero:before { content:""; position:absolute; inset:0; pointer-events:none; opacity:.42;
        background-image:radial-gradient(rgba(198,212,255,.55) 1px,transparent 1.3px); background-size:16px 16px;
        mask-image:linear-gradient(90deg,#000 0%,transparent 29%,transparent 100%); }
    .ns-hero:after { content:""; position:absolute; width:56%; height:120%; right:-7%; top:3%; pointer-events:none; opacity:.4;
        background:transparent; border:1px solid rgba(177,194,255,.42); transform:skewY(-29deg) rotate(-5deg); }
    .ns-hero-wave { position:absolute; left:0; right:0; bottom:-1px; height:54px; background:#fff; clip-path:polygon(0 0,100% 100%,0 100%); z-index:2; pointer-events:none; }
    .ns-hero-copy { position:relative; z-index:2; max-width:560px; padding-bottom:22px; }
    .ns-hero-title { text-align:left !important; font-family:Georgia,'Times New Roman',serif !important;
        font-size:clamp(2.7rem,4.15vw,4.25rem) !important; font-weight:700 !important; line-height:1.02 !important;
        letter-spacing:-1.7px !important; margin:0 0 1.65rem !important; color:#fff !important;
        background:none !important; -webkit-text-fill-color:#fff !important; text-shadow:none !important; }
    .ns-hero-title span { color:#fff; }
    .ns-hero-subtitle { color:#c1c9ed; font-size:1.08rem; line-height:1.65; max-width:470px; }
    .ns-hero-art { position:relative; z-index:1; width:100%; min-height:400px; }
    .ns-hero-art svg { width:100%; height:100%; min-height:400px; overflow:visible; }
    .ns-data-panel { animation:nsDrift 5.5s ease-in-out infinite; transform-origin:center; }
    .ns-data-panel.panel-two { animation-delay:-2.3s; }
    .ns-verify-tile { animation:nsDrift 4s ease-in-out infinite; transform-origin:center; }
    .ns-tower-glow { animation:nsTowerGlow 2.2s ease-in-out infinite; }
    .ns-tower-glow.delay { animation-delay:.75s; }
    .ns-tower-glow.delay2 { animation-delay:1.35s; }
    .ns-flow-dot { animation:nsFlow 3.2s linear infinite; }
    .ns-flow-dot.second { animation-delay:-1.6s; }
    .ns-orbit-dot { transform-box:fill-box; transform-origin:center; animation:nsDotBob 2.6s ease-in-out infinite; }
    .ns-orbit-dot.pink { animation-delay:-1.2s; }
    .ns-orbit-dot.green { animation-delay:-.2s; }
    .ns-tower-ring { transform-box:fill-box; transform-origin:center; animation:nsRing 2.8s ease-out infinite; }
    .ns-tower-ring.delay { animation-delay:.9s; }
    .ns-tower-ring.delay2 { animation-delay:1.8s; }
    .ns-ground-glow { animation:nsGroundPulse 3.4s ease-in-out infinite; transform-origin:center; }
    @keyframes nsDrift { 0%,100%{translate:0 0} 50%{translate:0 -10px} }
    @keyframes nsTowerGlow { 0%,100%{opacity:.3; transform:scale(.88)} 50%{opacity:1; transform:scale(1.16)} }
    @keyframes nsFlow { 0%{offset-distance:0%;opacity:0} 12%{opacity:1} 90%{opacity:1} 100%{offset-distance:100%;opacity:0} }
    @keyframes nsDotBob { 0%,100%{translate:0 0;opacity:.85} 50%{translate:0 -8px;opacity:1} }
    @keyframes nsRing { 0%{opacity:.8;scale:.65} 75%,100%{opacity:0;scale:1.6} }
    @keyframes nsGroundPulse { 0%,100%{opacity:.14;scale:.88} 50%{opacity:.32;scale:1.08} }
    .ns-flow-dot { offset-path:path('M 310 210 L 369 244 L 414 220 L 500 100'); }
    /* HLR-style search strip, using the real Streamlit input/button. */
    .st-key-ns-search-row { position:relative; z-index:5; max-width:1220px; margin:-145px auto 38px !important; padding:0 28px 22px !important; box-sizing:border-box; }
    .ns-search-hint { color:#fff; font-size:.91rem; font-weight:650; padding:0 16px 10px; text-shadow:0 1px 5px rgba(0,0,0,.16); }
    .st-key-ns-search-row [data-testid="stHorizontalBlock"] { background:#fff; border:1px solid #d7def0; border-radius:10px; padding:9px 10px 9px 16px; gap:8px !important; box-shadow:0 8px 25px rgba(5,15,55,.12); align-items:center; }
    .st-key-ns-search-row div[data-testid="stAlert"] {
        display:block !important; width:100% !important; margin:0 0 12px !important;
        background:#fff0f0 !important; color:#a3132a !important;
        border:1px solid #ff8a98 !important; border-radius:10px !important;
        padding:10px 14px !important; font-weight:700 !important;
    }
    .st-key-ns-search-row div[data-testid="stTextInput"] { max-width:none; margin:0 !important; padding:0 !important; }
    .st-key-ns-search-row div[data-testid="stTextInput"] > label { display:none !important; }
    .st-key-ns-search-row div[data-testid="stTextInput"] input { background:#fff !important; color:#202a55 !important; border:0 !important; border-radius:5px !important; min-height:48px !important; padding:0 8px !important; box-shadow:none !important; font-size:1rem !important; }
    .st-key-ns-search-row div[data-testid="stTextInput"] input::placeholder { color:#7f879f !important; opacity:.85 !important; }
    .st-key-ns-search-row div.stButton { max-width:none; margin:0 !important; padding:0 !important; }
    .st-key-ns-search-row div.stButton > button { width:100% !important; border-radius:8px !important; min-height:48px !important; white-space:nowrap; background:linear-gradient(120deg,#16b89a,#42d6b5) !important; color:#062b35 !important; border:0 !important; font-weight:800 !important; padding:0 18px !important; }
    @media(max-width:900px) {
      .st-key-ns-search-row { margin:-80px auto 30px !important; padding:0 20px 18px !important; }
      .ns-search-hint { font-size:.82rem; }
    }
    @media(max-width:560px) {
      .st-key-ns-search-row { margin:-45px auto 24px !important; padding:0 14px 16px !important; }
      .st-key-ns-search-row [data-testid="stHorizontalBlock"] { padding:8px; gap:6px !important; }
      .st-key-ns-search-row div.stButton > button { padding:0 9px !important; font-size:.76rem !important; }
      .ns-search-hint { padding:0 8px 8px; }
    }
    @media(max-width:900px) {
      .st-key-ns-home-page .ns-hero{height:calc(100vh - 135px);min-height:520px}
      .ns-topbar{height:68px;padding:0 22px}.ns-nav-links{display:none}.ns-hero{grid-template-columns:1fr;gap:0;padding:48px 26px 70px;min-height:auto}
      .ns-hero-title{font-size:clamp(2.5rem,8vw,3.7rem)!important}.ns-hero-copy{padding-bottom:0}
      .ns-hero-art{min-height:300px}.ns-hero-art svg{min-height:300px}
    }
    @media(max-width:520px) {
      .st-key-ns-home-page .ns-hero{height:calc(100vh - 125px);min-height:500px;padding-bottom:60px}
      .st-key-ns-home-page .ns-hero-art{min-height:235px}
      .ns-brand{font-size:.85rem}.ns-top-pill{padding:11px 16px;font-size:.68rem}
      .ns-hero{padding:38px 20px 28px}.ns-hero-title{font-size:2.45rem!important;letter-spacing:-.8px!important}
      .ns-hero-subtitle{font-size:.98rem}.ns-hero-art{min-height:245px}.ns-hero-art svg{min-height:245px}
    }
    /* Continue the hero palette below the angled divider instead of a black empty strip. */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background:
          radial-gradient(ellipse at 82% 0%, rgba(51,84,165,.20), transparent 44%),
          linear-gradient(112deg, #202b64 0%, #151f57 52%, #0b1246 100%) !important;
    }
    .stAppViewContainer > .main { background:transparent !important; }
    /* Keep the project content centered and the hero artwork unobstructed. */
    .block-container { padding-top:0 !important; }

    </style>

    """,

    unsafe_allow_html=True,

)

# =========================================================

# DATABASE

# =========================================================

def get_connection():

    os.makedirs(

        os.path.dirname(DB_PATH),

        exist_ok=True

    )

    return sqlite3.connect(DB_PATH)

def setup_database():

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(

        """

        CREATE TABLE IF NOT EXISTS spam_numbers (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            mobile_number TEXT UNIQUE NOT NULL,

            spam_reports INTEGER DEFAULT 0,

            genuine_reports INTEGER DEFAULT 0,

            trust_score REAL DEFAULT 50,

            status TEXT DEFAULT 'Unknown'

        )

        """

    )

    cur.execute(

        """

        CREATE TABLE IF NOT EXISTS spam_appeals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            mobile_number TEXT NOT NULL,

            appeal_date TEXT NOT NULL,

            status TEXT DEFAULT 'Pending'

        )

        """

    )

    cur.execute(

        """

        CREATE TABLE IF NOT EXISTS verification_cache (

            mobile_number TEXT PRIMARY KEY,

            result_json TEXT NOT NULL,

            created_at TEXT NOT NULL

        )

        """

    )

    # Verified/report-backed demo intelligence used by the project.

    # The number below is the real-world test number used during testing.

    cur.execute(

        """

        INSERT OR IGNORE INTO spam_numbers

        (mobile_number, spam_reports, genuine_reports, trust_score, status)

        VALUES (?, ?, ?, ?, ?)

        """,

        ("8037392213", 7, 0, 5, "Spam"),

    )

    conn.commit()

    conn.close()

setup_database()

# =========================================================

# MACHINE LEARNING MODEL

# =========================================================

@st.cache_resource

def load_model():

    try:

        return joblib.load(MODEL_PATH)

    except Exception:

        return None

model = load_model()

# =========================================================

# HELPER FUNCTIONS

# =========================================================

def clean_number(value: str) -> str:

    digits = re.sub(

        r"\D+",

        "",

        value or ""

    )

    if digits.startswith("91") and len(digits) == 12:

        digits = digits[2:]

    if len(digits) > 10 and digits.startswith("0"):

        digits = digits[-10:]

    return digits

def api_number(value: str) -> str:

    return "+91" + clean_number(value)

def get_db_reports(number: str):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(

        """

        SELECT

            spam_reports,

            genuine_reports,

            trust_score,

            status

        FROM spam_numbers

        WHERE mobile_number = ?

        """,

        (number,),

    )

    row = cur.fetchone()

    conn.close()

    if row:

        return {

            "spam_reports": int(row[0] or 0),

            "genuine_reports": int(

                row[1] or 0

            ),

            "stored_trust": float(

                row[2]

                if row[2] is not None

                else 50

            ),

            "stored_status": (

                row[3]

                or "Unknown"

            ),

        }

    return {

        "spam_reports": 0,

        "genuine_reports": 0,

        "stored_trust": 50.0,

        "stored_status": "Unknown",

    }

def safe_get(

    data,

    *keys,

    default=None

):

    current = data

    for key in keys:

        if not isinstance(

            current,

            dict

        ):

            return default

        current = current.get(key)

    return (

        default

        if current is None

        else current

    )

# =========================================================

# ABSTRACT API RESPONSE

# =========================================================

def normalize_api_response(

    data,

    number

):

    validation = (

        data.get(

            "phone_validation",

            {}

        )

        if isinstance(data, dict)

        else {}

    )

    carrier = (

        data.get(

            "phone_carrier",

            {}

        )

        if isinstance(data, dict)

        else {}

    )

    location = (

        data.get(

            "phone_location",

            {}

        )

        if isinstance(data, dict)

        else {}

    )

    risk = (

        data.get(

            "phone_risk",

            {}

        )

        if isinstance(data, dict)

        else {}

    )

    fmt = (

        data.get(

            "phone_format",

            {}

        )

        if isinstance(data, dict)

        else {}

    )

    return {

        "mobile_number": safe_get(

            fmt,

            "international",

            default=api_number(number),

        ),

        "carrier": safe_get(

            carrier,

            "name",

            default="Not available",

        ),

        "line_type": safe_get(

            carrier,

            "line_type",

            default="Unknown",

        ),

        "country": safe_get(

            location,

            "country_name",

            default="India",

        ),

        "country_code": safe_get(

            location,

            "country_code",

            default="IN",

        ),

        "region": safe_get(

            location,

            "region",

            default="Not available",

        ),

        "city": safe_get(

            location,

            "city",

            default="Not available",

        ),

        "timezone": safe_get(

            data.get("phone_location", {}) if isinstance(data, dict) else {},

            "timezone",

            default="Not available",

        ),

        "valid": (
            bool(
                safe_get(
                    validation,
                    "is_valid",
                    default=False,
                )
            )
            if "is_valid" in validation
            else None
        ),

        "line_status": safe_get(

            validation,

            "line_status",

            default="Unknown",

        ),
        "validation_confirmed": "is_valid" in validation,

        "is_voip": bool(

            safe_get(

                validation,

                "is_voip",

                default=False,

            )

        ),

        "carrier_available": bool(

            str(

                safe_get(

                    carrier,

                    "name",

                    default="",

                ) or ""

            ).strip()

        ),

        "risk_level": str(

            safe_get(

                risk,

                "risk_level",

                default="unknown",

            )

        ).lower(),

        "abuse": bool(

            safe_get(

                risk,

                "is_abuse_detected",

                default=False,

            )

        ),

        "disposable": bool(

            safe_get(

                risk,

                "is_disposable",

                default=False,

            )

        ),

        "breaches": int(

            safe_get(

                data.get("phone_breaches", {}) if isinstance(data, dict) else {},

                "total_breaches",

                default=0,

            ) or 0

        ),

        "live": True,

    }

# =========================================================

# LOCAL FALLBACK

# =========================================================

def local_fallback(number):

    db = get_db_reports(number)

    return {

        "mobile_number":

            api_number(number),

        "carrier":

            "Not available (Local Fallback)",

        "line_type":

            "Unknown",

        "country":

            "India",

        "country_code":

            "IN",

        "region":

            "Not available",

        "city":

            "Not available",

        "timezone":

            "Asia/Kolkata",

        "valid":
            True,
        "validation_confirmed":
            True,

        "is_voip":
            False,

        "carrier_available":
            False,

        "line_status":

            "Unknown",

        "risk_level":

            "unknown",

        "abuse":

            False,

        "disposable":

            False,

        "breaches":

            0,

        "live":

            False,

        "fallback_spam":

            db["spam_reports"],

        "fallback_genuine":

            db["genuine_reports"],

    }

# =========================================================

# STRICT MOBILE NUMBER VALIDATION
# =========================================================

def is_confirmed_indian_mobile(info):
    """Accept provider-confirmed Indian mobile format, without implying live SIM status."""
    if str(info.get("country_code", "")).upper().strip() not in {"IN", "IND"}:
        return False

    line_type = str(info.get("line_type", "")).lower().strip()
    if not any(x in line_type for x in ("mobile", "wireless", "cell", "cellular")):
        return False

    # HLR can confirm network status. Veriphone can only validate the number range.
    if info.get("network_verified", False):
        return str(info.get("hlr_live_status", "")).upper().strip() in {
            "LIVE", "ABSENT_SUBSCRIBER", "NO_TELESERVICE_PROVISIONED", "DEAD"
        }

    return info.get("validation_source", "").startswith("Veriphone") and info.get("valid") is True

# =========================================================

# GET API DATA

# =========================================================

def normalize_hlr_response(data, number):
    """Convert HLR live-network data into the app's common format."""
    results = data.get("body", {}).get("results", []) if isinstance(data, dict) else []
    if not results or not isinstance(results[0], dict):
        return None, "HLR returned no result."

    result = results[0]
    live_status = str(result.get("live_status", "")).upper().strip()
    number_type = str(result.get("telephone_number_type", "")).upper().strip()
    network = result.get("current_network_details", {}) or {}
    if not isinstance(network, dict):
        network = {}

    carrier_name = str(network.get("name", "")).strip()
    country_iso = str(network.get("country_iso3", "IND")).upper().strip()
    country_name = str(network.get("country_name", "India")).strip() or "India"

    if live_status == "LIVE":
        valid, line_status = True, "active"
    elif live_status == "ABSENT_SUBSCRIBER":
        valid, line_status = True, "absent_subscriber"
    elif live_status == "NO_TELESERVICE_PROVISIONED":
        valid, line_status = True, "active_no_sms"
    elif live_status in {"DEAD", "BAD_FORMAT", "NOT_APPLICABLE"}:
        valid, line_status = False, live_status.lower()
    else:
        valid, line_status = None, live_status.lower() or "unknown"

    info = {
        "mobile_number": "+91" + number,
        "carrier": carrier_name or "Not available",
        "line_type": number_type.lower() or "Unknown",
        "country": country_name,
        "country_code": "IN" if country_iso in {"IND", "IN"} else country_iso,
        "region": "Not available",
        "city": "Not available",
        "timezone": "Asia/Kolkata",
        "valid": valid,
        "validation_confirmed": live_status in {"LIVE", "ABSENT_SUBSCRIBER", "NO_TELESERVICE_PROVISIONED", "DEAD", "BAD_FORMAT", "NOT_APPLICABLE"},
        "is_voip": number_type in {"VOIP", "VO_IP"},
        "carrier_available": bool(carrier_name),
        "risk_level": "unknown",
        "abuse": False,
        "disposable": False,
        "breaches": 0,
        "live": True,
        "network_verified": True,
        "hlr_live_status": live_status,
        "hlr_error": str(result.get("error", "NONE")),
    }
    return info, None


def get_hlr_data(number):
    if not HLR_API_KEY or not HLR_API_SECRET:
        return None, "HLR credentials not configured."

    payload = {
        "api_key": HLR_API_KEY,
        "api_secret": HLR_API_SECRET,
        "requests": [{
            "telephone_number": api_number(number),
            "output_format": "PLUS_E164",
            "save_to_cache": "NO",
        }],
    }

    try:
        response = requests.post(HLR_API_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        if response.status_code != 200:
            return None, f"HLR returned status {response.status_code}."
        info, message = normalize_hlr_response(response.json(), number)
        if info is None:
            return None, message or "HLR returned no usable result."
        return info, None
    except requests.Timeout:
        return None, "HLR request timed out."
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as exc:
        return None, f"HLR request failed: {exc}"



def normalize_veriphone_response(data, number):
    """Convert Veriphone v3 response into the app's common phone-info format."""
    if not isinstance(data, dict):
        return None, "Veriphone returned an invalid response."

    status = str(data.get("status", "")).lower().strip()
    if status != "success":
        return None, str(data.get("message", "Veriphone could not verify this number."))

    phone_valid = data.get("phone_valid")
    phone_type = str(data.get("phone_type", "unknown") or "unknown").strip()
    carrier = str(data.get("current_carrier") or data.get("carrier") or "Not available").strip()
    region = str(data.get("phone_region") or "Not available").strip()
    country = str(data.get("country") or "India").strip()
    country_code = str(data.get("country_code") or "IN").upper().strip()
    timezone_value = data.get("timezone", [])
    if isinstance(timezone_value, list):
        timezone = ", ".join(str(x) for x in timezone_value if x) or "Not available"
    else:
        timezone = str(timezone_value or "Not available")

    info = {
        "mobile_number": str(data.get("international_number") or data.get("e164") or api_number(number)),
        "carrier": carrier,
        "line_type": phone_type,
        "country": country,
        "country_code": country_code,
        "region": region,
        "city": "Not available",
        "valid": bool(phone_valid) if phone_valid is not None else None,
        "validation_confirmed": phone_valid is not None,
        "is_voip": phone_type.lower() == "voip",
        "carrier_available": bool(carrier and carrier.lower() != "not available"),
        "line_status": "valid range" if phone_valid is True else "invalid range" if phone_valid is False else "Unknown",
        "risk_level": "unknown",
        "abuse": False,
        "disposable": False,
        "breaches": 0,
        "live": True,
        "network_verified": False,
        "validation_source": "Veriphone",
        "timezone": timezone,
        "ported": data.get("ported"),
        "veriphone_mode": data.get("mode", "static"),
    }
    return info, None


def get_veriphone_data(number):
    """Free Veriphone validation/enrichment. One successful static lookup costs 1 credit."""
    if not VERIPHONE_API_KEY:
        return None, "Veriphone API key not configured."

    params = {
        "phone": api_number(number),
        "default_country": "IN",
        "mode": "static",
    }
    headers = {"Authorization": f"Bearer {VERIPHONE_API_KEY}"}

    try:
        response = requests.get(
            VERIPHONE_API_URL,
            params=params,
            headers=headers,
            timeout=10,
        )
        data = response.json()
        if response.status_code != 200:
            message = str(data.get("message", f"Veriphone returned status {response.status_code}.")) if isinstance(data, dict) else f"Veriphone returned status {response.status_code}."
            return None, message
        return normalize_veriphone_response(data, number)
    except requests.Timeout:
        return None, "Veriphone request timed out."
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError) as exc:
        return None, f"Veriphone request failed: {exc}"

def get_api_data(number):
    """Prefer HLR live-network status; otherwise use Veriphone for number details.

    Veriphone validation is never represented as proof that a SIM is active or assigned.
    """

    if not HLR_API_KEY or not HLR_API_SECRET:
        if VERIPHONE_API_KEY:
            info, message = get_veriphone_data(number)
            if info is not None:
                info["verification_blocked"] = False
                info["network_verified"] = False
                info["live"] = False
                info["validation_source"] = "Veriphone"
                return info, (
                    "Number format checked by Veriphone. Live SIM/network status "
                    "could not be verified because HLR credentials are not configured."
                )
            return None, message or "Veriphone could not return number details. Check the API key and try again."
        return None, "Veriphone API key is missing. Add VERIPHONE_API_KEY to your .env file."

    hlr_info, hlr_message = get_hlr_data(number)
    if hlr_info is None:
        return None, hlr_message or "HLR could not verify this number."

    status = str(hlr_info.get("hlr_live_status", "")).upper().strip()

    # HLR is authoritative for existence/status. Never replace a negative or
    # inconclusive HLR result with a Veriphone/local guess.
    if status in {"LIVE", "ABSENT_SUBSCRIBER", "NO_TELESERVICE_PROVISIONED"}:
        hlr_info["verification_blocked"] = False
        hlr_info["validation_source"] = "HLR"

        # Add optional secondary enrichment without allowing it to override HLR.
        if VERIPHONE_API_KEY:
            extra, _ = get_veriphone_data(number)
            if extra is not None:
                for key in ("region", "timezone", "ported"):
                    if extra.get(key) not in (None, "", "Not available", []):
                        hlr_info[key] = extra[key]
                if not hlr_info.get("carrier") or hlr_info.get("carrier") == "Not available":
                    hlr_info["carrier"] = extra.get("carrier", hlr_info["carrier"])
                hlr_info["secondary_source"] = "Veriphone"

        return hlr_info, None

    if status in {"DEAD", "BAD_FORMAT", "NOT_APPLICABLE"}:
        hlr_info["verification_blocked"] = False
        hlr_info["validation_source"] = "HLR"
        return hlr_info, (
            "HLR confirmed that this number is not currently assigned to an "
            "existing mobile subscriber."
        )

    # NO_COVERAGE, NOT_AVAILABLE_NETWORK_ONLY, INCONCLUSIVE, etc. are not proof
    # of either existence or non-existence. Stop rather than guessing.
    hlr_info["verification_blocked"] = True
    hlr_info["validation_source"] = "HLR"
    return hlr_info, (
        f"HLR could not establish the subscriber status ({status or 'UNKNOWN'}). "
        "No existence result is being guessed."
    )

# =========================================================

# MACHINE LEARNING PREDICTION

# =========================================================

def model_prediction(number, reports, info):

    digits = clean_number(number)

    spam = int(reports.get("spam_reports", 0))

    genuine = int(reports.get("genuine_reports", 0))

    total = spam + genuine

    spam_ratio = spam / total if total else 0.0

    # Trained Random Forest prediction

    base_probs = {

        "Genuine": 33.0,

        "Suspicious": 34.0,

        "Spam": 33.0,

    }

    active = False

    if model is not None:

        risk_map = {

            "low": 0,

            "medium": 1,

            "high": 2,

            "unknown": 0,

        }

        first_digit = int(digits[0]) if digits else 0

        second_digit = int(digits[1]) if len(digits) > 1 else 0

        row = pd.DataFrame(

            [

                {

                    "length": len(digits),

                    "starts_with_plus": 1,

                    "digit_pattern_1": first_digit,

                    "digit_pattern_2": second_digit,

                    "spam_reports": spam,

                    "genuine_reports": genuine,

                    "total_reports": total,

                    "spam_ratio": spam_ratio,

                    "risk_level": risk_map.get(

                        str(info.get("risk_level", "unknown")).lower(),

                        0,

                    ),

                    "abuse_detected": int(info.get("abuse", False)),

                    "disposable_number": int(info.get("disposable", False)),

                    "is_valid": int(info.get("valid") is True),

                }

            ]

        )

        try:

            raw_probs = model.predict_proba(row)[0]

            classes = list(model.classes_)

            names = {

                0: "Genuine",

                1: "Suspicious",

                2: "Spam",

            }

            base_probs = {

                names.get(int(c), str(c)): float(p * 100)

                for c, p in zip(classes, raw_probs)

            }

            base_probs = {

                "Genuine": base_probs.get("Genuine", 0.0),

                "Suspicious": base_probs.get("Suspicious", 0.0),

                "Spam": base_probs.get("Spam", 0.0),

            }

            active = True

        except Exception:

            active = False

    # ------------------------------------------------------------

    # Deterministic number-pattern signals.

    # These are supporting signals only; they are not treated as

    # proof that a number is spam.

    # ------------------------------------------------------------

    pattern_risk = 0.0

    pattern_reasons = []

    if digits:

        max_run = 1

        run = 1

        for i in range(1, len(digits)):

            if digits[i] == digits[i - 1]:

                run += 1

                max_run = max(max_run, run)

            else:

                run = 1

        if max_run >= 4:

            pattern_risk += 25

            pattern_reasons.append("repeated digits")

        elif max_run == 3:

            pattern_risk += 12

            pattern_reasons.append("repeated digits")

        asc = 1

        desc = 1

        max_asc = 1

        max_desc = 1

        for i in range(1, len(digits)):

            diff = int(digits[i]) - int(digits[i - 1])

            asc = asc + 1 if diff == 1 else 1

            desc = desc + 1 if diff == -1 else 1

            max_asc = max(max_asc, asc)

            max_desc = max(max_desc, desc)

        if max_asc >= 4 or max_desc >= 4:

            pattern_risk += 18

            pattern_reasons.append("sequential digits")

        if len(digits) >= 6 and digits[:3] == digits[3:6]:

            pattern_risk += 15

            pattern_reasons.append("repeated block")

        unique_count = len(set(digits))

        if unique_count <= 2:

            pattern_risk += 20

            pattern_reasons.append("low digit diversity")

        elif unique_count <= 5:

            pattern_risk += 10

        if digits.startswith("140"):

            pattern_risk += 22

            pattern_reasons.append("140-series promotional signal")

    # ------------------------------------------------------------

    # Reputation / API signals

    # ------------------------------------------------------------

    known_spam = digits in KNOWN_SPAM_NUMBERS

    report_risk = spam_ratio * 100 if total else 0.0

    api_risk = {

        "low": 10,

        "medium": 45,

        "high": 75,

        "unknown": 35,

    }.get(

        str(info.get("risk_level", "unknown")).lower(),

        35,

    )

    if info.get("abuse"):

        api_risk += 35

    if info.get("disposable"):

        api_risk += 20

    if not info.get("valid", True):

        api_risk += 35

    line_type = str(info.get("line_type", "")).lower()

    if "voip" in line_type:

        api_risk += 15

    breaches = int(info.get("breaches", 0) or 0)

    if breaches >= 3:

        api_risk += 10

    api_risk = min(api_risk, 100)

    # A number with no community reports must NOT automatically

    # become Genuine. Unknown reputation remains conservative.

    if total == 0:

        community_component = 35.0

    else:

        community_component = report_risk

    # ML output is one signal, not the final decision.

    model_spam = base_probs["Spam"]

    # Small, explainable number-profile signal. It is deliberately weak and
    # never decides whether a number exists; it only adds variation when
    # different numbers have different digit characteristics.
    digit_diversity = (len(set(digits)) / 10.0) * 100 if digits else 0.0
    profile_risk = max(
        0.0,
        min(100.0, 55.0 - (digit_diversity - 50.0) * 0.20),
    )

    combined_risk = (
        community_component * 0.35
        + api_risk * 0.30
        + pattern_risk * 0.15
        + model_spam * 0.15
        + profile_risk * 0.05
    )

    if known_spam:

        combined_risk = 98.0

        pattern_reasons.append("known spam report database match")

    combined_risk = max(0.0, min(100.0, combined_risk))

    # Convert evidence into stable probabilities.

    genuine_probability = max(

        1.0,

        base_probs["Genuine"] * (1.0 - combined_risk / 140.0),

    )

    suspicious_probability = max(

        1.0,

        base_probs["Suspicious"] + abs(combined_risk - 50.0) * 0.15,

    )

    spam_probability = max(

        1.0,

        base_probs["Spam"] * 0.70 + combined_risk * 0.30,

    )

    if known_spam:

        probabilities = {

            "Genuine": 1.0,

            "Suspicious": 4.0,

            "Spam": 95.0,

        }

    elif info.get("abuse") or info.get("valid") is False:

        probabilities = {

            "Genuine": 3.0,

            "Suspicious": 12.0,

            "Spam": 85.0,

        }

    elif report_risk >= 70 or str(info.get("risk_level", "")).lower() == "high":

        probabilities = {

            "Genuine": 5.0,

            "Suspicious": 15.0,

            "Spam": 80.0,

        }

    else:

        probabilities = {

            "Genuine": genuine_probability,

            "Suspicious": suspicious_probability,

            "Spam": spam_probability,

        }

        total_probability = sum(probabilities.values())

        probabilities = {

            key: round(value / total_probability * 100, 2)

            for key, value in probabilities.items()

        }

    prediction = max(probabilities, key=probabilities.get)

    # Evidence-based final ML class.

    if known_spam:

        prediction = "Spam"

    elif (

        info.get("abuse")

        or not info.get("valid", True)

        or report_risk >= 70

        or str(info.get("risk_level", "")).lower() == "high"

    ):

        prediction = "Spam"

    elif (

        report_risk >= 40

        or str(info.get("risk_level", "")).lower() == "medium"

        or combined_risk >= 45

        or digits.startswith("140")

    ):

        prediction = "Suspicious"

    return {

        "prediction": prediction,

        "probabilities": probabilities,

        "active": active,

        "risk_score": round(combined_risk, 1),

        "pattern_risk": round(pattern_risk, 1),

        "combined_risk": round(combined_risk, 1),

        "pattern_reasons": pattern_reasons,

        "known_spam": known_spam,

        "digit_diversity": round((len(set(digits)) / 10.0) * 100, 1) if digits else 0.0,

    }

def calculate_result(reports, info, ml):

    # A network-confirmed DEAD number is not a spam classification.
    # It is a genuine network status result: the number is not assigned.
    hlr_status = str(info.get("hlr_live_status", "")).upper().strip()
    if info.get("network_verified") and hlr_status in {"DEAD", "BAD_FORMAT", "NOT_APPLICABLE"}:
        return 0.0, "Not Assigned"

    spam = int(reports.get("spam_reports", 0))

    genuine = int(reports.get("genuine_reports", 0))

    total = spam + genuine

    if total > 0:

        report_score = (genuine / total) * 100

    else:

        # No community reports means unknown, not automatically genuine.

        report_score = 50.0

    api_score = {

        "low": 85,

        "medium": 50,

        "high": 20,

        "unknown": 45,

    }.get(

        str(info.get("risk_level", "unknown")).lower(),

        45,

    )

    if info.get("abuse"):

        api_score -= 35

    if info.get("disposable"):

        api_score -= 15

    if not info.get("valid", True):

        api_score -= 35

    if "voip" in str(info.get("line_type", "")).lower():

        api_score -= 10

    api_score = max(0, min(100, api_score))

    genuine_probability = float(

        ml["probabilities"].get("Genuine", 0.0)

    )

    digit_profile = float(ml.get("digit_diversity", 50.0))
    profile_score = max(0.0, min(100.0, 45.0 + (digit_profile - 50.0) * 0.30))

    if info.get("network_verified"):
        validation_score = 100.0 if info.get("valid") is True else 0.0
    else:
        validation_score = 85.0 if info.get("validation_confirmed") else 55.0

    trust = (
        report_score * 0.25
        + genuine_probability * 0.30
        + api_score * 0.20
        + (100 - ml.get("risk_score", 50.0)) * 0.15
        + profile_score * 0.05
        + validation_score * 0.05
    )

    # Strong evidence overrides the numerical trust calculation.

    if ml.get("known_spam"):

        trust = min(trust, 10.0)

        status = "Likely Spam"

    elif (

        info.get("abuse")

        or not info.get("valid", True)

        or ml["prediction"] == "Spam"

        or str(info.get("risk_level", "")).lower() == "high"

        or (total > 0 and spam / total >= 0.70)

    ):

        trust = min(trust, 30.0)

        status = "Likely Spam"

    elif total == 0 and not ml.get("pattern_reasons") and ml.get("risk_score", 0) < 65:
        # No community reports means there is not enough evidence to call a number safe or spam.
        status = "Insufficient Data"
    elif (
        ml["prediction"] == "Suspicious"
        or str(info.get("risk_level", "")).lower() == "medium"
        or trust < 70
    ):
        trust = min(trust, 69.9)
        status = "Suspicious"
    else:
        status = "Likely Genuine"

    return (

        round(max(0, min(100, trust)), 1),

        status,

    )

CACHE_VERSION = 9

def get_cached_result(number):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(

        "SELECT result_json FROM verification_cache WHERE mobile_number = ?",

        (number,),

    )

    row = cur.fetchone()

    conn.close()

    if not row:

        return None

    try:

        result = json.loads(row[0])

        # Ignore results generated by older logic.

        if result.get("_cache_version") != CACHE_VERSION:

            return None

        return result

    except Exception:

        return None

def save_cached_result(number, result):

    result = dict(result)

    result["_cache_version"] = CACHE_VERSION

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(

        """

        INSERT OR REPLACE INTO verification_cache

        (mobile_number, result_json, created_at)

        VALUES (?, ?, ?)

        """,

        (

            number,

            json.dumps(result),

            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        ),

    )

    conn.commit()

    conn.close()

def save_appeal(number):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(

        """

        INSERT INTO spam_appeals

        (

            mobile_number,

            appeal_date,

            status

        )

        VALUES (?, ?, ?)

        """,

        (

            number,

            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

            "Pending",

        ),

    )

    conn.commit()

    appeal_id = cur.lastrowid

    conn.close()

    return appeal_id

def save_appeal(number):

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(

        """

        INSERT INTO spam_appeals

        (

            mobile_number,

            appeal_date,

            status

        )

        VALUES (?, ?, ?)

        """,

        (

            number,

            datetime.now().strftime(

                "%Y-%m-%d %H:%M:%S"

            ),

            "Pending",

        ),

    )

    conn.commit()

    appeal_id = cur.lastrowid

    conn.close()

    return appeal_id

# =========================================================

# HEADER

# =========================================================

if st.session_state.get("app_page", "home") == "home":
    with st.container(key="ns-home-page"):
        st.markdown(
            """
            <div class="ns-topbar">
              <div class="ns-brand"><span class="ns-brand-mark"></span><span>SpamShield</span></div>
              <nav class="ns-nav-links" aria-label="Main navigation">
                <span>HOME</span><span>NUMBER CHECK</span><span>SPAM VERIFICATION</span><span>ABOUT</span>
              </nav>
              <div class="ns-top-pill">VERIFY NUMBER</div>
            </div>
            <section class="ns-hero">
              <div class="ns-hero-copy">
                <h1 class="ns-hero-title">Number Spam<br>Verification<br>System</h1>
                <div class="ns-hero-subtitle">Check if a phone number is Spam or Safe.</div>
              </div>
              <div class="ns-hero-art" aria-hidden="true">
                <svg viewBox="0 0 720 430" role="img" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="panelFill" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f5f8ff"/><stop offset="1" stop-color="#7298e9"/></linearGradient>
                    <linearGradient id="panelScreen" x1="0" y1="0" x2="0.9" y2="1"><stop offset="0" stop-color="#3f5fae"/><stop offset="1" stop-color="#263875"/></linearGradient>
                    <linearGradient id="tileFill" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#d9fff5"/></linearGradient>
                    <linearGradient id="towerLine" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#9bbaff"/></linearGradient>
                    <filter id="tileShadow" x="-60%" y="-60%" width="220%" height="240%"><feGaussianBlur stdDeviation="13"/></filter>
                  </defs>
                  <!-- Fine geometric network paths like the HLR Lookup hero -->
                  <g fill="none" stroke="#b9c8ff" stroke-width="1.1" opacity=".23">
                    <path d="M12 94 L138 165 L138 18 L300 112 L300 238 L424 164 L424 20 L572 104 L704 28"/>
                    <path d="M12 354 L142 278 L246 346 L372 277 L500 354 L705 248"/>
                    <path d="M405 0 L520 70 L520 190 L628 120 L706 162"/>
                    <path d="M390 428 L390 350 L478 300 L566 350 L705 276"/>
                    <path d="M548 44 L650 4 M604 216 L704 154"/>
                  </g>
                  <!-- Three small floating data panes -->
                  <g class="ns-data-panel panel-two" transform="translate(176 108) rotate(-7 11 18)">
                    <rect width="23" height="38" rx="2" fill="url(#panelFill)" stroke="#fff" stroke-width="1.6"/><rect x="4" y="4" width="15" height="30" fill="url(#panelScreen)"/>
                  </g>
                  <g class="ns-data-panel" transform="translate(197 78) rotate(-7 11 18)">
                    <rect width="23" height="38" rx="2" fill="url(#panelFill)" stroke="#fff" stroke-width="1.6"/><rect x="4" y="4" width="15" height="30" fill="url(#panelScreen)"/>
                  </g>
                  <g class="ns-data-panel panel-two" transform="translate(206 139) rotate(-7 11 18)">
                    <rect width="23" height="38" rx="2" fill="url(#panelFill)" stroke="#fff" stroke-width="1.6"/><rect x="4" y="4" width="15" height="30" fill="url(#panelScreen)"/>
                  </g>
                  <!-- Main floating telecom data/report panel -->
                  <g class="ns-data-panel" transform="translate(240 82) rotate(-7 33 67)">
                    <rect x="-7" y="-5" width="72" height="137" rx="3" fill="#07143d" opacity=".28"/>
                    <rect x="0" y="0" width="67" height="130" rx="3" fill="url(#panelFill)" stroke="#f7f9ff" stroke-width="2.1"/>
                    <rect x="6" y="7" width="55" height="116" rx="2" fill="url(#panelScreen)"/>
                    <circle cx="15" cy="17" r="3" fill="#e9f4ff"/><path d="M23 16 H51 M23 21 H43" stroke="#eaf4ff" stroke-width="1.3"/>
                    <path d="M12 34 H54 M12 42 H50 M12 50 H54 M12 58 H45 M12 72 H54 M12 80 H50 M12 88 H54 M12 96 H39 M12 108 H51" stroke="#d8e7ff" stroke-width="1.6" opacity=".85"/>
                  </g>
                  <!-- Connection from the data panel to the central verification tile -->
                  <g fill="none" stroke="#56e3cf" stroke-width="1.6">
                    <path d="M310 210 L369 244 L414 220"/>
                    <path d="M406 220 L414 220 L410 228"/>
                    <path d="M414 220 L438 234 L466 220" opacity=".42"/>
                  </g>
                  <path d="M310 210 L369 244 L414 220" fill="none" stroke="#66f0df" stroke-width="1.3" stroke-dasharray="5 8" opacity=".75"/>
                  <circle class="ns-flow-dot" r="4.3" fill="#66ffe7"/>
                  <circle class="ns-flow-dot second" r="3.2" fill="#c6e4ff"/>
                  <!-- Three detailed lattice mobile network towers -->
                  <g fill="none" stroke="url(#towerLine)" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round">
                    <g transform="translate(500 100)">
                      <path d="M0 8 L-36 112 H36 Z M0 8 L0 112 M-8 29 L8 29 M-14 47 L14 47 M-21 67 L21 67 M-28 89 L28 89 M-36 112 L21 67 L-21 67 L36 112 M-28 89 L14 47 L-14 47 L28 89 M-14 47 L0 8 L14 47"/>
                      <path d="M-9 20 H9 L14 29 H-14 Z"/>
                    </g>
                    <g transform="translate(574 128) scale(.78)">
                      <path d="M0 8 L-36 112 H36 Z M0 8 L0 112 M-8 29 L8 29 M-14 47 L14 47 M-21 67 L21 67 M-28 89 L28 89 M-36 112 L21 67 L-21 67 L36 112 M-28 89 L14 47 L-14 47 L28 89 M-14 47 L0 8 L14 47"/>
                    </g>
                    <g transform="translate(638 150) scale(.57)">
                      <path d="M0 8 L-36 112 H36 Z M0 8 L0 112 M-8 29 L8 29 M-14 47 L14 47 M-21 67 L21 67 M-28 89 L28 89 M-36 112 L21 67 L-21 67 L36 112 M-28 89 L14 47 L-14 47 L28 89 M-14 47 L0 8 L14 47"/>
                    </g>
                  </g>
                  <!-- Pulsing telecom signal waves around each tower, like the reference animation -->
                  <g fill="none" stroke="#5cebd5" stroke-width="1.35" stroke-linecap="round">
                    <circle class="ns-tower-ring" cx="500" cy="89" r="9" opacity=".65"/>
                    <circle class="ns-tower-ring delay" cx="574" cy="117" r="8" opacity=".65"/>
                    <circle class="ns-tower-ring delay2" cx="638" cy="139" r="7" opacity=".65"/>
                    <path class="ns-tower-glow" d="M489 89 Q477 73 489 61 Q502 74 491 85"/>
                    <path class="ns-tower-glow delay" d="M565 119 Q554 104 565 93 Q577 105 567 115"/>
                    <path class="ns-tower-glow delay2" d="M633 139 Q623 126 633 116 Q644 128 635 136"/>
                  </g>
                  <g fill="#61e8d8"><circle cx="500" cy="100" r="2.7"/><circle cx="574" cy="128" r="2.4"/><circle cx="638" cy="150" r="2.1"/></g>
                  <!-- Soft glow and moving ground shadow under the floating central tile -->
                  <ellipse class="ns-ground-glow" cx="398" cy="302" rx="77" ry="23" fill="#030b30" opacity=".35"/>
                  <ellipse class="ns-ground-glow" cx="398" cy="282" rx="70" ry="30" fill="#55dfd8" opacity=".2" filter="url(#tileShadow)"/>
                  <!-- Central tilted white/teal HLR-style verification tile -->
                  <g class="ns-verify-tile" transform="translate(328 246)">
                    <path d="M0 28 L62 -7 Q70 -11 78 -7 L132 24 Q143 31 132 39 L72 74 Q64 78 56 73 L0 41 Q-10 34 0 28Z" fill="#07133d" opacity=".7" transform="translate(0 12)"/>
                    <path d="M0 16 L62 -19 Q70 -23 78 -19 L132 12 Q143 19 132 27 L72 62 Q64 66 56 61 L0 29 Q-10 22 0 16Z" fill="url(#tileFill)" stroke="#ffffff" stroke-width="1.5"/>
                    <path d="M43 11 L69 -4 L95 11 L69 27 Z" fill="none" stroke="#26366e" stroke-width="2.8" stroke-linejoin="round"/>
                    <path d="M43 11 L69 27 L95 11 M69 27 L69 40" fill="none" stroke="#26366e" stroke-width="2.8" stroke-linejoin="round"/>
                    <path d="M58 14 L66 19 L80 5" fill="none" stroke="#4dc9b6" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>
                  </g>
                  <!-- Branching data flow: arrows point cleanly toward the smaller data cylinders -->
                  <g fill="none" stroke="#36d9d2" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M397 309 L426 329 L451 342"/>
                    <path d="M426 329 L466 326 L486 336"/>
                    <!-- Arrow into the pink cylinder -->
                    <path d="M451 342 L443 340 M451 342 L448 334"/>
                    <!-- Arrow into the green cylinder -->
                    <path d="M486 336 L477 335 M486 336 L482 328"/>
                  </g>
                  <circle cx="426" cy="329" r="4.8" fill="#17366e" stroke="#43e3d6" stroke-width="1.8"/>
                  <circle cx="426" cy="329" r="1.8" fill="#71fff0"/>
                  <!-- Smaller pink data cylinder -->
                  <g class="ns-orbit-dot pink">
                    <ellipse cx="451" cy="365" rx="19" ry="5.5" fill="#07133d" opacity=".32"/>
                    <path d="M432 350 V364 C432 369 440.5 373 451 373 C461.5 373 470 369 470 364 V350Z" fill="#e94b8a"/>
                    <ellipse cx="451" cy="350" rx="19" ry="6.5" fill="#ff669f" stroke="#ff9fc3" stroke-width=".9"/>
                    <path d="M451 346 V354 M447 350 H455" stroke="#fff1f7" stroke-width="1.2" stroke-linecap="round"/>
                  </g>
                  <!-- Smaller green data cylinder, moved closer to the pink one -->
                  <g class="ns-orbit-dot green">
                    <ellipse cx="503" cy="339" rx="19" ry="5.5" fill="#07133d" opacity=".32"/>
                    <path d="M484 325 V338 C484 343 492.5 347 503 347 C513.5 347 522 343 522 338 V325Z" fill="#42cda8"/>
                    <ellipse cx="503" cy="325" rx="19" ry="6.5" fill="#62dcb9" stroke="#8bf0d4" stroke-width=".9"/>
                    <path d="M494 327 Q503 332 512 327" fill="none" stroke="#b6ffeb" stroke-width="1" opacity=".8"/>
                  </g>
                </svg>
              </div>
              <div class="ns-hero-wave" aria-hidden="true"></div>
            </section>
            """,
            unsafe_allow_html=True,
        )

        # =========================================================

        # INPUT

        # =========================================================

        with st.container(key="ns-search-row"):
            st.markdown(
                '<div class="ns-search-hint">Enter your 10-digit Indian mobile number to check its spam status.</div>',
                unsafe_allow_html=True,
            )
            search_col, button_col = st.columns([6, 1], gap="small", vertical_alignment="bottom")
            with search_col:
                if st.session_state.get("validation_error"):
                    st.error(st.session_state["validation_error"])
                    st.session_state["validation_error"] = None

                number_input = st.text_input(
                    "Enter Mobile Number",
                    placeholder="Enter 10-digit Indian mobile number",
                    max_chars=10,
                    label_visibility="collapsed",
                )
            with button_col:
                verify = st.button(
                    "Verify Number",
                    type="secondary",
                    use_container_width=True,
                )
else:
    number_input = st.session_state.get("submitted_number", "")
    verify = False

# =========================================================

# VERIFICATION

# =========================================================

if verify:
    # Clear the previous result so an invalid number never shows
    # the result of the number checked before it.
    st.session_state.pop("result", None)

    number = clean_number(number_input)

    # Show a dedicated message when the user presses Verify without typing anything.
    if not number.strip():
      st.session_state["validation_message"] = (
        "Please enter a mobile number first."
    )
    st.session_state["app_page"] = "home"
    st.rerun()

    # Basic Indian mobile-number format check.
    # This also avoids wasting an API request on obviously invalid input.
    if len(number) != 10 or number[0] not in "6789":
        st.session_state["validation_error"] = "This number is invalid or does not exist."
        st.session_state["app_page"] = "home"
        st.rerun()


    st.session_state["submitted_number"] = number
    cached_result = get_cached_result(number)

    if cached_result:
        cached_info = cached_result.get("info", {})

        # Accept cache entries from HLR or successful Veriphone format validation.
        cached_hlr_status = str(cached_info.get("hlr_live_status", "")).upper().strip()
        cached_hlr_ok = (
            cached_info.get("network_verified")
            and cached_hlr_status in {
                "LIVE", "ABSENT_SUBSCRIBER", "NO_TELESERVICE_PROVISIONED",
                "DEAD", "BAD_FORMAT", "NOT_APPLICABLE"
            }
        )
        cached_veriphone_ok = (
            str(cached_info.get("validation_source", "")).startswith("Veriphone")
            and cached_info.get("validation_confirmed")
            and cached_info.get("valid") is True
        )
        if not (cached_hlr_ok or cached_veriphone_ok):
            st.session_state.pop("result", None)
            cached_result = None
        else:
            st.session_state["result"] = cached_result

        st.session_state["result"] = cached_result

    else:
        with st.spinner("Checking number information..."):
            reports = get_db_reports(number)
            info, api_message = get_api_data(number)

            # Never let the ML model invent phone-number existence.
            if info is None or info.get("verification_blocked", False):
                st.error(api_message or "Number details could not be verified. Check the API key and try again.")
                st.stop()

            hlr_status = str(info.get("hlr_live_status", "")).upper().strip()

            if not is_confirmed_indian_mobile(info):
                # A DEAD HLR result is a genuine negative result, so show it
                # instead of pretending it was merely a bad input.
                if info.get("network_verified") and hlr_status in {"DEAD", "BAD_FORMAT", "NOT_APPLICABLE"}:
                    pass
                else:
                    st.error(
                        api_message
                        or "The live network could not confirm this mobile number."
                    )
                    st.stop()

            if not info.get("live", False):
                reports["spam_reports"] = int(
                    info.get("fallback_spam", reports["spam_reports"])
                )
                reports["genuine_reports"] = int(
                    info.get("fallback_genuine", reports["genuine_reports"])
                )

            ml = model_prediction(number, reports, info)
            trust, status = calculate_result(reports, info, ml)

            verification_result = {
                "number": number,
                "reports": reports,
                "info": info,
                "ml": ml,
                "trust": trust,
                "status": status,
                "api_message": api_message,
            }

            save_cached_result(number, verification_result)
            st.session_state["result"] = verification_result

    result_now = st.session_state.get("result")
    if result_now:
        st.session_state["app_page"] = "results"
        st.rerun()
    # Status banner intentionally omitted; details are shown in the result cards.

# =========================================================

# RESULTS

# =========================================================

if st.session_state.get("app_page") == "results":
    with st.container(key="ns-results-page"):
        header_left, header_center, header_right = st.columns(
            [1, 5, 1],
            vertical_alignment="center",
        )
        # Empty left column balances the Home button on the right.
        with header_left:
            st.empty()
        with header_center:
            st.markdown(
                """
                <div class="ns-results-top">
                    <div class="ns-results-brand">
                        <span>📞</span>
                        <span>Number Spam Verification System</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with header_right:
            if st.button(
                "← Home",
                key="back_to_home",
                use_container_width=True,
            ):
                st.session_state["app_page"] = "home"
                st.rerun()

result = st.session_state.get(

    "result"

)

if result and st.session_state.get("app_page") == "results":

    number = result[

        "number"

    ]

    reports = result[

        "reports"

    ]

    info = result[

        "info"

    ]

    ml = result[

        "ml"

    ]

    trust = result[

        "trust"

    ]

    status = result[

        "status"

    ]

    with st.container(key="ns-verification-heading"):
        st.subheader("Verification Result")

    tab_overview, tab_ml, tab_appeal = st.tabs(
        ["Overview", "Machine Learning", "Spam Appeal"]
    )

    with tab_overview:
        # =====================================================

            # ROW 1

        # =====================================================

        c1, c2, c3 = st.columns(3)

        # =====================================================

        # INFORMATION

        # =====================================================

        with c1:

            with st.container(

                border=True

            ):

                st.markdown(

                    "### 📞 Information"

                )

                st.markdown(

                    f"**Mobile Number:** "

                    f"{info['mobile_number']}"

                )

                st.markdown(

                    f"**Carrier / Network:** "

                    f"{info['carrier']}"

                )

                st.markdown(

                    f"**Line Type:** "

                    f"{info['line_type']}"

                )

                st.markdown(

                    f"**Country:** "

                    f"{info['country']}"

                )

                st.markdown(

                    f"**Valid:** "

                    f"{'Yes' if info['valid'] is True else 'No' if info['valid'] is False else 'Not verified'}"

                )

                st.markdown(

                    f"**Line Status:** "

                    f"{info['line_status']}"

                )

                st.markdown(

                    f"**Region:** "

                    f"{info['region']}"

                )

                st.markdown(

                    f"**City:** "

                    f"{info['city']}"

                )

                st.markdown(

                    f"**Timezone:** "

                    f"{info.get('timezone', 'Not available')}"

                )

                network_status = (
                    str(info.get("hlr_live_status", "Unknown"))
                    if info.get("network_verified")
                    else "Not checked (HLR not configured)"
                    if str(info.get("validation_source", "")).startswith("Veriphone")
                    else "Unavailable"
                )
                st.markdown(f"**Live Network Status:** {network_status}")

        # =====================================================

        # SPAM REPORTS

        # =====================================================

        with c2:

            with st.container(

                border=True

            ):

                st.markdown(

                    "### 📊 Spam Reports"

                )

                st.markdown(

                    f"**Spam Reports:** "

                    f"{reports['spam_reports']}"

                )

                st.markdown(

                    f"**Genuine Reports:** "

                    f"{reports['genuine_reports']}"

                )

                total_reports = (

                    reports[

                        "spam_reports"

                    ]

                    +

                    reports[

                        "genuine_reports"

                    ]

                )

                st.markdown(

                    f"**Total Reports:** "

                    f"{total_reports}"

                )

                if total_reports == 0:

                    st.info(

                        "No community reports are "

                        "currently available for "

                        "this number."

                    )

        # =====================================================

        # RISK ANALYSIS

        # =====================================================

        with c3:

            with st.container(

                border=True

            ):

                st.markdown(

                    "### 🛡️ Risk Analysis"

                )

                dynamic_risk = float(

                    ml.get(

                        "risk_score",

                        50.0,

                    )

                )

                if dynamic_risk < 35:

                    display_risk = "Low"

                elif dynamic_risk < 65:

                    display_risk = "Medium"

                else:

                    display_risk = "High"

                st.markdown(

                    f"**Risk Level:** "

                    f"{display_risk}"

                )

                st.markdown(

                    f"**Abuse Detected:** "

                    f"{'Yes' if info['abuse'] else 'No'}"

                )

                st.markdown(

                    f"**Disposable:** "

                    f"{'Yes' if info['disposable'] else 'No'}"

                )

                if info.get("network_verified"):
                    verification_type = "HLR Network Verification"
                elif str(info.get("validation_source", "")).startswith("Veriphone"):
                    verification_type = "Veriphone Number Validation"
                else:
                    verification_type = "Local Database / ML Only"

                st.markdown(

                    f"**Verification:** "

                    f"{verification_type}"

                )

    with tab_ml:
        # =====================================================

            # ROW 2

        # =====================================================

        c4, c5 = st.columns(2)

        # =====================================================

        # MACHINE LEARNING

        # =====================================================

        with c4:

            with st.container(

                border=True

            ):

                st.markdown(

                    "### 🤖 Machine Learning Analysis"

                )

                model_status = (

                    "Active"

                    if ml["active"]

                    else "Fallback"

                )

                st.markdown(

                    f"**Model Status:** "

                    f"{model_status}"

                )

                display_prediction = ml["prediction"]
                if (reports.get("spam_reports", 0) + reports.get("genuine_reports", 0)) == 0 and not ml.get("known_spam") and ml.get("risk_score", 0) < 65:
                    display_prediction = "Inconclusive (no report data)"

                st.markdown(f"**Prediction:** {display_prediction}")

                st.markdown(

                    f"**Genuine Probability:** "

                    f"{ml['probabilities']['Genuine']:.2f}%"

                )

                st.markdown(

                    f"**Suspicious Probability:** "

                    f"{ml['probabilities']['Suspicious']:.2f}%"

                )

                st.markdown(

                    f"**Spam Probability:** "

                    f"{ml['probabilities']['Spam']:.2f}%"

                )

                st.caption(

                    "The Machine Learning model analyzes "

                    "number characteristics, community "

                    "reports, and risk-related features "

                    "to generate a classification."

                )

        # =====================================================

        # FINAL VERIFICATION

        # =====================================================

        with c5:

            with st.container(

                border=True

            ):

                st.markdown(

                    "### 🎯 Final Verification"

                )

                st.metric(

                    "Trust Score",

                    f"{trust:.1f}%",

                )

                st.markdown(

                    "**Final Status:**"

                )

                if status == "Likely Genuine":

                    st.success(

                        "Likely Genuine"

                    )

                elif status == "Suspicious":

                    st.warning(

                        "Suspicious"

                    )

                elif status == "Insufficient Data":
                    st.info("Insufficient Data — no community reports available")

                elif status == "Not Assigned":
                    st.error("Not Assigned / DEAD")

                else:

                    st.error(

                        "Likely Spam"

                    )

    with tab_appeal:
        # =====================================================

            # SPAM APPEAL

        # =====================================================

        with st.container(

            border=True

        ):

            st.markdown(

                "### 📄 Spam Appeal"

            )

            st.write(

                "If you believe this number has been "

                "wrongly marked as spam, you can submit "

                "an appeal for verification."

            )

            if st.button(

                "This Number Is Not Spam",

                key="appeal_button",

            ):

                try:

                    appeal_id = save_appeal(

                        number

                    )

                    st.success(

                        "Appeal request submitted successfully."

                    )

                    st.info(

                        f"Appeal ID: {appeal_id}"

                    )

                except Exception as exc:

                    st.error(

                        f"Unable to submit appeal: {exc}"

                    )

            # =================================================

            # APPEAL HISTORY

            # =================================================

            conn = get_connection()

            appeals_df = pd.read_sql_query(

                """

                SELECT

                    id AS Appeal_ID,

                    mobile_number AS Mobile_Number,

                    appeal_date AS Appeal_Date,

                    status AS Status

                FROM spam_appeals

                WHERE mobile_number = ?

                ORDER BY id DESC

                """,

                conn,

                params=(number,),

            )

            conn.close()

            if not appeals_df.empty:

                st.write(

                    "**Appeal History**"

                )

                st.dataframe(

                    appeals_df,

                    use_container_width=True,

                    hide_index=True,

                )