from simulator import AeroEngineSimulator


class DataFusion:

    # Parameters normally available from your DC motor setup
    HARDWARE_PARAMETERS = [
        "rpm",
        "vibration_g",
        "battery_v"
    ]

    # Parameters that your prototype may not have
    SIMULATED_PARAMETERS = [
        "cht_c",
        "egt_c",
        "oil_press_bar",
        "oil_temp_c",
        "fuel_flow_lph",
        "injection_deg"
    ]

    def __init__(self):

        self.simulator = AeroEngineSimulator(
            seed=42
        )

    @staticmethod
    def is_valid(value):

        if value is None:
            return False

        try:
            value = float(value)

            return np.isfinite(value)

        except:

            return False

    def fuse(
        self,
        hardware_data,
        operating_conditions,
        simulation_condition="healthy"
    ):

        hardware_data = hardware_data or {}

        # -------------------------------------
        # Operating conditions
        # -------------------------------------

        rpm = hardware_data.get(
            "rpm",
            operating_conditions.get(
                "rpm",
                5000
            )
        )

        load = operating_conditions.get(
            "load",
            60
        )

        altitude = operating_conditions.get(
            "altitude",
            5000
        )

        ambient_temp = operating_conditions.get(
            "ambient_temp",
            25
        )

        throttle = operating_conditions.get(
            "throttle",
            60
        )

        # -------------------------------------
        # Generate simulated values
        # -------------------------------------

        simulated_data = self.simulator.simulate(

            rpm=rpm,

            load=load,

            altitude=altitude,

            ambient_temp=ambient_temp,

            throttle=throttle,

            condition=simulation_condition
        )

        final_data = {}

        source = {}

        # -------------------------------------
        # HARDWARE-FIRST LOGIC
        # -------------------------------------

        for parameter in self.HARDWARE_PARAMETERS:

            hardware_value = hardware_data.get(
                parameter
            )

            if hardware_value is not None:

                try:

                    hardware_value = float(
                        hardware_value
                    )

                    if np.isfinite(
                        hardware_value
                    ):

                        final_data[
                            parameter
                        ] = hardware_value

                        source[
                            parameter
                        ] = "HARDWARE"

                        continue

                except:

                    pass

            # Hardware unavailable
            # Generate fallback

            if parameter == "rpm":

                final_data[
                    parameter
                ] = rpm

            elif parameter == "vibration_g":

                final_data[
                    parameter
                ] = simulated_data[
                    "vibration_g"
                ]

            elif parameter == "battery_v":

                final_data[
                    parameter
                ] = simulated_data[
                    "battery_v"
                ]

            source[
                parameter
            ] = "SIMULATION_FALLBACK"

        # -------------------------------------
        # AERO PARAMETERS
        # -------------------------------------

        for parameter in self.SIMULATED_PARAMETERS:

            hardware_value = hardware_data.get(
                parameter
            )

            if hardware_value is not None:

                try:

                    hardware_value = float(
                        hardware_value
                    )

                    if np.isfinite(
                        hardware_value
                    ):

                        final_data[
                            parameter
                        ] = hardware_value

                        source[
                            parameter
                        ] = "HARDWARE"

                        continue

                except:

                    pass

            # Hardware does not provide this
            # parameter → simulation

            final_data[
                parameter
            ] = simulated_data[
                parameter
            ]

            source[
                parameter
            ] = "SIMULATION"

        # -------------------------------------
        # Operating conditions
        # -------------------------------------

        final_data["load"] = load

        final_data["altitude"] = altitude

        final_data["ambient_temp"] = ambient_temp

        final_data["throttle"] = throttle

        source["load"] = "OPERATING_CONDITION"

        source["altitude"] = "OPERATING_CONDITION"

        source["ambient_temp"] = "OPERATING_CONDITION"

        source["throttle"] = "OPERATING_CONDITION"

        return {

            "data": final_data,

            "source": source
        }