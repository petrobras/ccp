"""Unit vocabularies, input parsing and the calculation context.

The vocabularies match ``ccp/app/common.py`` so that ``.ccp`` files keep their
unit strings. Two pieces of ccp state are process-global: the pint ``barg``
unit (its offset is the ambient pressure) and ``ccp.config.POLYTROPIC_METHOD``.
``calculation_context`` sets both under one lock and restores the method on
exit, so concurrent requests in a threaded server cannot interleave them.
"""

import logging
import threading
from contextlib import contextmanager

import ccp
from ccp import Q_
from ccp.config.units import ureg

flow_m_units = ["kg/h", "kg/min", "kg/s", "lbm/h", "lbm/min", "lbm/s"]
flow_v_units = ["m³/h", "m³/min", "m³/s"]
flow_units = flow_m_units + flow_v_units
pressure_units = ["bar", "kgf/cm²", "barg", "Pa", "kPa", "MPa", "psi", "mmH2O"]
temperature_units = ["degK", "degC", "degF", "degR"]
head_units = ["kJ/kg", "J/kg", "m*g0", "ft"]
power_units = ["kW", "hp", "W", "Btu/h", "MW"]
speed_units = ["rpm", "Hz"]
length_units = ["m", "mm", "ft", "in"]
specific_heat_units = ["kJ/kg/degK", "J/kg/degK", "cal/g/degC", "Btu/lb/degF"]
oil_iso_options = ["VG 32", "VG 46"]
oil_flow_units = ["l/min", "l/h", "gal/min", "m³/h", "m³/min", "m³/s"]
density_units = ["kg/m³", "g/cm³", "g/ml", "g/l"]
area_units = ["m²", "mm²", "ft²", "in²"]
roughness_units = length_units + ["microm"]
orifice_length_units = ["mm", "m", "ft", "in"]
tappings_options = ["flange", "corner", "D D/2"]
fluid_fraction_units = ["mol_frac", "percent", "ppm"]

polytropic_methods = {
    "Sandberg-Colby": "sandberg_colby",
    "Sandberg-Colby Multistep": "sandberg_colby_multistep",
    "Huntington": "huntington",
    "Mallen-Saville": "mallen_saville",
    "Schultz": "schultz",
}

DEFAULT_AMBIENT_PRESSURE_BAR = 1.01325

_lock = threading.RLock()
_log = logging.getLogger("ccp_web.units")


class Cancelled(Exception):
    """Raised inside a calculation when its job was cancelled."""


class InputError(ValueError):
    """Invalid or missing form values, keyed by the state key."""

    def __init__(self, errors, message=None):
        self.errors = dict(errors)
        if message is None:
            first = next(iter(self.errors.items()), None)
            message = f"{len(self.errors)} invalid field(s)" + (
                f"; {first[0]}: {first[1]}" if first else ""
            )
        super().__init__(message)


def is_mass_flow_unit(unit):
    return Q_(0, unit).dimensionality == "[mass] / [time]"


def define_barg(ambient_pressure_bar):
    """Define ``barg`` with the given ambient pressure (bar) as offset."""
    ureg.define(f"barg = 1 * bar; offset: {float(ambient_pressure_bar)}")


def ambient_pressure_bar(state):
    """Ambient pressure from the options panel, in bar (absolute)."""
    reader = StateReader(state)
    value = reader.number("ambient_pressure_magnitude", required=False)
    if value is None:
        return DEFAULT_AMBIENT_PRESSURE_BAR
    unit = state.get("ambient_pressure_unit") or "bar"
    if unit == "barg":
        # Gauge ambient pressure makes no sense; read it as bar.
        unit = "bar"
    return Q_(value, unit).to("bar").m


def polytropic_method_from_state(state):
    label = state.get("polytropic_method") or "Sandberg-Colby"
    return polytropic_methods.get(label, label)


@contextmanager
def calculation_context(ambient_pressure=None, polytropic_method=None):
    """Hold the unit/config lock with ``barg`` and the polytropic method set.

    Parameters
    ----------
    ambient_pressure : float, optional
        Ambient pressure in bar used as the ``barg`` offset. Defaults to
        1.01325 bar so ``barg`` always parses.
    polytropic_method : str, optional
        ccp method name (``sandberg_colby``...). Restored on exit.
    """
    with _lock:
        define_barg(
            DEFAULT_AMBIENT_PRESSURE_BAR
            if ambient_pressure is None
            else ambient_pressure
        )
        previous = ccp.config.POLYTROPIC_METHOD
        if polytropic_method:
            ccp.config.POLYTROPIC_METHOD = polytropic_method
        try:
            yield
        finally:
            ccp.config.POLYTROPIC_METHOD = previous


@contextmanager
def state_context(state):
    """``calculation_context`` configured from a case state."""
    with calculation_context(
        ambient_pressure=ambient_pressure_bar(state),
        polytropic_method=polytropic_method_from_state(state),
    ):
        yield


class StateReader:
    """Read and validate values from a flat state dict.

    Errors are collected per key so a page can flag every invalid field at
    once; call ``raise_errors`` after reading.
    """

    def __init__(self, state):
        self.state = state
        self.errors = {}

    def raw(self, key):
        value = self.state.get(key, "")
        return "" if value is None else value

    def is_blank(self, key):
        value = self.raw(key)
        return isinstance(value, str) and value.strip() == ""

    def text(self, key, default=""):
        value = self.state.get(key)
        return default if value is None else str(value)

    def flag(self, key, default=False):
        value = self.state.get(key, default)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "on", "yes"}
        return bool(value)

    def number(self, key, required=True):
        value = self.raw(key)
        if isinstance(value, bool):
            self.errors[key] = "Not a number"
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if text == "":
            if required:
                self.errors[key] = "Required"
            return None
        if "," in text:
            self.errors[key] = "Use '.' as decimal separator"
            return None
        try:
            return float(text)
        except ValueError:
            self.errors[key] = "Not a number"
            return None

    def quantity(self, key, unit, required=True):
        """Quantity from ``key`` with ``unit`` (a unit string)."""
        value = self.number(key, required=required)
        if value is None:
            return None
        try:
            return Q_(value, unit or "")
        except Exception as exc:  # pint raises several error types
            self.errors[key] = f"Invalid unit {unit!r}: {exc}"
            return None

    def raise_errors(self):
        if self.errors:
            raise InputError(self.errors)
