
import os
import joblib
import pandas as pd

from sklearn.ensemble import (
    IsolationForest,
    RandomForestClassifier,
    RandomForestRegressor
)

from sklearn.preprocessing import LabelEncoder

from sklearn.model_selection import (
    train_test_split
)

from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error
)


# ============================================================
# AEROSYNX AI / ML MODEL TRAINING
# ============================================================


# ============================================================
# PATHS
# ============================================================

DATA_FILE = (
    "data/engine_data.csv"
)

MODEL_DIR = "models"

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


# ============================================================
# FEATURES
#
# IMPORTANT:
# This order MUST remain exactly the same during prediction.
#
# Hardware/API values and simulated fallback values will
# eventually be converted into these same features.
# ============================================================

FEATURES = [

    "rpm",

    "cht_c",

    "egt_c",

    "oil_press_bar",

    "oil_temp_c",

    "fuel_flow_lph",

    "vibration_g",

    "battery_v",

    "injection_deg",

    "cht_residual",

    "egt_residual",

    "oil_pressure_residual",

    "vibration_residual"
]


# ============================================================
# EXPECTED FAULT CLASSES
# ============================================================

EXPECTED_FAULTS = [

    "healthy",

    "misfire",

    "injector_abnormality",

    "coking_degradation",

    "lubrication_issue",

    "sensor_drift",

    "combustion_instability",

    "overheating",

    "abnormal_vibration",

    "battery_alternator_health",

    "injection_timing_issue"
]


# ============================================================
# LOAD DATASET
# ============================================================

if not os.path.exists(
    DATA_FILE
):

    raise FileNotFoundError(

        f"Dataset not found: {DATA_FILE}\n"

        "Run generate_data.py first."
    )


df = pd.read_csv(
    DATA_FILE
)


# ============================================================
# START INFORMATION
# ============================================================

print()

print("=" * 70)

print(
    "AEROSYNX AI / ML MODEL TRAINING"
)

print("=" * 70)

print()

print(
    f"Dataset size : {len(df)}"
)

print(
    f"Features     : {len(FEATURES)}"
)

print(
    f"Fault classes: {df['fault'].nunique()}"
)

print()


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = (

    FEATURES
    +
    [
        "fault",
        "rul"
    ]
)


missing_columns = [

    column

    for column in required_columns

    if column not in df.columns
]


if missing_columns:

    raise ValueError(

        "Missing columns in dataset:\n"

        +
        "\n".join(
            missing_columns
        )
    )


# ============================================================
# CHECK FAULT CLASSES
# ============================================================

dataset_faults = sorted(
    df["fault"].unique()
)

expected_faults = sorted(
    EXPECTED_FAULTS
)


print(
    "Fault classes found in dataset:"
)

for fault in dataset_faults:

    count = (
        df["fault"] == fault
    ).sum()

    print(
        f"  {fault:<30} "
        f"{count} samples"
    )

print()


# Check whether any expected
# fault class is missing.

missing_faults = [

    fault

    for fault in EXPECTED_FAULTS

    if fault not in dataset_faults
]


if missing_faults:

    raise ValueError(

        "The following expected fault "
        "classes are missing from the dataset:\n"

        +
        "\n".join(
            missing_faults
        )

        +

        "\n\nRun generate_data.py again."
    )


# ============================================================
# INPUT / OUTPUT DATA
# ============================================================

X = df[
    FEATURES
]

y_fault = df[
    "fault"
]

y_rul = df[
    "rul"
]


# ============================================================
# 1. ANOMALY DETECTION
# ============================================================

print()

print(
    "=" * 70
)

print(
    "1. TRAINING ANOMALY DETECTION MODEL"
)

print(
    "=" * 70
)

print()


# ------------------------------------------------------------
# Only healthy data is used to teach the model what normal
# engine behaviour looks like.
# ------------------------------------------------------------

healthy_data = df[
    df["fault"] == "healthy"
]


if len(healthy_data) == 0:

    raise ValueError(
        "No healthy samples found in dataset."
    )


X_healthy = healthy_data[
    FEATURES
]


print(
    f"Healthy training samples: "
    f"{len(X_healthy)}"
)


# ------------------------------------------------------------
# Isolation Forest
# ------------------------------------------------------------

anomaly_model = IsolationForest(

    n_estimators=200,

    contamination=0.08,

    random_state=42,

    n_jobs=-1
)


anomaly_model.fit(
    X_healthy
)


# ------------------------------------------------------------
# Save anomaly model
# ------------------------------------------------------------

anomaly_model_path = os.path.join(

    MODEL_DIR,

    "anomaly_model.pkl"
)


joblib.dump(

    anomaly_model,

    anomaly_model_path
)


print()

print(
    "Anomaly model saved:"
)

print(
    anomaly_model_path
)


# ============================================================
# 2. FAULT CLASSIFICATION
# ============================================================

print()

print(
    "=" * 70
)

print(
    "2. TRAINING FAULT CLASSIFICATION MODEL"
)

print(
    "=" * 70
)

print()


# ------------------------------------------------------------
# Encode fault labels
# ------------------------------------------------------------

fault_encoder = LabelEncoder()


y_encoded = (
    fault_encoder.fit_transform(
        y_fault
    )
)


print(
    "Fault classes used by model:"
)

for index, fault in enumerate(
    fault_encoder.classes_
):

    print(
        f"  {index:<3} {fault}"
    )

print()


# ------------------------------------------------------------
# Train/test split
# ------------------------------------------------------------

