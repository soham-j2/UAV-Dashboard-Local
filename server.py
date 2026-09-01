from flask import Flask, jsonify
from flask_cors import CORS
import time

from telemetry_bridge import create_hybrid_reading
from ai_digital_twin import AIDigitalTwin


# ============================================================
# AEROSYNX BACKEND SERVER
# ============================================================

app = Flask(__name__)
CORS(app)

ai_twin = AIDigitalTwin()


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "project": "AeroSynX",
        "status": "Backend running",
        "message": "AeroSynX Digital Twin API"
    })


# ============================================================
# LIVE TELEMETRY + AI
# ============================================================

@app.route("/api/dashboard", methods=["GET"])
def dashboard():

    try:

        # ----------------------------------------------------
        # telemetry_bridge:
        #
        # API/Hardware value → use real value
        # Missing value → simulate
        # ----------------------------------------------------

        telemetry = create_hybrid_reading()

        # ----------------------------------------------------
        # ADD TIMESTAMP
        # ----------------------------------------------------

        telemetry["timestamp"] = int(
            time.time() * 1000
        )

        # ----------------------------------------------------
        # SEND COMPLETE READING TO DIGITAL TWIN + AI
        # ----------------------------------------------------

        result = ai_twin.process(
            telemetry
        )

        # ----------------------------------------------------
        # FINAL RESPONSE FOR REACT
        # ----------------------------------------------------

        return jsonify({

            "success": True,

            "timestamp":
                telemetry["timestamp"],

            "reading":
                result["current_state"],

            "expected":
                result["expected_state"],

            "residuals":
                result["residuals"],

            "health_score":
                result["health_score"],

            "source":
                result["source"],

            "ai":
                result["ai_prediction"],

            "range_status":
                telemetry.get(
                    "range_status",
                    {}
                ),

            "possible_faults":
                telemetry.get(
                    "possible_faults",
                    []
                ),

            "api":
                telemetry.get(
                    "api",
                    {}
                ),

            "physics":
                result.get(
                    "physics",
                    {}
                ),

            "context":
                telemetry.get(
                    "context",
                    {}
                )

        })

    except Exception as error:

        print(
            "Dashboard error:",
            error
        )

        return jsonify({

            "success": False,

            "error":
                str(error)

        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({

        "status": "online",

        "service":
            "AeroSynX Digital Twin",

        "timestamp":
            int(time.time() * 1000)

    })


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 65)
    print("              AEROSYNX BACKEND")
    print("=" * 65)
    print()
    print("Dashboard API:")
    print("http://127.0.0.1:5000/api/dashboard")
    print()
    print("Health:")
    print("http://127.0.0.1:5000/api/health")
    print()
    print("=" * 65)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )