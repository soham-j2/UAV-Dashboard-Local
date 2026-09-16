from flask import Flask, jsonify
from flask_cors import CORS
import time
import threading

from telemetry_bridge import create_hybrid_reading
from ai_digital_twin import AIDigitalTwin


# ============================================================
# AEROSYNX BACKEND SERVER  —  Low-Latency Edition
#
# Architecture:
#   Background thread runs the full telemetry + AI pipeline
#   every 50 ms and stores the result in _CACHE.
#
#   /api/dashboard just returns _CACHE instantly (< 1 ms).
#   No blocking work happens on the request path.
# ============================================================

app = Flask(__name__)
CORS(app)

ai_twin = AIDigitalTwin()


# ============================================================
# SHARED CACHE
# ============================================================

_CACHE_LOCK  = threading.Lock()
_CACHE       = None          # last computed payload
_CACHE_TIME  = 0.0           # epoch seconds of last update

PIPELINE_INTERVAL = 0.05     # 50 ms → 20 Hz refresh rate


# ============================================================
# BACKGROUND PIPELINE LOOP
# ============================================================

def _pipeline_loop():
    global _CACHE, _CACHE_TIME

    while True:
        loop_start = time.perf_counter()

        try:
            # 1. Fetch / blend telemetry (non-blocking — uses cached API data)
            telemetry = create_hybrid_reading()
            telemetry["timestamp"] = int(time.time() * 1000)

            # 2. Run digital twin + AI
            result = ai_twin.process(telemetry)

            # 3. Build response payload
            payload = {
                "success":        True,
                "timestamp":      telemetry["timestamp"],
                "reading":        result["current_state"],
                "expected":       result["expected_state"],
                "residuals":      result["residuals"],
                "health_score":   result["health_score"],
                "source":         result["source"],
                "ai":             result["ai_prediction"],
                "range_status":   telemetry.get("range_status", {}),
                "possible_faults":telemetry.get("possible_faults", []),
                "api":            telemetry.get("api", {}),
                "physics":        result.get("physics", {}),
                "context":        telemetry.get("context", {}),
            }

                        with _CACHE_LOCK:
                _CACHE      = payload
                _CACHE_TIME = time.time()

        except Exception as error:
            import traceback
            print("[Pipeline] Error:", error, flush=True)
            traceback.print_exc()

        # Sleep only for the remainder of the interval
        elapsed = time.perf_counter() - loop_start
        sleep_for = max(0.0, PIPELINE_INTERVAL - elapsed)
        time.sleep(sleep_for)


# Start background pipeline immediately
_bg_thread = threading.Thread(target=_pipeline_loop, daemon=True)
_bg_thread.start()


# ============================================================
# HOME
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "project": "AeroSynX",
        "status":  "Backend running",
        "message": "AeroSynX Digital Twin API — Low-Latency Edition"
    })


# ============================================================
# LIVE TELEMETRY + AI  (returns cached result — instant)
# ============================================================

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    with _CACHE_LOCK:
        payload = _CACHE

    if payload is None:
        # Pipeline hasn't produced a result yet (first ~50 ms)
        return jsonify({"success": False, "error": "Warming up…"}), 503

    return jsonify(payload)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():
    with _CACHE_LOCK:
        age_ms = int((time.time() - _CACHE_TIME) * 1000) if _CACHE_TIME else -1

    return jsonify({
        "status":    "online",
        "service":   "AeroSynX Digital Twin",
        "cache_age_ms": age_ms,
        "timestamp": int(time.time() * 1000)
    })


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 65)
    print("         AEROSYNX BACKEND  —  Low-Latency Edition")
    print("=" * 65)
    print()
    print("Dashboard API:")
    print("  http://127.0.0.1:5001/api/dashboard")
    print()
    print("Health:")
    print("  http://127.0.0.1:5001/api/health")
    print()
    print(f"Pipeline interval: {int(PIPELINE_INTERVAL * 1000)} ms  ({int(1/PIPELINE_INTERVAL)} Hz)")
    print("=" * 65)

    app.run(
        host="0.0.0.0",
        port=5001,
        debug=False,      # debug=True adds ~5-10ms overhead per request
        threaded=True,
        use_reloader=False
    )