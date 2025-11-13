import pickle
from collections import namedtuple

import pytest
from numpy.testing import assert_allclose

from ccp.config.units import Q_, check_units


def test_new_units_loaded():
    speed = Q_(1, "RPM")
    assert speed.m == 1
    # check if h is hour instead of planck constant
    v = Q_(3600, "m/h")
    assert v.to("m/s").m == 1


def test_units_pickle():
    speed = Q_(1, "RPM")
    speed_pickled = pickle.loads(pickle.dumps(speed))
    assert speed == speed_pickled


# each possible argument
Argument = namedtuple(
    "Argument", ["single_value", "si_unit", "other_unit", "expected_converted_value"]
)
arguments = {
    "E": Argument(1, "N/m²", "lbf/in²", 6894.7572931683635),
    "Gs": Argument(1, "N/m²", "lbf/in²", 6894.7572931683635),
    "rho": Argument(1, "kg/m³", "lb/foot**3", 16.01846337396014),
    "L": Argument(1, "meter", "inches", 0.0254),
    "idl": Argument(1, "meter", "inches", 0.0254),
    "idr": Argument(1, "meter", "inches", 0.0254),
    "odl": Argument(1, "meter", "inches", 0.0254),
    "odr": Argument(1, "meter", "inches", 0.0254),
    "speed": Argument(1, "rad/s", "RPM", 0.10471975511965977),
    "frequency": Argument(1, "rad/s", "RPM", 0.10471975511965977),
    "frequency_range": Argument(
        (1, 1), "rad/s", "RPM", (0.10471975511965977, 0.10471975511965977)
    ),
    "mx": Argument(1, "kg", "lb", 0.4535923700000001),
    "my": Argument(1, "kg", "lb", 0.4535923700000001),
    "Ip": Argument(1, "kg*m²", "lb*in²", 0.0002926396534292),
    "Id": Argument(1, "kg*m²", "lb*in²", 0.0002926396534292),
    "width": Argument(1, "meter", "inches", 0.0254),
    "depth": Argument(1, "meter", "inches", 0.0254),
    "pitch": Argument(1, "meter", "inches", 0.0254),
    "height": Argument(1, "meter", "inches", 0.0254),
    "shaft_radius": Argument(1, "meter", "inches", 0.0254),
    "radial_clearance": Argument(1, "meter", "inches", 0.0254),
    "i_d": Argument(1, "meter", "inches", 0.0254),
    "o_d": Argument(1, "meter", "inches", 0.0254),
    "unbalance_magnitude": Argument(1, "kg*m", "lb*in", 0.011521246198000002),
    "unbalance_phase": Argument(1, "rad", "deg", 0.017453292519943295),
    "inlet_pressure": Argument(1, "pascal", "kgf/cm²", 98066.5),
    "outlet_pressure": Argument(1, "pascal", "kgf/cm²", 98066.5),
    "p": Argument(1, "pascal", "kgf/cm²", 98066.5),
    "inlet_temperature": Argument(1, "degK", "degC", 274.15),
    "T": Argument(1, "degK", "degC", 274.15),
    "inlet_swirl_velocity": Argument(1, "m/s", "ft/s", 0.3048),
    "pad_thickness": Argument(1, "meter", "inches", 0.0254),
    "kxx": Argument(1, "N/m", "lbf/in", 175.12683524647645),
    "kxy": Argument(1, "N/m", "lbf/in", 175.12683524647645),
    "kxz": Argument(1, "N/m", "lbf/in", 175.12683524647645),
    "kyx": Argument(1, "N/m", "lbf/in", 175.12683524647645),
    "kyy": Argument(1, "N/m", "lbf/in", 175.12683524647645),
    "kyz": Argument(1, "N/m", "lbf/in", 175.12683524647645),
    "kzx": Argument(1, "N/m", "lbf/in", 175.12683524647645),
    "kzy": Argument(1, "N/m", "lbf/in", 175.12683524647645),
    "kzz": Argument(1, "N/m", "lbf/in", 175.12683524647645),
    "cxx": Argument(1, "N*s/m", "lbf*s/in", 175.12683524647645),
    "cxy": Argument(1, "N*s/m", "lbf*s/in", 175.12683524647645),
    "cxz": Argument(1, "N*s/m", "lbf*s/in", 175.12683524647645),
    "cyx": Argument(1, "N*s/m", "lbf*s/in", 175.12683524647645),
    "cyy": Argument(1, "N*s/m", "lbf*s/in", 175.12683524647645),
    "cyz": Argument(1, "N*s/m", "lbf*s/in", 175.12683524647645),
    "czx": Argument(1, "N*s/m", "lbf*s/in", 175.12683524647645),
    "czy": Argument(1, "N*s/m", "lbf*s/in", 175.12683524647645),
    "czz": Argument(1, "N*s/m", "lbf*s/in", 175.12683524647645),
    "viscosity": Argument(1, "Pa*s", "lb/ft/s", 1.488164),
    "weight": Argument(1, "N", "lbf", 4.4482216152605005),
    "load": Argument(1, "N", "lbf", 4.4482216152605005),
    "force": Argument(1, "N", "lbf", 4.4482216152605005),
    "torque": Argument(1, "N*m", "lbf*ft", 1.3558179483314006),
    "flow_v": Argument(1, "m³/s", "ft³/h", 7.865791e-06),
    "flow_m": Argument(1, "kg/s", "lb/h", 0.0001259978805555556),
    "h": Argument(1, "joule/kilogram", "BTU/lb", 2326.000325),
    "s": Argument(1, "joule/(kelvin kilogram)", "BTU/(degF lb)", 4186.800585),
    "b": Argument(1, "meter", "inches", 0.0254),
    "D": Argument(1, "meter", "inches", 0.0254),
    "d": Argument(1, "meter", "inches", 0.0254),
    "roughness": Argument(1, "meter", "inches", 0.0254),
    "head": Argument(1, "joule/kg", "BTU/lb", 2326.0003),
    "eff": Argument(1, "dimensionless", "dimensionless", 1),
    "power": Argument(1, "watt", "hp", 745.699872),
}


