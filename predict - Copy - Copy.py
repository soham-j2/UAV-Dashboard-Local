import os
import joblib
import pandas as pd


# ============================================================
# PATHS
# ============================================================

MODEL_DIR = "models"


ANOMALY_MODEL = os.path.join(
    MODEL_DIR,
    "anomaly_model.pkl"
)

FAULT_MODEL = os.path.join(
    MODEL_DIR,
    "fault_model.pkl"
)

FAULT_ENCODER = os.path.join(
    MODEL_DIR,
    "fault_encoder.pkl"
)

RUL_MODEL = os.path.join(
    MODEL_DIR,
    "rul_model.pkl"
)

FEATURE_FILE = os.path.join(
    MODEL_DIR,
    "features.pkl"
)


# ============================================================
# LOAD MODELS
# ============================================================

anomaly_model = joblib.load(
    ANOMALY_MODEL
)

fault_model = joblib.load(
    FAULT_MODEL
)

fault_encoder = joblib.load(
    FAULT_ENCODER
)

rul_model = joblib.load(
    RUL_MODEL
)

FEATURES = joblib.load(
    FEATURE_FILE
)


# ============================================================
# ENGINEERING LIMITS
# ============================================================

NORMAL_RANGES = {

    "rpm": (4800, 5300),

    "cht_c": (95, 125),

    "egt_c": (620, 720),

    "oil_press_bar": (2.5, 4.2),

    "oil_temp_c": (85, 105),

    "fuel_flow_lph": (14, 18),

    "vibration_g": (0.05, 0.15),

    "battery_v": (13.8, 14.4),

    "injection_deg": (20, 25)
}


# ============================================================
# FAULT MAPPING
# ============================================================

FAULT_MAPPING = {

    "rpm": [
        "misfire",
        "combustion_instability"
    ],

    "cht_c": [
        "overheating",
        "coking_degradation"
    ],

    "egt_c": [
        "misfire",
        "combustion_instability",
        "overheating"
    ],

    "oil_press_bar": [
        "lubrication_issue"
    ],

    "oil_temp_c": [
        "lubrication_issue",
        "overheating"
    ],

    "fuel_flow_lph": [
        "injector_abnormality"
    ],

    "vibration_g": [
        "misfire",
        "abnormal_vibration",
        "combustion_instability"
    ],

    "battery_v": [
        "battery_alternator_health"
    ],

    "injection_deg": [
        "injector_abnormality",
        "injection_timing_issue"
    ]
}


# ============================================================
# ENGINEERING RANGE CHECK
# ============================================================

def engineering_check(data):

    violations = []

    possible_faults = []

    for field, limits in NORMAL_RANGES.items():

        if field not in data:

            continue

        value = data[field]

        minimum = limits[0]

        maximum = limits[1]


        if value < minimum or value > maximum:

            faults = FAULT_MAPPING.get(
                field,
                []
            )

            violations.append({

                "parameter":
                    field,

                "value":
                    value,

                "normal_min":
                    minimum,

                "normal_max":
                    maximum,

                "possible_faults":
                    faults
            })


            for fault in faults:

                if fault not in possible_faults:

                    possible_faults.append(
                        fault
                    )


    return (
        violations,
        possible_faults
    )


# ============================================================
# PREDICT ENGINE
# ============================================================