X_train, X_test, y_train, y_test = (

    train_test_split(

        X,

        y_encoded,

        test_size=0.20,

        random_state=42,

        stratify=y_encoded
    )
)


print(
    f"Training samples: "
    f"{len(X_train)}"
)

print(
    f"Testing samples : "
    f"{len(X_test)}"
)

print()


# ------------------------------------------------------------
# Random Forest Classifier
# ------------------------------------------------------------

fault_model = RandomForestClassifier(

    n_estimators=300,

    max_depth=18,

    min_samples_leaf=2,

    random_state=42,

    n_jobs=-1,

    class_weight="balanced"
)


fault_model.fit(

    X_train,

    y_train
)


# ------------------------------------------------------------
# Test classifier
# ------------------------------------------------------------

predictions = fault_model.predict(
    X_test
)


accuracy = accuracy_score(

    y_test,

    predictions
)


print(
    f"Fault model accuracy: "
    f"{accuracy * 100:.2f}%"
)


# ------------------------------------------------------------
# Save classifier
# ------------------------------------------------------------

fault_model_path = os.path.join(

    MODEL_DIR,

    "fault_model.pkl"
)


joblib.dump(

    fault_model,

    fault_model_path
)


print()

print(
    "Fault model saved:"
)

print(
    fault_model_path
)


# ------------------------------------------------------------
# Save label encoder
# ------------------------------------------------------------

fault_encoder_path = os.path.join(

    MODEL_DIR,

    "fault_encoder.pkl"
)


joblib.dump(

    fault_encoder,

    fault_encoder_path
)


print(
    "Fault encoder saved:"
)

print(
    fault_encoder_path
)


# ============================================================
# 3. RUL REGRESSION
# ============================================================

print()

print(
    "=" * 70
)

print(
    "3. TRAINING REMAINING USEFUL LIFE MODEL"
)

print(
    "=" * 70
)

print()


# ------------------------------------------------------------
# Train/test split for RUL
# ------------------------------------------------------------

X_train_rul, X_test_rul, y_train_rul, y_test_rul = (

    train_test_split(

        X,

        y_rul,

        test_size=0.20,

        random_state=42
    )
)


print(
    f"RUL training samples: "
    f"{len(X_train_rul)}"
)

print(
    f"RUL testing samples : "
    f"{len(X_test_rul)}"
)

print()


# ------------------------------------------------------------
# Random Forest Regressor
# ------------------------------------------------------------

rul_model = RandomForestRegressor(

    n_estimators=300,

    max_depth=18,

    min_samples_leaf=2,

    random_state=42,

    n_jobs=-1
)


rul_model.fit(

    X_train_rul,

    y_train_rul
)


# ------------------------------------------------------------
# Test RUL model
# ------------------------------------------------------------

rul_predictions = (

    rul_model.predict(

        X_test_rul
    )
)


mae = mean_absolute_error(

    y_test_rul,

    rul_predictions
)


print(
    f"RUL MAE: "
    f"{mae:.2f} hours"
)


# ------------------------------------------------------------
# Save RUL model
# ------------------------------------------------------------

rul_model_path = os.path.join(

    MODEL_DIR,

    "rul_model.pkl"
)


joblib.dump(

    rul_model,

    rul_model_path
)


print()

print(
    "RUL model saved:"
)

print(
    rul_model_path
)


# ============================================================
# SAVE FEATURE ORDER
# ============================================================

features_path = os.path.join(

    MODEL_DIR,

    "features.pkl"
)


joblib.dump(

    FEATURES,

    features_path
)


print()

print(
    "Feature order saved:"
)

print(
    features_path
)


# ============================================================
# SAVE MODEL INFORMATION
# ============================================================

model_info = {

    "model_name":
        "AeroSynX Engine Health AI",

    "version":
        "2.0",

    "feature_count":
        len(FEATURES),

    "features":
        FEATURES,

    "anomaly_model":
        "IsolationForest",

    "fault_model":
        "RandomForestClassifier",

    "rul_model":
        "RandomForestRegressor",

    "fault_classes":
        list(
            fault_encoder.classes_
        ),

    "fault_count":
        len(
            fault_encoder.classes_
        ),

    "fault_accuracy":
        float(
            accuracy
        ),

    "rul_mae_hours":
        float(
            mae
        ),

    "training_samples":
        int(
            len(df)
        ),

    "healthy_samples":
        int(
            len(healthy_data)
        )
}


model_info_path = os.path.join(

    MODEL_DIR,

    "model_info.pkl"
)


joblib.dump(

    model_info,

    model_info_path
)


print()

print(
    "Model information saved:"
)

print(
    model_info_path
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()

print("=" * 70)

print(
    "ALL AEROSYNX AI / ML MODELS SAVED"
)

print("=" * 70)

print()

print(
    "Models directory:"
)

print(
    "├── anomaly_model.pkl"
)

print(
    "├── fault_model.pkl"
)

print(
    "├── fault_encoder.pkl"
)

print(
    "├── rul_model.pkl"
)

print(
    "├── features.pkl"
)

print(
    "└── model_info.pkl"
)

print()

print(
    "Fault classes trained:"
)

for fault in fault_encoder.classes_:

    print(
        f"  ✓ {fault}"
    )

print()

print(
    f"Fault classification accuracy: "
    f"{accuracy * 100:.2f}%"
)

print(
    f"RUL prediction MAE: "
    f"{mae:.2f} hours"
)

print()

print(
    "AEROSYNX AI / ML TRAINING COMPLETED."
)

print()