@pytest.fixture
def auxiliary_function():
    @check_units
    def func(
        E,
        Gs,
        rho,
        L,
        idl,
        idr,
        odl,
        odr,
        speed,
        frequency,
        frequency_range,
        mx,
        my,
        Ip,
        Id,
        width,
        depth,
        pitch,
        height,
        shaft_radius,
        radial_clearance,
        i_d,
        o_d,
        unbalance_magnitude,
        unbalance_phase,
        inlet_pressure,
        outlet_pressure,
        p,
        inlet_temperature,
        T,
        inlet_swirl_velocity,
        pad_thickness,
        kxx,
        kxy,
        kxz,
        kyx,
        kyy,
        kyz,
        kzx,
        kzy,
        kzz,
        cxx,
        cxy,
        cxz,
        cyx,
        cyy,
        cyz,
        czx,
        czy,
        czz,
        viscosity,
        weight,
        load,
        force,
        torque,
        flow_v,
        flow_m,
        h,
        s,
        b,
        D,
        d,
        roughness,
        head,
        eff,
        power,
    ):
        return (
            E,
            Gs,
            rho,
            L,
            idl,
            idr,
            odl,
            odr,
            speed,
            frequency,
            frequency_range,
            mx,
            my,
            Ip,
            Id,
            width,
            depth,
            pitch,
            height,
            shaft_radius,
            radial_clearance,
            i_d,
            o_d,
            unbalance_magnitude,
            unbalance_phase,
            inlet_pressure,
            outlet_pressure,
            p,
            inlet_temperature,
            T,
            inlet_swirl_velocity,
            pad_thickness,
            kxx,
            kxy,
            kxz,
            kyx,
            kyy,
            kyz,
            kzx,
            kzy,
            kzz,
            cxx,
            cxy,
            cxz,
            cyx,
            cyy,
            cyz,
            czx,
            czy,
            czz,
            viscosity,
            weight,
            load,
            force,
            torque,
            flow_v,
            flow_m,
            h,
            s,
            b,
            D,
            d,
            roughness,
            head,
            eff,
            power,
        )

    return func


def test_units(auxiliary_function):
    results = auxiliary_function(**{k: v.single_value for k, v in arguments.items()})
    results_dict = {k: v for k, v in zip(arguments.keys(), results)}
    for arg, actual in results_dict.items():
        assert_allclose(actual, arguments[arg].single_value)


