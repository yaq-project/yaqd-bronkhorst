__all__ = ["BronkhorstMfcRS232"]

import asyncio
from typing import Dict, Any, List
import numpy as np
import serial  # type: ignore


from yaqd_core import (
    HasTransformedPosition,
    HasLimits,
    HasPosition,
    UsesSerial,
    UsesUart,
    IsDaemon,
)


class BronkhorstMfcRS232(
    HasTransformedPosition, HasLimits, HasPosition, UsesUart, UsesSerial, IsDaemon
):
    _kind = "bronkhorst-mfc-rs232"

    def __init__(self, name, config, config_filepath):
        super().__init__(name, config, config_filepath)
        self._ser = serial.Serial(
            self._config["serial_port"], baudrate=self._config["baud_rate"], timeout=0.5
        )
        if self._config["make"] is None:
            self.make = "Bronkhorst"

    def direct_serial_write(self, _bytes):
        raise NotImplementedError

    def _relative_to_transformed(self, relative_position):
        xp = [p["setpoint"] for p in self._config["calibration"]]
        fp = [p["measured"] for p in self._config["calibration"]]
        out = np.interp(relative_position, xp, fp)
        return out

    def _set_position(self, position):
        if position > 0:
            position_str = (position / float(self._config["max_position"])) * 32000
            position_str = hex(int(position_str))[2:]
        else:
            position_str = "0000"
        position_str = ":0680010121" + position_str + "\r\n"
        self._ser.write(position_str.encode())

    def _transformed_to_relative(self, transformed_position):
        xp = [p["measured"] for p in self._config["calibration"]]
        fp = [p["setpoint"] for p in self._config["calibration"]]
        return np.interp(transformed_position, xp, fp)

    async def update_state(self):
        while True:
            read_code = ":06800401210120\r\n"
            self._ser.write(read_code.encode())
            await asyncio.sleep(0.25)
            val = self._ser.readline()

            val = val.decode().rstrip()[-4:]  # Gets last 4 hex digits
            num = int(val, 16)  # Converts to decimal
            position = (float(num) / 32000) * float(
                self._config["max_position"]
            )  # Determines actual flow

            self._state["position"] = position
            if abs(self._state["position"] - self._state["destination"]) < 1.0:
                self._busy = False
            await asyncio.sleep(0.25)
