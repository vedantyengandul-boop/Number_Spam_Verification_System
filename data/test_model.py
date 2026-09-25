import joblib
import pandas as pd


# ==========================================
# LOAD TRAINED MODEL
# ==========================================

model_path = "data/models/spam_model.pkl"

model = joblib.load(model_path)

print("==========================================")
print("ML MODEL LOADED SUCCESSFULLY")
print("==========================================")


# ==========================================
# SAMPLE NUMBER DATA
# ==========================================

sample_data = pd.DataFrame([{
    "length": 10,
    "starts_with_plus": 0,
    "digit_pattern_1": 987,
    "digit_pattern_2": 65,
    "spam_reports": 2,
    "genuine_reports": 8,
    "total_reports": 10,
    "spam_ratio": 0.20,
    "risk_level": 0,
    "abuse_detected": 0,
    "disposable_number": 0,
    "is_valid": 1
}])


# ==========================================
# PREDICTION
# ==========================================

prediction = model.predict(sample_data)[0]

probabilities = model.predict_proba(sample_data)[0]


# ==========================================
# CONVERT PREDICTION TO STATUS
# ==========================================

status_mapping = {
    0: "Genuine",
    1: "Suspicious",
    2: "Spam"
}

predicted_status = status_mapping[prediction]


# ==========================================
# DISPLAY RESULT
# ==========================================

print("\n==========================================")
print("ML PREDICTION")
print("==========================================")

print("Predicted Status:", predicted_status)

print("\nPrediction Probabilities:")

print("Genuine     :", f"{probabilities[0] * 100:.2f}%")
print("Suspicious  :", f"{probabilities[1] * 100:.2f}%")
print("Spam        :", f"{probabilities[2] * 100:.2f}%")


print("\n==========================================")
print("TEST COMPLETED")
print("==========================================")