def test_unit_Q_(auxiliary_function):
    kwargs = {k: Q_(v.single_value, v.si_unit) for k, v in arguments.items()}
    results = auxiliary_function(**kwargs)
    results_dict = {k: v for k, v in zip(arguments.keys(), results)}
    for arg, actual in results_dict.items():
        assert_allclose(actual, arguments[arg].single_value)


def test_unit_Q_conversion(auxiliary_function):
    kwargs = {k: Q_(v.single_value, v.other_unit) for k, v in arguments.items()}
    results = auxiliary_function(**kwargs)
    results_dict = {k: v for k, v in zip(arguments.keys(), results)}
    for arg, actual in results_dict.items():
        assert_allclose(actual, arguments[arg].expected_converted_value)


# Water column pressure unit tests (for pint compatibility)
# These tests ensure backward compatibility across pint versions (< 0.24 and >= 0.24)
# See: https://github.com/hgrecco/pint/issues/2186
# See: /home/raphael/ccp/ccp/config/WATER_UNITS_README.md for details


def test_water_column_units_exist():
    """Test that all water column pressure units are available."""
    # Test all aliases for water column units
    units_to_test = [
        "meter_H2O",
        "mH2O",
        "centimeter_H2O",
        "cmH2O",
        "millimeter_H2O",
        "mmH2O",
    ]

    for unit_str in units_to_test:
        # Should not raise an exception
        q = Q_(1, unit_str)
        assert q is not None, f"Failed to create quantity with unit '{unit_str}'"


def test_water_column_units_to_pascal():
    """Test that water column units can be converted to pascal."""
    # Expected values based on conventional water density at 4°C
    # 1 meter of water = 9806.65 Pa
    test_cases = [
        ("meter_H2O", 1, 9806.65),
        ("mH2O", 1, 9806.65),
        ("centimeter_H2O", 1, 98.0665),
        ("cmH2O", 1, 98.0665),
        ("millimeter_H2O", 1, 9.80665),
        ("mmH2O", 1, 9.80665),
    ]

    for unit_str, value, expected_pascal in test_cases:
        q = Q_(value, unit_str)
        converted = q.to("pascal")
        assert_allclose(
            converted.magnitude,
            expected_pascal,
            rtol=1e-4,
            err_msg=f"Conversion failed for {unit_str}",
        )


def test_water_column_units_conversions():
    """Test conversions between different water column units."""
    # 1 meter = 100 centimeters = 1000 millimeters
    q_meter = Q_(1, "meter_H2O")
    q_cm = Q_(100, "centimeter_H2O")
    q_mm = Q_(1000, "millimeter_H2O")

    # Convert all to pascal and compare
    meter_to_pa = q_meter.to("pascal").magnitude
    cm_to_pa = q_cm.to("pascal").magnitude
    mm_to_pa = q_mm.to("pascal").magnitude

    assert_allclose(meter_to_pa, cm_to_pa, rtol=1e-4)
    assert_allclose(meter_to_pa, mm_to_pa, rtol=1e-4)


def test_water_column_aliases():
    """Test that all aliases for water column units are equivalent."""
    # Test meter_H2O aliases
    q1 = Q_(1, "meter_H2O")
    q2 = Q_(1, "mH2O")
    assert_allclose(q1.to("pascal").magnitude, q2.to("pascal").magnitude, rtol=1e-10)

    # Test centimeter_H2O aliases
    q3 = Q_(1, "centimeter_H2O")
    q4 = Q_(1, "cmH2O")
    assert_allclose(q3.to("pascal").magnitude, q4.to("pascal").magnitude, rtol=1e-10)

    # Test millimeter_H2O aliases
    q5 = Q_(1, "millimeter_H2O")
    q6 = Q_(1, "mmH2O")
    assert_allclose(q5.to("pascal").magnitude, q6.to("pascal").magnitude, rtol=1e-10)


