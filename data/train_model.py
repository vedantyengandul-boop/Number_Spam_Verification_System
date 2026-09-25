import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


# ==========================================
# 1. LOAD DATASET
# ==========================================

file_path = "data/dataset/spam_dataset.csv"

df = pd.read_csv(file_path)

print("==========================================")
print("DATASET LOADED")
print("==========================================")

print("Rows:", len(df))
print("Columns:", len(df.columns))


# ==========================================
# 2. CONVERT YES / NO VALUES
# ==========================================

yes_no_columns = [
    "abuse_detected",
    "disposable_number",
    "is_valid"
]

for column in yes_no_columns:
    df[column] = df[column].map({
        "Yes": 1,
        "No": 0
    })


# ==========================================
# 3. CONVERT RISK LEVEL
# ==========================================

risk_mapping = {
    "low": 0,
    "medium": 1,
    "high": 2
}

df["risk_level"] = df["risk_level"].map(risk_mapping)


# ==========================================
# 4. CONVERT STATUS / TARGET
# ==========================================

status_mapping = {
    "Genuine": 0,
    "Suspicious": 1,
    "Spam": 2
}

df["status"] = df["status"].map(status_mapping)


# ==========================================
# 5. SELECT FEATURES
# ==========================================

features = [
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

X = df[features]
y = df["status"]


# ==========================================
# 6. TRAIN / TEST SPLIT
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


print("\n==========================================")
print("TRAIN / TEST SPLIT")
print("==========================================")

print("Training records:", len(X_train))
print("Testing records:", len(X_test))


# ==========================================
# 7. CREATE RANDOM FOREST MODEL
# ==========================================

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    class_weight="balanced"
)


# ==========================================
# 8. TRAIN MODEL
# ==========================================

model.fit(X_train, y_train)


# ==========================================
# 9. PREDICTION
# ==========================================

y_pred = model.predict(X_test)


# ==========================================
# 10. MODEL ACCURACY
# ==========================================

accuracy = accuracy_score(y_test, y_pred)

print("\n==========================================")
print("MODEL RESULTS")
print("==========================================")

print(f"Accuracy: {accuracy * 100:.2f}%")


# ==========================================
# 11. CLASSIFICATION REPORT
# ==========================================

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        y_pred,
        target_names=[
            "Genuine",
            "Suspicious",
            "Spam"
        ],
        zero_division=0
    )
)


# ==========================================
# 12. CONFUSION MATRIX
# ==========================================

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        y_pred
    )
)


# ==========================================
# 13. SAVE MODEL
# ==========================================

model_path = "data/models/spam_model.pkl"

joblib.dump(model, model_path)

print("\n==========================================")
print("MODEL SAVED SUCCESSFULLY!")
print("==========================================")

print("Model location:", model_path)