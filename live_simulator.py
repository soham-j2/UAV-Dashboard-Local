import time
import random
import math

from ai_digital_twin import AIDigitalTwin


# ==========================================================
# AEROSYNC LIVE ENGINE SIMULATOR
# ==========================================================

twin = AIDigitalTwin()


# Starting engine conditions
rpm = 3000
load = 60
ambient_temp = 30
altitude = 5000
throttle = 65

# Simulated degradation
degradation = 0.0


def generate_engine_data():

    global rpm
    global load
    global ambient_temp
    global altitude
    global throttle
    global degradation

    # ------------------------------------------------------
    # Slowly change engine operating conditions
    # ------------------------------------------------------

    rpm += random.uniform(-80, 80)

    rpm = max(1800, min(3500, rpm))

    load += random.uniform(-3, 3)

    load = max(30, min(90, load))

    throttle += random.uniform(-2, 2)

    throttle = max(30, min(90, throttle))


    # ------------------------------------------------------
    # Simulate gradual engine degradation
    # ------------------------------------------------------

    degradation += 0.002

    # ------------------------------------------------------
    # Calculate simulated sensor readings
    # ------------------------------------------------------

    cht = (
        90
        + 0.018 * rpm
        + 0.45 * load
        + 0.5 * ambient_temp
        - 0.001 * altitude
        + degradation * 50
        + random.uniform(-2, 2)
    )


    egt = (
        450
        + 0.025 * rpm
        + 0.9 * load
        + 0.35 * throttle
        + degradation * 80
        + random.uniform(-5, 5)
    )


    oil_pressure = (
        35
        + 0.008 * rpm
        - 0.08 * load
        - degradation * 10
        + random.uniform(-1, 1)
    )


    vibration = (
        0.2
        + 0.00015 * rpm
        + degradation * 2
        + random.uniform(-0.05, 0.05)
    )


    fuel_flow = (
        5
        + load * 0.06
        + random.uniform(-0.3, 0.3)
    )


    current = (
        1.5
        + load * 0.02
        + random.uniform(-0.1, 0.1)
    )


    return {

        "rpm": rpm,

        "load": load,

        "ambient_temp": ambient_temp,

        "altitude": altitude,

        "throttle": throttle,

        "cht": cht,

        "egt": egt,

        "oil_pressure": oil_pressure,

        "vibration": vibration,

        "fuel_flow": fuel_flow,

        "current": current
    }


# ==========================================================
# LIVE LOOP
# ==========================================================

print("\n")
print("=" * 70)
print("             AEROSYNC LIVE ENGINE SIMULATOR")
print("=" * 70)

print("\nStarting engine simulation...")
print("Press CTRL + C to stop.\n")


try:

    while True:

        # Generate new sensor data

        sensor_data = generate_engine_data()


        # Send data to Digital Twin

        result = twin.process(
            sensor_data
        )


        # --------------------------------------------------
        # DISPLAY CURRENT ENGINE DATA
        # --------------------------------------------------

        print("\n" + "-" * 70)

        print("LIVE ENGINE DATA")

        print(
            f"RPM           : {sensor_data['rpm']:.0f}"
        )

        print(
            f"Load          : {sensor_data['load']:.1f}%"
        )

        print(
            f"CHT           : {sensor_data['cht']:.1f} °C"
        )

        print(
            f"EGT           : {sensor_data['egt']:.1f} °C"
        )

        print(
            f"Oil Pressure  : {sensor_data['oil_pressure']:.1f} PSI"
        )

        print(
            f"Vibration     : {sensor_data['vibration']:.2f}"
        )


        # --------------------------------------------------
        # DIGITAL TWIN
        # --------------------------------------------------

        print("\nDIGITAL TWIN")

        print(
            f"Health Score  : {result['health_score']:.1f}/100"
        )


        # --------------------------------------------------
        # AI RESULTS
        # --------------------------------------------------

        ai = result["ai_prediction"]

        print("\nAI/ML")

        print(
            f"Anomaly       : {ai['anomaly_detected']}"
        )

        print(
            f"Fault         : {ai['predicted_fault']}"
        )

        print(
            f"Confidence    : {ai['fault_confidence']:.2f}"
        )

        print(
            f"RUL           : {ai['predicted_rul_hours']:.1f} hours"
        )


        # --------------------------------------------------
        # WAIT 1 SECOND
        # --------------------------------------------------

        time.sleep(1)


except KeyboardInterrupt:

    print("\n")
    print("=" * 70)
    print("AEROSYNC SIMULATOR STOPPED")
    print("=" * 70)