def test_water_column_dimensionality():
    """Test that water column units have correct dimensionality (pressure)."""
    q = Q_(1, "meter_H2O")

    # Should be convertible to other pressure units
    pressure_units = ["pascal", "bar", "psi", "atm", "kPa"]

    for pressure_unit in pressure_units:
        try:
            converted = q.to(pressure_unit)
            assert converted is not None
        except Exception as e:
            pytest.fail(f"Failed to convert meter_H2O to {pressure_unit}: {e}")


def test_mH2O_is_pressure_not_density():
    """Test that mH2O is interpreted as meter_H2O (pressure), not milli-H2O (density).

    This is a critical test for pint compatibility. In older pint versions (< 0.24),
    H2O was defined as a density unit, so mH2O could be interpreted as "milliwater"
    (a density). Our legacy definitions ensure mH2O is always a pressure unit.
    """
    q = Q_(1, "mH2O")

    # Convert to pascal (pressure unit)
    try:
        converted = q.to("pascal")
        # Should succeed with the expected value for 1 meter of water
        assert_allclose(converted.magnitude, 9806.65, rtol=1e-4)
    except Exception as e:
        pytest.fail(
            f"mH2O should be convertible to pascal (pressure), but got error: {e}"
        )

    # Should NOT be convertible to kg/m³ (density)
    # If this succeeds, it means mH2O is being interpreted as a density unit (wrong!)
    try:
        q.to("kg/m**3")
        pytest.fail(
            "mH2O should NOT be convertible to kg/m³ (density). "
            "It should be a pressure unit (meter_H2O)."
        )
    except Exception:
        # Expected to fail - mH2O should be pressure, not density
        pass


def test_water_column_units_no_recursion():
    """Test that water column unit conversions don't cause recursion errors.

    This test ensures that the fix for pint >= 0.24 is working correctly.
    In pint >= 0.24, redefining existing water column units caused circular
    references and RecursionError. This test verifies the fix.
    """
    try:
        # These operations would cause RecursionError if the fix isn't working
        q1 = Q_(1, "meter_H2O")
        q1.to("pascal")

        q2 = Q_(1, "mH2O")
        q2.to("pascal")

        q3 = Q_(100, "cmH2O")
        q3.to("bar")

        # If we get here, no recursion error occurred
        assert True
    except RecursionError as e:
        pytest.fail(f"RecursionError occurred during water column unit conversion: {e}")


def test_h_alias_for_hour():
    """Test that 'h' alias works correctly for hour and doesn't conflict with water units.

    The 'h' alias should represent 'hour', not Planck's constant.
    This is important because water column units like 'mH2O' contain 'h' in their name,
    and we need to ensure there's no parsing conflict.
    """
    # Test that h is hour
    h_unit = Q_(1, "h")
    assert_allclose(h_unit.to("second").magnitude, 3600, rtol=1e-10)
    assert_allclose(h_unit.to("minute").magnitude, 60, rtol=1e-10)

    # Test velocity with h (m/h should work)
    velocity = Q_(3600, "m/h")
    assert_allclose(velocity.to("m/s").magnitude, 1.0, rtol=1e-10)

    # Test that h doesn't interfere with water column units
    # mH2O should be parsed as meter_H2O, not as m*h*2*O
    water_pressure = Q_(1, "mH2O")
    assert_allclose(water_pressure.to("pascal").magnitude, 9806.65, rtol=1e-4)

    # Verify h has time dimensionality, not other dimensions
    h_dimensionality = h_unit.dimensionality
    # Should be [time] dimension
    assert "[time]" in str(h_dimensionality)


def test_h_alias_not_planck():
    """Test that 'h' is hour, not Planck's constant.

    This ensures the custom unit definition overrides any default
    interpretation of 'h' as Planck's constant.
    """
    h_unit = Q_(1, "h")

    # Should be convertible to time units
    try:
        h_unit.to("second")
        h_unit.to("minute")
        h_unit.to("hour")
    except Exception as e:
        pytest.fail(f"'h' should be convertible to time units: {e}")

    # Should NOT be Planck's constant (which has action/angular momentum dimensions)
    # If h were Planck's constant, it would have dimensions of energy*time or J*s
    try:
        h_unit.to("J*s")  # Planck constant units
        pytest.fail("'h' should NOT be convertible to J*s (Planck's constant units)")
    except Exception:
        # Expected - h should be time, not action
        pass