def predict_engine(
    ai_input,
    engineering_faults=None
):

    # --------------------------------------------------------
    # Create dataframe
    # --------------------------------------------------------

    values = {}

    for feature in FEATURES:

        values[feature] = [
            ai_input.get(
                feature,
                0
            )
        ]


    X = pd.DataFrame(
        values,
        columns=FEATURES
    )


    # ========================================================
    # 1. ANOMALY DETECTION
    # ========================================================

    anomaly_prediction = (
        anomaly_model.predict(X)[0]
    )

    anomaly_score = (
        anomaly_model.decision_function(X)[0]
    )


    if anomaly_prediction == -1:

        anomaly_status = (
            "ANOMALY DETECTED"
        )

    else:

        anomaly_status = (
            "NORMAL"
        )


    # ========================================================
    # 2. FAULT CLASSIFICATION
    # ========================================================

    encoded_fault = (
        fault_model.predict(X)[0]
    )

    predicted_fault = (
        fault_encoder.inverse_transform(
            [encoded_fault]
        )[0]
    )


    # ========================================================
    # FAULT CONFIDENCE
    # ========================================================

    probabilities = (
        fault_model.predict_proba(X)[0]
    )

    fault_confidence = (
        max(probabilities) * 100
    )


    # ========================================================
    # 3. RUL
    # ========================================================

    rul = (
        rul_model.predict(X)[0]
    )

    rul = max(
        0,
        float(rul)
    )


    # ========================================================
    # ENGINEERING FAULT OVERRIDE
    # ========================================================

    engineering_faults = (
        engineering_faults
        or []
    )


    # --------------------------------------------------------
    # If engineering range says abnormal,
    # don't blindly call engine healthy.
    # --------------------------------------------------------

    if engineering_faults:

        if predicted_fault == "healthy":

            predicted_fault = (
                engineering_faults[0]
            )

            fault_confidence = max(
                fault_confidence,
                75.0
            )


    # ========================================================
    # FINAL DECISION
    # ========================================================

    if engineering_faults:

        if rul < 100:

            decision = (
                "NOT RECOMMENDED"
            )

        else:

            decision = (
                "CAUTION"
            )


    elif anomaly_status == "ANOMALY DETECTED":

        if rul < 100:

            decision = (
                "NOT RECOMMENDED"
            )

        else:

            decision = (
                "CAUTION"
            )


    elif rul < 100:

        decision = (
            "NOT RECOMMENDED"
        )


    elif rul < 250:

        decision = (
            "CAUTION"
        )


    else:

        decision = (
            "SAFE"
        )


    # ========================================================
    # MAINTENANCE RECOMMENDATION
    # ========================================================

    if predicted_fault == "overheating":

        recommendation = (
            "Inspect cooling system and "
            "engine temperature."
        )

    elif predicted_fault == "coking_degradation":

        recommendation = (
            "Inspect combustion chamber "
            "and deposits."
        )

    elif predicted_fault == "lubrication_issue":

        recommendation = (
            "Check oil level, oil pressure "
            "and lubrication system."
        )

    elif predicted_fault == "misfire":

        recommendation = (
            "Inspect ignition, fuel delivery "
            "and combustion system."
        )

    elif predicted_fault == "injector_abnormality":

        recommendation = (
            "Inspect fuel injector and "
            "fuel delivery system."
        )

    elif predicted_fault == "abnormal_vibration":

        recommendation = (
            "Inspect engine mounting, "
            "rotating components and bearings."
        )

    elif predicted_fault == "combustion_instability":

        recommendation = (
            "Inspect combustion and "
            "injection parameters."
        )

    elif predicted_fault == "battery_alternator_health":

        recommendation = (
            "Inspect battery and alternator "
            "charging system."
        )

    elif predicted_fault == "injection_timing_issue":

        recommendation = (
            "Inspect injection timing and "
            "fuel injection system."
        )

    elif predicted_fault == "sensor_drift":

        recommendation = (
            "Inspect sensor calibration "
            "and sensor wiring."
        )

    elif predicted_fault == "healthy":

        recommendation = (
            "No immediate maintenance required."
        )

    else:

        recommendation = (
            "Perform detailed engine inspection."
        )


    # ========================================================
    # RETURN
    # ========================================================

    return {

        "anomaly_status":
            anomaly_status,

        "anomaly_score":
            round(
                float(anomaly_score),
                4
            ),

        "predicted_fault":
            predicted_fault,

        "fault_confidence":
            f"{fault_confidence:.2f}%",

        "rul_hours":
            round(
                rul,
                2
            ),

        "decision":
            decision,

        "maintenance_recommendation":
            recommendation,

        "engineering_faults":
            engineering_faults
    }