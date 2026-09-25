import streamlit as st
import sqlite3
import requests
import os
import joblib
import pandas as pd

from dotenv import load_dotenv


# =========================================
# LOAD API KEY
# =========================================

load_dotenv()

API_KEY = os.getenv("ABSTRACT_API_KEY")


# =========================================
# LOAD MACHINE LEARNING MODEL
# =========================================

MODEL_PATH = "data/models/spam_model.pkl"

try:
    ml_model = joblib.load(MODEL_PATH)
    MODEL_LOADED = True
except Exception:
    ml_model = None
    MODEL_LOADED = False


# =========================================
# PAGE CONFIGURATION
# =========================================

st.set_page_config(
    page_title="Number Spam Verification System",
    page_icon="📞",
    layout="wide"
)


# =========================================
# CUSTOM CSS
# =========================================

st.markdown(
    """
    <style>

    .main {
        padding-top: 1rem;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .section-title {
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 14px;
    }

    .field {
        margin-bottom: 13px;
    }

    .field-label {
        font-size: 12px;
        color: #8b8b8b;
        margin-bottom: 3px;
    }

    .field-value {
        font-size: 15px;
        font-weight: 500;
    }

    .trust-score {
        font-size: 34px;
        font-weight: 600;
        margin-top: 2px;
    }

    .ml-probability {
        font-size: 14px;
        margin-top: 5px;
    }

    .small-note {
        font-size: 12px;
        color: #8b8b8b;
        margin-top: 3px;
    }

    .result-heading {
        margin-top: 18px;
        margin-bottom: 8px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================
# PAGE TITLE
# =========================================

st.title("Number Spam Verification System")

st.write(
    "Enter a mobile number to check its current verification status."
)


# =========================================
# REAL-TIME PHONE INFORMATION FUNCTION
# =========================================

def get_phone_information(phone_number):

    url = "https://phoneintelligence.abstractapi.com/v1"

    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    params = {
        "phone": phone_number
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code == 200:
            return response.json()

        return None

    except requests.RequestException:
        return None


# =========================================
# MACHINE LEARNING PREDICTION FUNCTION
# =========================================

def get_ml_prediction(
    cleaned_number,
    spam_reports,
    genuine_reports,
    risk_level,
    abuse_detected,
    disposable,
    is_valid
):

    if not MODEL_LOADED:
        return None, None, None

    try:

        # -------------------------------------
        # Number features
        # -------------------------------------

        number_digits = "".join(
            character for character in cleaned_number
            if character.isdigit()
        )

        number_length = len(number_digits)

        starts_with_plus = (
            1 if cleaned_number.startswith("+") else 0
        )

        if len(number_digits) >= 3:
            digit_pattern_1 = int(number_digits[:3])
        else:
            digit_pattern_1 = 0

        if len(number_digits) >= 5:
            digit_pattern_2 = int(number_digits[3:5])
        else:
            digit_pattern_2 = 0


        # -------------------------------------
        # Report features
        # -------------------------------------

        total_reports = spam_reports + genuine_reports

        if total_reports > 0:
            spam_ratio = spam_reports / total_reports
        else:
            spam_ratio = 0


        # -------------------------------------
        # Risk encoding
        #
        # Same logical mapping used for the
        # training dataset:
        #
        # low    = 0
        # medium = 1
        # high   = 2
        # -------------------------------------

        risk_mapping = {
            "low": 0,
            "medium": 1,
            "high": 2
        }

        risk_encoded = risk_mapping.get(
            str(risk_level).lower(),
            0
        )


        # -------------------------------------
        # Boolean values
        # -------------------------------------

        abuse_encoded = 1 if abuse_detected else 0

        disposable_encoded = 1 if disposable else 0

        valid_encoded = 1 if is_valid else 0


        # -------------------------------------
        # CREATE ML INPUT
        # -------------------------------------

        features = pd.DataFrame(
            [[
                number_length,
                starts_with_plus,
                digit_pattern_1,
                digit_pattern_2,
                spam_reports,
                genuine_reports,
                total_reports,
                spam_ratio,
                risk_encoded,
                abuse_encoded,
                disposable_encoded,
                valid_encoded
            ]],
            columns=[
                "length",
                "starts_with_plus",
                "digit_pattern_1",
                "digit_pattern_2",
                "spam_reports",
                "genuine_reports",
                "total_reports",
                "spam_ratio",
                "risk_level",
                "abuse_detected",
                "disposable_number",
                "is_valid"
            ]
        )


        # -------------------------------------
        # PREDICTION
        # -------------------------------------

        prediction = ml_model.predict(features)[0]

        probabilities = ml_model.predict_proba(features)[0]


        # -------------------------------------
        # STATUS MAPPING
        # -------------------------------------

        status_mapping = {
            0: "Genuine",
            1: "Suspicious",
            2: "Spam"
        }

        predicted_status = status_mapping.get(
            int(prediction),
            "Unknown"
        )


        # -------------------------------------
        # PROBABILITY VALUES
        # -------------------------------------

        model_classes = list(
            ml_model.classes_
        )

        probability_dict = {}

        for index, model_class in enumerate(model_classes):

            class_name = status_mapping.get(
                int(model_class),
                "Unknown"
            )

            probability_dict[class_name] = (
                float(probabilities[index]) * 100
            )


        genuine_probability = probability_dict.get(
            "Genuine",
            0
        )

        suspicious_probability = probability_dict.get(
            "Suspicious",
            0
        )

        spam_probability = probability_dict.get(
            "Spam",
            0
        )


        return (
            predicted_status,
            genuine_probability,
            suspicious_probability,
            spam_probability
        )

    except Exception as error:

        return (
            "ML Error",
            0,
            0,
            0
        )


# =========================================
# MOBILE NUMBER INPUT
# =========================================

mobile_number = st.text_input(
    "Enter Mobile Number",
    placeholder="Example: 9876543210"
)


# =========================================
# VERIFY BUTTON
# =========================================

if st.button("Verify Number"):

    # =====================================
    # EMPTY NUMBER
    # =====================================

    if mobile_number.strip() == "":

        st.warning(
            "Please enter a mobile number."
        )

    else:

        # =================================
        # CLEAN NUMBER
        # =================================

        cleaned_number = (
            mobile_number
            .replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )


        # =================================
        # INDIAN NUMBER FORMAT
        # =================================

        if (
            cleaned_number.isdigit()
            and
            len(cleaned_number) == 10
        ):

            api_number = "+91" + cleaned_number
            database_number = cleaned_number


        elif cleaned_number.startswith("+91"):

            digits_only = cleaned_number[3:]

            if (
                digits_only.isdigit()
                and
                len(digits_only) >= 10
            ):

                api_number = cleaned_number
                database_number = digits_only[-10:]

            else:

                api_number = cleaned_number
                database_number = None


        else:

            api_number = cleaned_number
            database_number = None


        # =================================
        # CHECK API KEY
        # =================================

        if not API_KEY:

            st.error(
                "API key not found. Please check the .env file."
            )

        else:

            # =================================
            # REAL-TIME API REQUEST
            # =================================

            with st.spinner(
                "Checking real-time number information..."
            ):

                api_data = get_phone_information(
                    api_number
                )


            # =================================
            # API DATA RECEIVED
            # =================================

            if api_data:

                # =================================
                # EXTRACT API SECTIONS
                # =================================

                validation = api_data.get(
                    "phone_validation",
                    {}
                )

                carrier = api_data.get(
                    "phone_carrier",
                    {}
                )

                location = api_data.get(
                    "phone_location",
                    {}
                )

                risk = api_data.get(
                    "phone_risk",
                    {}
                )

                phone_format = api_data.get(
                    "phone_format",
                    {}
                )


                # =================================
                # VALIDATION INFORMATION
                # =================================

                is_valid = validation.get(
                    "is_valid",
                    False
                )

                line_status = validation.get(
                    "line_status",
                    "Unknown"
                )


                # =================================
                # CARRIER INFORMATION
                # =================================

                carrier_name = carrier.get(
                    "name",
                    "Not available"
                )

                line_type = carrier.get(
                    "line_type",
                    "Unknown"
                )


                # =================================
                # LOCATION INFORMATION
                # =================================

                country = location.get(
                    "country_name",
                    "Not available"
                )

                region = location.get(
                    "region",
                    "Not available"
                )

                city = location.get(
                    "city",
                    "Not available"
                )


                # =================================
                # RISK INFORMATION
                # =================================

                risk_level = risk.get(
                    "risk_level",
                    "Unknown"
                )

                abuse_detected = risk.get(
                    "is_abuse_detected",
                    False
                )

                disposable = risk.get(
                    "is_disposable",
                    False
                )


                # =================================
                # CLEAN EMPTY API VALUES
                # =================================

                if region is None or str(region).strip() == "":
                    region = "Not available"

                if city is None or str(city).strip() == "":
                    city = "Not available"

                if carrier_name is None or str(carrier_name).strip() == "":
                    carrier_name = "Not available"

                if line_type is None or str(line_type).strip() == "":
                    line_type = "Unknown"

                if country is None or str(country).strip() == "":
                    country = "Not available"

                if risk_level is None or str(risk_level).strip() == "":
                    risk_level = "Unknown"


                # =================================
                # INVALID NUMBER
                # =================================

                if not is_valid:

                    st.error(
                        "This mobile number appears to be invalid."
                    )

                else:

                    # =================================
                    # DATABASE INFORMATION
                    # =================================

                    spam_reports = 0
                    genuine_reports = 0


                    connection = sqlite3.connect(
                        "data/database/spam_database.db"
                    )

                    cursor = connection.cursor()


                    if database_number:

                        cursor.execute(
                            """
                            SELECT spam_reports, genuine_reports
                            FROM spam_numbers
                            WHERE mobile_number = ?
                            """,
                            (database_number,)
                        )

                        result = cursor.fetchone()

                        if result:

                            spam_reports = result[0]
                            genuine_reports = result[1]


                    connection.close()


                    # =================================
                    # REPORT SCORE
                    # =================================

                    total_reports = (
                        spam_reports +
                        genuine_reports
                    )


                    if total_reports > 0:

                        report_score = (
                            genuine_reports /
                            total_reports
                        ) * 100

                    else:

                        report_score = 50


                    # =================================
                    # API RISK SCORE
                    # =================================

                    if risk_level.lower() == "low":

                        api_score = 85

                    elif risk_level.lower() == "medium":

                        api_score = 55

                    elif risk_level.lower() == "high":

                        api_score = 25

                    else:

                        api_score = 50


                    # =================================
                    # ABUSE DETECTED
                    # =================================

                    if abuse_detected:

                        api_score -= 20


                    # =================================
                    # DISPOSABLE NUMBER
                    # =================================

                    if disposable:

                        api_score -= 10


                    # =================================
                    # SCORE LIMIT
                    # =================================

                    api_score = max(
                        0,
                        min(100, api_score)
                    )


                    # =================================
                    # MACHINE LEARNING PREDICTION
                    # =================================

                    (
                        ml_status,
                        genuine_probability,
                        suspicious_probability,
                        spam_probability
                    ) = get_ml_prediction(

                        cleaned_number,
                        spam_reports,
                        genuine_reports,
                        risk_level,
                        abuse_detected,
                        disposable,
                        is_valid
                    )


                    # =================================
                    # FINAL TRUST SCORE
                    # =================================

                    if ml_status not in [
                        None,
                        "ML Error"
                    ]:

                        # ML genuine probability is used
                        # as the main intelligent score.

                        ml_score = genuine_probability


                        if total_reports > 0:

                            trust_score = (
                                report_score * 0.30
                                +
                                ml_score * 0.50
                                +
                                api_score * 0.20
                            )

                        else:

                            trust_score = (
                                ml_score * 0.70
                                +
                                api_score * 0.30
                            )

                    else:

                        # Fallback if ML model has an issue.

                        if total_reports > 0:

                            trust_score = (
                                report_score * 0.60
                                +
                                api_score * 0.40
                            )

                        else:

                            trust_score = api_score


                    # =================================
                    # SCORE LIMIT
                    # =================================

                    trust_score = round(
                        max(
                            0,
                            min(100, trust_score)
                        ),
                        2
                    )


                    # =================================
                    # FINAL STATUS
                    # =================================

                    if abuse_detected:

                        status = "Likely Spam"

                    elif ml_status == "Spam":

                        status = "Likely Spam"

                    elif ml_status == "Suspicious":

                        status = "Suspicious"

                    elif trust_score < 40:

                        status = "Likely Spam"

                    elif trust_score < 70:

                        status = "Suspicious"

                    else:

                        status = "Likely Genuine"


                    # =================================
                    # VERIFICATION COMPLETED
                    # =================================

                    st.success(
                        "Real-time number verification completed!"
                    )


                    st.markdown(
                        '<div class="result-heading">'
                        '<h2>Verification Result</h2>'
                        '</div>',
                        unsafe_allow_html=True
                    )


                    # ==================================================
                    # TOP THREE SECTIONS
                    # ==================================================

                    info_col, report_col, risk_col = st.columns(3)


                    # ==================================================
                    # 📞 INFORMATION
                    # ==================================================

                    with info_col:

                        with st.container(border=True):

                            st.markdown(
                                '<div class="section-title">'
                                '📞 Information'
                                '</div>',
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Mobile Number
                                    </div>
                                    <div class="field-value">
                                        {phone_format.get(
                                            "international",
                                            api_number
                                        )}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Carrier
                                    </div>
                                    <div class="field-value">
                                        {carrier_name}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Line Type
                                    </div>
                                    <div class="field-value">
                                        {line_type}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Country
                                    </div>
                                    <div class="field-value">
                                        {country}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Valid
                                    </div>
                                    <div class="field-value">
                                        {"Yes" if is_valid else "No"}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Line Status
                                    </div>
                                    <div class="field-value">
                                        {line_status}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Region
                                    </div>
                                    <div class="field-value">
                                        {region}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        City
                                    </div>
                                    <div class="field-value">
                                        {city}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                    # ==================================================
                    # 📊 SPAM REPORTS
                    # ==================================================

                    with report_col:

                        with st.container(border=True):

                            st.markdown(
                                '<div class="section-title">'
                                '📊 Spam Reports'
                                '</div>',
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Spam Reports
                                    </div>
                                    <div class="field-value">
                                        {spam_reports}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Genuine Reports
                                    </div>
                                    <div class="field-value">
                                        {genuine_reports}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Total Reports
                                    </div>
                                    <div class="field-value">
                                        {total_reports}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            if total_reports > 0:

                                spam_ratio = (
                                    spam_reports /
                                    total_reports
                                ) * 100

                                spam_ratio = round(
                                    spam_ratio,
                                    2
                                )


                                st.markdown(
                                    f"""
                                    <div class="field">
                                        <div class="field-label">
                                            Spam Report Ratio
                                        </div>
                                        <div class="field-value">
                                            {spam_ratio}%
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                            else:

                                st.markdown(
                                    """
                                    <div class="small-note">
                                        No community reports are currently
                                        available for this number.
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )


                    # ==================================================
                    # 🛡️ RISK ANALYSIS
                    # ==================================================

                    with risk_col:

                        with st.container(border=True):

                            st.markdown(
                                '<div class="section-title">'
                                '🛡️ Risk Analysis'
                                '</div>',
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Risk Level
                                    </div>
                                    <div class="field-value">
                                        {str(risk_level).title()}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Abuse Detected
                                    </div>
                                    <div class="field-value">
                                        {"Yes" if abuse_detected else "No"}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                f"""
                                <div class="field">
                                    <div class="field-label">
                                        Disposable
                                    </div>
                                    <div class="field-value">
                                        {"Yes" if disposable else "No"}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                """
                                <div class="field">
                                    <div class="field-label">
                                        Real-time Verification
                                    </div>
                                    <div class="field-value">
                                        Completed
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                    # ==================================================
                    # BOTTOM TWO SECTIONS
                    # ==================================================

                    ml_col, final_col = st.columns(2)


                    # ==================================================
                    # 🤖 MACHINE LEARNING ANALYSIS
                    # ==================================================

                    with ml_col:

                        with st.container(border=True):

                            st.markdown(
                                '<div class="section-title">'
                                '🤖 Machine Learning Analysis'
                                '</div>',
                                unsafe_allow_html=True
                            )


                            ml_inner_col1, ml_inner_col2 = st.columns(2)


                            with ml_inner_col1:

                                st.markdown(
                                    f"""
                                    <div class="field">
                                        <div class="field-label">
                                            Model Status
                                        </div>
                                        <div class="field-value">
                                            {
                                                "Active"
                                                if MODEL_LOADED
                                                else
                                                "Unavailable"
                                            }
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )


                            with ml_inner_col2:

                                st.markdown(
                                    f"""
                                    <div class="field">
                                        <div class="field-label">
                                            Prediction
                                        </div>
                                        <div class="field-value">
                                            {ml_status}
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )


                            st.markdown(
                                f"""
                                <div class="ml-probability">
                                    <b>Genuine:</b>
                                    {genuine_probability:.2f}%
                                </div>

                                <div class="ml-probability">
                                    <b>Suspicious:</b>
                                    {suspicious_probability:.2f}%
                                </div>

                                <div class="ml-probability">
                                    <b>Spam:</b>
                                    {spam_probability:.2f}%
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                            st.markdown(
                                """
                                <div class="small-note">
                                    The Machine Learning model analyzes
                                    number characteristics, community reports,
                                    and risk-related features to generate
                                    a classification.
                                </div>
                                """,
                                unsafe_allow_html=True
                            )


                    # ==================================================
                    # 🎯 FINAL VERIFICATION
                    # ==================================================

                    with final_col:

                        with st.container(border=True):

                            st.markdown(
                                '<div class="section-title">'
                                '🎯 Final Verification'
                                '</div>',
                                unsafe_allow_html=True
                            )


                            final_inner_col1, final_inner_col2 = st.columns(2)


                            with final_inner_col1:

                                st.markdown(
                                    """
                                    <div class="field">
                                        <div class="field-label">
                                            Trust Score
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )


                                st.markdown(
                                    f"""
                                    <div class="trust-score">
                                        {trust_score}%
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )


                            with final_inner_col2:

                                st.markdown(
                                    """
                                    <div class="field">
                                        <div class="field-label">
                                            Final Status
                                        </div>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )


                                if status == "Likely Genuine":

                                    st.success(status)

                                elif status == "Suspicious":

                                    st.warning(status)

                                else:

                                    st.error(status)


                    # ==================================================
                    # 📝 SPAM APPEAL
                    # ==================================================

                    with st.container(border=True):

                        st.markdown(
                            '<div class="section-title">'
                            '📝 Spam Appeal'
                            '</div>',
                            unsafe_allow_html=True
                        )


                        st.write(
                            "If you believe this number has been "
                            "wrongly marked as spam, you can submit "
                            "an appeal for verification."
                        )


                        if st.button(
                            "This Number Is Not Spam"
                        ):

                            st.success(
                                "Appeal request submitted successfully."
                            )


            # =========================================
            # API FAILURE
            # =========================================

            else:

                st.error(
                    "Unable to retrieve real-time information. "
                    "The API may be temporarily unavailable or "
                    "the free API quota may have been exhausted."
                )