
from digital_twin import EngineDigitalTwin
from predict import predict_engine, engineering_check


# ============================================================
# AEROSYNX HYBRID AI DIGITAL TWIN
# ============================================================


class AIDigitalTwin:

    def __init__(self):
        self.twin = EngineDigitalTwin()

    def process(self, telemetry):

        sensor_data = telemetry["reading"]

        # ====================================================
        # OPERATING CONTEXT
        # ====================================================

        context = telemetry.get(
            "context",
            {}
        )

        load = float(
            sensor_data.get(
                "load",
                context.get(
                    "load",
                    65
                )
            )
        )

        ambient_temp = float(
            sensor_data.get(
                "ambient_temp",
                context.get(
                    "ambient_temp",
                    30
                )
            )
        )

        altitude = float(
            sensor_data.get(
                "altitude",
                context.get(
                    "altitude",
                    8000
                )
            )
        )

        throttle = float(
            sensor_data.get(
                "throttle",
                context.get(
                    "throttle",
                    70
                )
            )
        )

        airspeed = float(
            sensor_data.get(
                "airspeed",
                context.get(
                    "airspeed",
                    35
                )
            )
        )

        # ====================================================
        # DIGITAL TWIN
        # ====================================================

        twin_input = dict(
            sensor_data
        )

        twin_input["load"] = load
        twin_input["ambient_temp"] = ambient_temp
        twin_input["altitude"] = altitude
        twin_input["throttle"] = throttle
        twin_input["airspeed"] = airspeed

        twin_result = self.twin.update(
            twin_input
        )

        # ====================================================
        # RESIDUALS
        # ====================================================

        residuals = twin_result[
            "residuals"
        ]

        # ====================================================
        # AI INPUT
        # ====================================================

        ai_input = {

            "rpm":
                sensor_data.get(
                    "rpm",
                    0
                ),

            "cht_c":
                sensor_data.get(
                    "cht_c",
                    0
                ),

            "egt_c":
                sensor_data.get(
                    "egt_c",
                    0
                ),

            "oil_press_bar":
                sensor_data.get(
                    "oil_press_bar",
                    0
                ),

            "oil_temp_c":
                sensor_data.get(
                    "oil_temp_c",
                    0
                ),

            "fuel_flow_lph":
                sensor_data.get(
                    "fuel_flow_lph",
                    0
                ),

            "vibration_g":
                sensor_data.get(
                    "vibration_g",
                    0
                ),

            "battery_v":
                sensor_data.get(
                    "battery_v",
                    0
                ),

            "injection_deg":
                sensor_data.get(
                    "injection_deg",
                    0
                ),

            "cht_residual":
                residuals.get(
                    "cht_residual",
                    0
                ),

            "egt_residual":
                residuals.get(
                    "egt_residual",
                    0
                ),

            "oil_pressure_residual":
                residuals.get(
                    "oil_pressure_residual",
                    0
                ),

            "vibration_residual":
                residuals.get(
                    "vibration_residual",
                    0
                )
        }

        # ====================================================
        # ENGINEERING CHECK
        # ====================================================

        violations, engineering_faults = (
            engineering_check(
                sensor_data
            )
        )

        # ====================================================
        # AI
        # ====================================================

        ai_result = predict_engine(

            ai_input,

            engineering_faults=
                engineering_faults

        )

        # ====================================================
        # FINAL RESULT
        # ====================================================

        return {

            "timestamp":
                telemetry.get(
                    "timestamp"
                ),

            "current_state":
                twin_result[
                    "current_state"
                ],

            "expected_state":
                twin_result[
                    "expected_state"
                ],

            "residuals":
                residuals,

            "health_score":
                twin_result[
                    "health_score"
                ],

            "ai_prediction":
                ai_result,

            "source":
                telemetry.get(
                    "source",
                    {}
                ),

            "context":
                context,

            "physics":
                twin_result.get(
                    "physics",
                    {}
                ),

            "engineering_violations":
                violations
        }
