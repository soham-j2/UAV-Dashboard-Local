# ============================================================
# AeroSynX - Physics-Informed Digital Twin
# ============================================================

import math
import json
import os


class EngineDigitalTwin:

    # ========================================================
    # ATMOSPHERIC CONSTANTS
    # ========================================================

    R_AIR = 287.05          # J/(kg·K)
    G = 9.80665             # m/s²
    L = 0.0065              # K/m
    T0 = 288.15             # K
    P0 = 101325.0            # Pa
    RHO0 = 1.225             # kg/m³

    # ========================================================
    # PROTOTYPE ENGINE PARAMETERS
    # ========================================================

    MAX_POWER_KW = 40.0

    # Cooling calibration constant
    K_COOL = 0.42

    # ========================================================
    # ENGINE AGING
    # 2% oil-pressure baseline reduction per 100 hours
    # ========================================================

    OIL_AGING_RATE = 0.02

    MAX_AGING_REDUCTION = 0.20

    STATE_FILE = "digital_twin_state.json"

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self, flight_hours=0.0):

        self.flight_hours = float(
            flight_hours
        )

        self.load_state()

    # ========================================================
    # LOAD DIGITAL TWIN STATE
    # ========================================================

    def load_state(self):

        if not os.path.exists(
            self.STATE_FILE
        ):
            return

        try:

            with open(
                self.STATE_FILE,
                "r"
            ) as file:

                state = json.load(file)

            self.flight_hours = float(
                state.get(
                    "flight_hours",
                    self.flight_hours
                )
            )

        except Exception:

            pass

    # ========================================================
    # SAVE DIGITAL TWIN STATE
    # ========================================================

    def save_state(self):

        state = {

            "flight_hours":
                round(
                    self.flight_hours,
                    3
                )
        }

        try:

            with open(
                self.STATE_FILE,
                "w"
            ) as file:

                json.dump(
                    state,
                    file,
                    indent=4
                )

        except Exception:

            pass

    # ========================================================
    # ADD FLIGHT HOURS
    # ========================================================

    def add_flight_time(
        self,
        hours
    ):

        if hours <= 0:
            return

        self.flight_hours += float(
            hours
        )

        self.save_state()

    # ========================================================
    # AIR DENSITY
    # ========================================================

    def calculate_air_density(
        self,
        altitude_ft
    ):

        """
        ISA atmosphere approximation.

        rho = rho0 *
              (1 - L*h/T0)^(g/(R*L))
        """

        altitude_m = (
            float(altitude_ft)
            * 0.3048
        )

        altitude_m = max(
            0.0,
            min(
                altitude_m,
                11000.0
            )
        )

        temperature_ratio = (

            1.0
            -
            (
                self.L
                * altitude_m
                / self.T0
            )
        )

        exponent = (

            self.G
            /
            (
                self.R_AIR
                * self.L
            )
        )

        density = (

            self.RHO0
            *
            (
                temperature_ratio
                ** exponent
            )
        )

        return density

    # ========================================================
    # DENSITY RATIO
    # ========================================================

    def calculate_density_ratio(
        self,
        altitude_ft
    ):

        density = self.calculate_air_density(
            altitude_ft
        )

        return density / self.RHO0

    # ========================================================
    # ENGINE POWER
    # ========================================================

    def calculate_power(
        self,
        rpm,
        load
    ):

        """
        Simplified brake power model.

        Power depends on:
            RPM
            Engine load
        """

        load_fraction = max(
            0.0,
            min(
                float(load) / 100.0,
                1.0
            )
        )

        rpm_factor = max(
            0.70,
            min(
                float(rpm) / 5100.0,
                1.05
            )
        )

        power_kw = (

            self.MAX_POWER_KW
            *
            load_fraction
            *
            rpm_factor
        )

        return power_kw

    # ========================================================
    # BSFC MAP
    # ========================================================

    def calculate_bsfc(
        self,
        rpm,
        load
    ):

        """
        Simplified BSFC map.

        BSFC = Brake Specific Fuel Consumption

        Unit:
            g/kWh
        """

        rpm = float(rpm)
        load = float(load)

        # Nominal BSFC
        bsfc = 300.0

        # Low-load penalty
        if load < 40:

            bsfc += (
                40.0 - load
            ) * 0.8

        # High-load penalty
        elif load > 85:

            bsfc += (
                load - 85.0
            ) * 0.7

        # RPM penalty
        rpm_difference = abs(
            rpm - 5100.0
        )

        bsfc += (

            rpm_difference
            /
            1000.0
            *
            12.0
        )

        return bsfc

    # ========================================================
    # EXPECTED FUEL FLOW
    # ========================================================

    def calculate_expected_fuel_flow(
        self,
        rpm,
        load
    ):

        """
        Fuel flow calculation:

        Fuel mass =
            Power × BSFC

        Then convert:
            g/hour → kg/hour → L/hour
        """

        power_kw = self.calculate_power(
            rpm,
            load
        )

        bsfc = self.calculate_bsfc(
            rpm,
            load
        )

        fuel_g_per_hour = (

            power_kw
            *
            bsfc
        )

        fuel_kg_per_hour = (

            fuel_g_per_hour
            /
            1000.0
        )

        # Approximate gasoline density
        fuel_density = 0.74

        fuel_lph = (

            fuel_kg_per_hour
            /
            fuel_density
        )

        return fuel_lph

    # ========================================================
    # EXPECTED CHT
    # ========================================================

    def calculate_expected_cht(
        self,
        ambient_temp,
        load,
        rpm,
        altitude_ft,
        airspeed
    ):

        """
        Simplified convective cooling model.

        Expected CHT =
            Ambient temperature
            +
            heat generation / cooling capability

        Cooling capability depends on:
            Air density
            Airspeed
        """

        density_ratio = (

            self.calculate_density_ratio(
                altitude_ft
            )
        )

        density_factor = math.sqrt(
            max(
                density_ratio,
                0.10
            )
        )

        # Avoid division by zero
        airspeed = max(
            float(airspeed),
            5.0
        )

        heat_term = (

            float(load)
            *
            float(rpm)

            /

            (
                self.K_COOL
                *
                density_factor
                *
                airspeed
            )
        )

        # Prototype calibration scale
        temperature_rise = (

            heat_term
            *
            0.00035
        )

        expected_cht = (

            float(ambient_temp)
            +
            temperature_rise
        )

        # Keep output inside reasonable prototype limits
        expected_cht = max(
            90.0,
            min(
                expected_cht,
                130.0
            )
        )

        return expected_cht

    # ========================================================
    # EXPECTED EGT
    # ========================================================

    def calculate_expected_egt(
        self,
        rpm,
        load,
        ambient_temp,
        fuel_flow
    ):

        """
        Simplified combustion thermal model.
        """

        load_fraction = (

            float(load)
            /
            100.0
        )

        rpm_factor = (

            float(rpm)
            /
            5100.0
        )

        expected_egt = (

            600.0

            +

            (
                100.0
                *
                load_fraction
            )

            +

            (
                20.0
                *
                rpm_factor
            )

            +

            (
                0.20
                *
                float(fuel_flow)
            )

            +

            (
                0.15
                *
                float(ambient_temp)
            )
        )

        return max(
            600.0,
            min(
                expected_egt,
                760.0
            )
        )

    # ========================================================
    # EXPECTED OIL PRESSURE
    # ========================================================

    def calculate_expected_oil_pressure(
        self,
        rpm,
        oil_temp
    ):

        """
        Oil pressure depends on:
            RPM
            Oil temperature
            Engine aging
        """

        rpm_factor = (

            float(rpm)
            /
            5100.0
        )

        base_pressure = (

            3.4
            *
            rpm_factor
        )

        # Hot oil reduces pressure
        temperature_effect = (

            (
                float(oil_temp)
                -
                95.0
            )
            *
            0.008
        )

        expected_pressure = (

            base_pressure
            -
            temperature_effect
        )

        # ====================================================
        # ENGINE AGING
        # ====================================================

        aging_steps = (

            self.flight_hours
            /
            100.0
        )

        aging_reduction = (

            aging_steps
            *
            self.OIL_AGING_RATE
        )

        aging_reduction = min(
            aging_reduction,
            self.MAX_AGING_REDUCTION
        )

        expected_pressure *= (

            1.0
            -
            aging_reduction
        )

        return max(
            2.0,
            min(
                expected_pressure,
                4.5
            )
        )

    # ========================================================
    # EXPECTED OIL TEMPERATURE
    # ========================================================

    def calculate_expected_oil_temperature(
        self,
        ambient_temp,
        load,
        cht
    ):

        expected_oil_temp = (

            float(ambient_temp)

            +

            45.0

            +

            (
                float(load)
                *
                0.20
            )

            +

            (
                (
                    float(cht)
                    -
                    110.0
                )
                *
                0.10
            )
        )

        return max(
            80.0,
            min(
                expected_oil_temp,
                125.0
            )
        )

    # ========================================================
    # EXPECTED VIBRATION
    # ========================================================

    def calculate_expected_vibration(
        self,
        rpm,
        load
    ):

        rpm_factor = (

            float(rpm)
            /
            5100.0
        )

        load_factor = (

            float(load)
            /
            100.0
        )

        vibration = (

            0.07

            +

            (
                0.025
                *
                rpm_factor
            )

            +

            (
                0.025
                *
                load_factor
            )
        )

        return max(
            0.05,
            min(
                vibration,
                0.15
            )
        )

    # ========================================================
    # EXPECTED BATTERY VOLTAGE
    # ========================================================

    def calculate_expected_battery_voltage(
        self,
        rpm
    ):

        rpm_factor = (

            float(rpm)
            /
            5100.0
        )

        voltage = (

            13.8
            +
            (
                0.5
                *
                rpm_factor
            )
        )

        return max(
            13.5,
            min(
                voltage,
                14.5
            )
        )

    # ========================================================
    # EXPECTED INJECTION TIMING
    # ========================================================

    def calculate_expected_injection_timing(
        self,
        rpm,
        load
    ):

        timing = (

            22.0

            +

            (
                (
                    float(rpm)
                    -
                    5100.0
                )
                /
                1000.0
                *
                1.5
            )

            +

            (
                (
                    50.0
                    -
                    float(load)
                )
                /
                100.0
            )
        )

        return max(
            18.0,
            min(
                timing,
                27.0
            )
        )

    # ========================================================
    # COMPLETE EXPECTED STATE
    # ========================================================

    def calculate_expected_state(
        self,
        data
    ):

        rpm = float(
            data.get(
                "rpm",
                5100
            )
        )

        load = float(
            data.get(
                "load",
                65
            )
        )

        ambient_temp = float(
            data.get(
                "ambient_temp",
                30
            )
        )

        altitude = float(
            data.get(
                "altitude",
                0
            )
        )

        airspeed = float(
            data.get(
                "airspeed",
                35
            )
        )

        # ----------------------------------------------------
        # Fuel
        # ----------------------------------------------------

        expected_fuel = (

            self.calculate_expected_fuel_flow(
                rpm,
                load
            )
        )

        # ----------------------------------------------------
        # CHT
        # ----------------------------------------------------

        expected_cht = (

            self.calculate_expected_cht(
                ambient_temp,
                load,
                rpm,
                altitude,
                airspeed
            )
        )

        # ----------------------------------------------------
        # EGT
        # ----------------------------------------------------

        expected_egt = (

            self.calculate_expected_egt(
                rpm,
                load,
                ambient_temp,
                expected_fuel
            )
        )

        # ----------------------------------------------------
        # Oil temperature
        # ----------------------------------------------------

        expected_oil_temp = (

            self.calculate_expected_oil_temperature(
                ambient_temp,
                load,
                expected_cht
            )
        )

        # ----------------------------------------------------
        # Oil pressure
        # ----------------------------------------------------

        expected_oil_pressure = (

            self.calculate_expected_oil_pressure(
                rpm,
                expected_oil_temp
            )
        )

        # ----------------------------------------------------
        # Vibration
        # ----------------------------------------------------

        expected_vibration = (

            self.calculate_expected_vibration(
                rpm,
                load
            )
        )

        # ----------------------------------------------------
        # Battery
        # ----------------------------------------------------

        expected_battery = (

            self.calculate_expected_battery_voltage(
                rpm
            )
        )

        # ----------------------------------------------------
        # Injection timing
        # ----------------------------------------------------

        expected_injection = (

            self.calculate_expected_injection_timing(
                rpm,
                load
            )
        )

        return {

            "cht_c":
                round(
                    expected_cht,
                    3
                ),

            "egt_c":
                round(
                    expected_egt,
                    3
                ),

            "oil_press_bar":
                round(
                    expected_oil_pressure,
                    3
                ),

            "oil_temp_c":
                round(
                    expected_oil_temp,
                    3
                ),

            "fuel_flow_lph":
                round(
                    expected_fuel,
                    3
                ),

            "vibration_g":
                round(
                    expected_vibration,
                    4
                ),

            "battery_v":
                round(
                    expected_battery,
                    3
                ),

            "injection_deg":
                round(
                    expected_injection,
                    3
                ),

            "air_density":
                round(
                    self.calculate_air_density(
                        altitude
                    ),
                    4
                ),

            "power_kw":
                round(
                    self.calculate_power(
                        rpm,
                        load
                    ),
                    3
                ),

            "bsfc_g_kwh":
                round(
                    self.calculate_bsfc(
                        rpm,
                        load
                    ),
                    3
                )
        }

    # ========================================================
    # RESIDUAL CALCULATION
    # ========================================================

    def calculate_residuals(
        self,
        actual,
        expected
    ):

        residuals = {}

        parameter_map = {

            "cht_c":
                "cht_residual",

            "egt_c":
                "egt_residual",

            "oil_press_bar":
                "oil_pressure_residual",

            "oil_temp_c":
                "oil_temp_residual",

            "fuel_flow_lph":
                "fuel_flow_residual",

            "vibration_g":
                "vibration_residual",

            "battery_v":
                "battery_residual",

            "injection_deg":
                "injection_residual"
        }

        for actual_field, residual_field in parameter_map.items():

            if (
                actual_field in actual
                and
                actual_field in expected
            ):

                residuals[residual_field] = round(

                    float(
                        actual[actual_field]
                    )
                    -
                    float(
                        expected[actual_field]
                    ),

                    4
                )

        return residuals

    # ========================================================
    # HEALTH SCORE
    # ========================================================

    def calculate_health_score(
        self,
        residuals
    ):

        penalties = []

        # CHT
        if "cht_residual" in residuals:

            penalties.append(

                min(
                    abs(
                        residuals[
                            "cht_residual"
                        ]
                    )
                    /
                    25.0,

                    1.0
                )
            )

        # EGT
        if "egt_residual" in residuals:

            penalties.append(

                min(
                    abs(
                        residuals[
                            "egt_residual"
                        ]
                    )
                    /
                    100.0,

                    1.0
                )
            )

        # Oil pressure
        if "oil_pressure_residual" in residuals:

            penalties.append(

                min(
                    abs(
                        residuals[
                            "oil_pressure_residual"
                        ]
                    )
                    /
                    1.5,

                    1.0
                )
            )

        # Oil temperature
        if "oil_temp_residual" in residuals:

            penalties.append(

                min(
                    abs(
                        residuals[
                            "oil_temp_residual"
                        ]
                    )
                    /
                    25.0,

                    1.0
                )
            )

        # Vibration
        if "vibration_residual" in residuals:

            penalties.append(

                min(
                    abs(
                        residuals[
                            "vibration_residual"
                        ]
                    )
                    /
                    0.20,

                    1.0
                )
            )

        # Fuel flow
        if "fuel_flow_residual" in residuals:

            penalties.append(

                min(
                    abs(
                        residuals[
                            "fuel_flow_residual"
                        ]
                    )
                    /
                    5.0,

                    1.0
                )
            )

        # Battery
        if "battery_residual" in residuals:

            penalties.append(

                min(
                    abs(
                        residuals[
                            "battery_residual"
                        ]
                    )
                    /
                    1.0,

                    1.0
                )
            )

        # Injection timing
        if "injection_residual" in residuals:

            penalties.append(

                min(
                    abs(
                        residuals[
                            "injection_residual"
                        ]
                    )
                    /
                    5.0,

                    1.0
                )
            )

        if not penalties:

            return 100.0

        average_penalty = (

            sum(penalties)
            /
            len(penalties)
        )

        health = (

            100.0
            *
            (
                1.0
                -
                average_penalty
            )
        )

        return round(

            max(
                0.0,
                min(
                    health,
                    100.0
                )
            ),

            2
        )

    # ========================================================
    # MAIN DIGITAL TWIN FUNCTION
    # ========================================================

    def update(
        self,
        data,
        flight_time_hours=0.0
    ):

        """
        Main Digital Twin pipeline.

        INPUT:
            Current engine telemetry

        OUTPUT:
            Current state
            Expected state
            Residuals
            Health score
            Physics information
        """

        # ----------------------------------------------------
        # Update engine age
        # ----------------------------------------------------

        if flight_time_hours > 0:

            self.add_flight_time(
                flight_time_hours
            )

        # ----------------------------------------------------
        # Current state
        # ----------------------------------------------------

        current_state = dict(
            data
        )

        # ----------------------------------------------------
        # Physics-based expected state
        # ----------------------------------------------------

        expected_state = (

            self.calculate_expected_state(
                data
            )
        )

        # ----------------------------------------------------
        # Residuals
        # ----------------------------------------------------

        residuals = (

            self.calculate_residuals(
                current_state,
                expected_state
            )
        )

        # ----------------------------------------------------
        # Health
        # ----------------------------------------------------

        health_score = (

            self.calculate_health_score(
                residuals
            )
        )

        # ----------------------------------------------------
        # FINAL DIGITAL TWIN RESULT
        # ----------------------------------------------------

        return {

            "current_state":
                current_state,

            "expected_state":
                expected_state,

            "residuals":
                residuals,

            "health_score":
                health_score,

            "flight_hours":
                round(
                    self.flight_hours,
                    3
                ),

            "physics": {

                "air_density":
                    expected_state[
                        "air_density"
                    ],

                "power_kw":
                    expected_state[
                        "power_kw"
                    ],

                "bsfc_g_kwh":
                    expected_state[
                        "bsfc_g_kwh"
                    ]
            }
        }