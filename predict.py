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
    detected_fault_scores = {}

    rpm = float(data.get("rpm", 0))
    cht = float(data.get("cht_c", 0))
    egt = float(data.get("egt_c", 0))
    oil_press = float(data.get("oil_press_bar", 0))
    oil_temp = float(data.get("oil_temp_c", 0))
    fuel_flow = float(data.get("fuel_flow_lph", 0))
    vibration = float(data.get("vibration_g", 0))
    battery = float(data.get("battery_v", 0))

    # 1. API Direct Fault Signal (Highest Priority if sent in data payload)
    raw_fault = data.get("fault") or data.get("active_fault") or data.get("context", {}).get("active_fault")
    if raw_fault and raw_fault != "none":
        fault_key = raw_fault
        if fault_key == "coking":
            fault_key = "coking_degradation"
        elif fault_key == "lubrication":
            fault_key = "lubrication_issue"
        elif fault_key == "battery":
            fault_key = "battery_alternator_health"
        detected_fault_scores[fault_key] = 100

    # 2. Signature Parameter Matching
    if (9 <= fuel_flow <= 13) or (egt >= 730 and fuel_flow < 14):
        detected_fault_scores["injector_abnormality"] = detected_fault_scores.get("injector_abnormality", 0) + 90

    if (11.0 <= battery <= 13.5):
        detected_fault_scores["battery_alternator_health"] = detected_fault_scores.get("battery_alternator_health", 0) + 85

    if (0.8 <= oil_press <= 2.4) or (oil_temp >= 110):
        detected_fault_scores["lubrication_issue"] = detected_fault_scores.get("lubrication_issue", 0) + 80

    if (130 <= cht <= 165 and oil_temp >= 105) or (fuel_flow >= 17 and egt >= 730):
        detected_fault_scores["coking_degradation"] = detected_fault_scores.get("coking_degradation", 0) + 75

    if (135 <= cht <= 170 and egt >= 730 and oil_temp >= 108):
        detected_fault_scores["overheating"] = detected_fault_scores.get("overheating", 0) + 70

    if (4400 <= rpm <= 4750 and 540 <= egt <= 620):
        detected_fault_scores["misfire"] = detected_fault_scores.get("misfire", 0) + 65

    if (140 <= cht <= 175 and oil_temp < 105):
        detected_fault_scores["sensor_drift"] = detected_fault_scores.get("sensor_drift", 0) + 60

    if (vibration >= 0.20 and (egt > 750 or egt < 600)):
        detected_fault_scores["combustion_instability"] = detected_fault_scores.get("combustion_instability", 0) + 55

    if (vibration >= 0.20):
        detected_fault_scores["abnormal_vibration"] = detected_fault_scores.get("abnormal_vibration", 0) + 50

    # Range violations check
    for field, limits in NORMAL_RANGES.items():
        if field in data and data[field] is not None:
            val = float(data[field])
            minimum, maximum = limits
            if val < minimum or val > maximum:
                faults = FAULT_MAPPING.get(field, [])
                violations.append({
                    "parameter": field,
                    "value": val,
                    "normal_min": minimum,
                    "normal_max": maximum,
                    "possible_faults": faults
                })

    # Sort detected faults by score descending (highest priority first!)
    sorted_faults = sorted(detected_fault_scores.keys(), key=lambda f: detected_fault_scores[f], reverse=True)

    return violations, sorted_faults



# ============================================================
# PREDICT ENGINE
# ============================================================

_PREDICT_CACHE = None
_LAST_PREDICT_TIME = 0.0

def predict_engine(
    ai_input,
    engineering_faults=None
):
    global _PREDICT_CACHE, _LAST_PREDICT_TIME
    import time
    now = time.time()

    if (now - _LAST_PREDICT_TIME < 0.10) and _PREDICT_CACHE is not None and not engineering_faults:
        return _PREDICT_CACHE

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

        predicted_fault = engineering_faults[0]

        fault_confidence = max(
            fault_confidence,
            85.0
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

    result = {

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

    _PREDICT_CACHE = result
    _LAST_PREDICT_TIME = now
    return result