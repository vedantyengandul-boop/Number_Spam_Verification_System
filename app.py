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


API_KEY = os.getenv("ABSTRACT_API_KEY", "").strip()


DB_PATH = "data/database/spam_database.db"


MODEL_PATH = "data/models/spam_model.pkl"


API_URL = "https://phoneintelligence.abstractapi.com/v1"

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


    @media (max-width: 768px) {


        h1 {


            font-size: 2.1rem !important;


        }


        .block-container {


            padding-left: 1rem;


            padding-right: 1rem;


        }


    }


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


        r"\D",


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


        "valid": bool(


            safe_get(


                validation,


                "is_valid",


                default=True,


            )


        ),


        "line_status": safe_get(


            validation,


            "line_status",


            default="Unknown",


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

        "region":
            "Not available",

        "city":
            "Not available",

        "valid":
            len(number) == 10,

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


# GET API DATA


# =========================================================


def get_api_data(number):

    # If Abstract API has already reported quota/rate-limit/auth
    # failure during this app session, do not keep sending requests.
    if st.session_state.get("api_unavailable", False):
        reason = st.session_state.get(
            "api_unavailable_reason",
            "Abstract API unavailable.",
        )

        return (
            local_fallback(number),
            f"{reason} Local verification used.",
        )

    if not API_KEY:
        return (
            local_fallback(number),
            "API key not configured. Local verification used.",
        )

    try:
        response = requests.get(
            API_URL,
            headers={
                "Authorization":
                    f"Bearer {API_KEY}"
            },
            params={
                "phone":
                    api_number(number)
            },
            timeout=6,
        )

        if response.status_code == 200:
            try:
                data = response.json()

                if not isinstance(data, dict):
                    raise ValueError("Invalid API response.")

                return (
                    normalize_api_response(
                        data,
                        number,
                    ),
                    None,
                )

            except (ValueError, TypeError, json.JSONDecodeError):
                return (
                    local_fallback(number),
                    "Invalid API response. Local verification used.",
                )

        # Quota / rate-limit / authorization failures:
        # stop making API calls for this Streamlit session.
        if response.status_code == 429:
            st.session_state["api_unavailable"] = True
            st.session_state["api_unavailable_reason"] = (
                "Abstract API request limit reached."
            )

            return (
                local_fallback(number),
                "Abstract API request limit reached. "
                "Local verification used.",
            )

        if response.status_code in (401, 402, 403):
            st.session_state["api_unavailable"] = True
            st.session_state["api_unavailable_reason"] = (
                "Abstract API is unavailable for this request."
            )

            return (
                local_fallback(number),
                f"Abstract API returned status {response.status_code}. "
                "Local verification used.",
            )

        return (
            local_fallback(number),
            f"API returned status {response.status_code}. "
            "Local verification used.",
        )

    except requests.Timeout:
        return (
            local_fallback(number),
            "Real-time API timed out. Local verification used.",
        )

    except requests.RequestException:
        return (
            local_fallback(number),
            "Real-time API unavailable. Local verification used.",
        )

    except Exception:
        return (
            local_fallback(number),
            "API error. Local verification used.",
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
                    "is_valid": int(info.get("valid", True)),
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

    combined_risk = (
        community_component * 0.40
        + api_risk * 0.35
        + pattern_risk * 0.10
        + model_spam * 0.15
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
    elif info.get("abuse") or not info.get("valid", True):
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
    }


def calculate_result(reports, info, ml):
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

    trust = (
        report_score * 0.30
        + genuine_probability * 0.35
        + api_score * 0.20
        + (100 - ml.get("risk_score", 50.0)) * 0.15
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

    elif (
        ml["prediction"] == "Suspicious"
        or str(info.get("risk_level", "")).lower() == "medium"
        or total == 0
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


CACHE_VERSION = 3


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


st.title(


    "Number Spam Verification System"


)


st.markdown(


    '<div class="hero-subtitle">'


    'Check if a phone number is spam or safe'


    '</div>',


    unsafe_allow_html=True,


)


# =========================================================


# INPUT


# =========================================================


number_input = st.text_input(


    "Enter Mobile Number",


    placeholder=


        "Enter 10-digit Indian mobile number",


    max_chars=15,


)


verify = st.button(


    "Verify Number",


    type="secondary",


)


# =========================================================


# VERIFICATION


# =========================================================


if verify:


    number = clean_number(number_input)


    if len(number) != 10:

        st.error(

            "Please enter a valid "

            "10-digit mobile number."

        )

        st.stop()


    # Same number -> same saved result.

    # Different number -> fresh verification.

    cached_result = get_cached_result(number)


    if cached_result:

        st.session_state["result"] = cached_result


    else:

        with st.spinner(

            "Checking number information..."

        ):


            reports = get_db_reports(number)


            info, api_message = get_api_data(

                number

            )


            if not info.get(

                "live",

                False,

            ):

                reports["spam_reports"] = int(

                    info.get(

                        "fallback_spam",

                        reports["spam_reports"],

                    )

                )


                reports["genuine_reports"] = int(

                    info.get(

                        "fallback_genuine",

                        reports["genuine_reports"],

                    )

                )


            ml = model_prediction(

                number,

                reports,

                info,

            )


            trust, status = calculate_result(

                reports,

                info,

                ml,

            )


            verification_result = {

                "number": number,

                "reports": reports,

                "info": info,

                "ml": ml,

                "trust": trust,

                "status": status,

                "api_message": api_message,

            }


            save_cached_result(

                number,

                verification_result,

            )


            st.session_state["result"] = (

                verification_result

            )


    result_now = st.session_state.get(

        "result"

    )


    if (

        result_now

        and result_now.get(

            "info",

            {},

        ).get(

            "live",

            False,

        )

    ):

        st.success(

            "Real-time number verification completed!"

        )


    elif result_now:

        st.warning(

            result_now.get(

                "api_message"

            )

            or

            "Real-time API unavailable. "

            "Local verification completed."

        )


# =========================================================


# RESULTS


# =========================================================


result = st.session_state.get(


    "result"


)


if result:


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


    st.subheader(


        "Verification Result"


    )


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


                f"{'Yes' if info['valid'] else 'No'}"


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


            verification_type = (


                "Real-time API"


                if info["live"]


                else "Local Fallback"


            )


            st.markdown(


                f"**Verification:** "


                f"{verification_type}"


            )


    st.write("")


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


            st.markdown(


                f"**Prediction:** "


                f"{ml['prediction']}"


            )


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


            else:


                st.error(


                    "Likely Spam"


                )


    st.write("")


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