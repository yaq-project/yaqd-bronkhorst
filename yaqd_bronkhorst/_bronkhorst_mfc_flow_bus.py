__all__ = ["BronkhorstMfcFlowBus"]

import asyncio
from typing import Dict, Any, List
import numpy as np

import propar  # type: ignore
from yaqd_core import (
    HasTransformedPosition,
    HasLimits,
    HasPosition,
    UsesSerial,
    UsesUart,
    IsDaemon,
)


class BronkhorstMfcFlowBus(
    HasTransformedPosition, HasLimits, HasPosition, UsesUart, UsesSerial, IsDaemon
):
    _kind = "bronkhorst-mfc-flow-bus"

    def __init__(self, name, config, config_filepath):
        super().__init__(name, config, config_filepath)
        self._instrument = propar.instrument(
            comport=self._config["serial_port"], baudrate=self._config["baud_rate"]
        )
        if self._instrument.setpoint is not None:
            self._state["destination"] = self._instrument.setpoint
        if self._config["make"] is None:
            self.make = "Bronkhorst"
        if self._config["model"] is None:
            self.model = self._instrument.readParameter(91)
        if self._config["serial"] is None:
            self.serial = self._instrument.readParameter(92)

    def direct_serial_write(self, _bytes):
        self._instrument.master.propar.serial.write(_bytes)

    def get_fluid_name(self) -> str:
        return self._instrument.readParameter(25).strip()

    def get_temperature(self) -> float:
        return self._instrument.readParameter(142)

    def get_temperature_units(self) -> str:
        return "degC"

    def _relative_to_transformed(self, relative_position):
        xp = [p["setpoint"] for p in self._config["calibration"]]
        fp = [p["measured"] for p in self._config["calibration"]]
        out = np.interp(relative_position, xp, fp)
        return out

    def _set_position(self, position):
        self._instrument.setpoint = position

    def _transformed_to_relative(self, transformed_position):
        xp = [p["measured"] for p in self._config["calibration"]]
        fp = [p["setpoint"] for p in self._config["calibration"]]
        return np.interp(transformed_position, xp, fp)

    async def update_state(self):
        while True:
            self._state["position"] = self._instrument.measure
            if abs(self._state["position"] - self._state["destination"]) < 1.0:
                self._busy = False
            await asyncio.sleep(0.25)
