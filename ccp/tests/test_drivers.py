import pytest
from numpy.testing import assert_allclose

from ccp import Q_
from ccp.drivers import InductionMotor, MotorEstimate, PowerComparison
from ccp.point import Point
from ccp.state import State


@pytest.fixture
def motor():
    """DOE fact sheet example: 40 hp, 1800 rpm class motor."""
    return InductionMotor(
        rated_power=Q_(40, "hp"),
        rated_voltage=Q_(460, "volt"),
        rated_current=Q_(46, "ampere"),
        rated_speed=Q_(1780, "rpm"),
        rated_frequency=Q_(60, "Hz"),
        rated_power_factor=0.86,
        efficiency=0.93,
    )


@pytest.fixture
def motor_other_units():
    return InductionMotor(
        rated_power=Q_(29828.0, "W"),
        rated_voltage=Q_(0.460, "kV"),
        rated_current=Q_(46, "ampere"),
        rated_speed=Q_(186.4158, "rad/s"),
        rated_frequency=Q_(60, "Hz"),
        rated_power_factor=0.86,
        efficiency=Q_(93, "percent"),
    )


@pytest.fixture
def motor_si_floats():
    return InductionMotor(
        rated_power=29828.0,
        rated_voltage=460.0,
        rated_current=46.0,
        rated_speed=186.4158,
        rated_frequency=60.0,
        rated_power_factor=0.86,
        efficiency=0.93,
    )


@pytest.fixture
def motor_slip():
    """DOE fact sheet slip example: 25 hp, sync 1800 rpm, rated 1750 rpm."""
    return InductionMotor(
        rated_power=Q_(25, "hp"),
        rated_voltage=Q_(460, "volt"),
        rated_speed=Q_(1750, "rpm"),
        rated_frequency=Q_(60, "Hz"),
    )


def test_input_power_doe_example(motor):
    # DOE fact sheet: 469.7 V, 37 A, PF 0.763 -> 22.9 kW
    input_power = motor.input_power(voltage=469.7, current=37, power_factor=0.763)
    assert_allclose(input_power.to("kW").m, 22.9672, rtol=1e-4)


def test_input_power_method(motor):
    estimate = motor.estimate(voltage=469.7, current=37, power_factor=0.763)
    assert estimate.method == "input_power"
    assert_allclose(estimate.power_output.m, 22967.1681 * 0.93, rtol=1e-4)
    assert_allclose(estimate.load.m, 0.71608, rtol=1e-4)
    assert_allclose(estimate.efficiency.m, 0.93)
    # direct power measurement gives the same result
    estimate_direct = motor.estimate(input_power=Q_(22.9671681, "kW"))
    assert_allclose(estimate_direct.power_output.m, estimate.power_output.m, rtol=1e-6)


def test_units_variants(motor, motor_other_units, motor_si_floats):
    measurements = dict(voltage=469.7, current=37, power_factor=0.763)
    reference = motor.estimate(**measurements)
    for m in [motor_other_units, motor_si_floats]:
        estimate = m.estimate(**measurements)
        assert_allclose(estimate.power_output.m, reference.power_output.m, rtol=1e-4)
        assert_allclose(estimate.load.m, reference.load.m, rtol=1e-4)
    # measurement units are also converted
    estimate_kv = motor.estimate(
        voltage=Q_(0.4697, "kV"), current=37, power_factor=0.763
    )
    assert_allclose(estimate_kv.power_output.m, reference.power_output.m)


def test_power_factor_not_converted_to_watt(motor):
    # regression: "rated_power_factor"/"power_factor" must resolve to
    # dimensionless in check_units, not match the "power" token -> watt
    assert motor.rated_power_factor.units == Q_(1, "dimensionless").units
    estimate = motor.estimate(
        voltage=469.7, current=37, power_factor=Q_(0.763, "dimensionless")
    )
    assert_allclose(estimate.load.m, 0.71608, rtol=1e-4)


def test_current_method(motor):
    estimate = motor.estimate(current=37, voltage=469.7, method="current")
    assert estimate.method == "current"
    assert_allclose(estimate.load.m, (37 / 46) * (469.7 / 460), rtol=1e-6)
    assert_allclose(estimate.power_output.to("hp").m, 32.8524, rtol=1e-4)
    assert estimate.efficiency is None
    # without voltage compensation
    estimate_no_v = motor.estimate(current=37, method="current")
    assert_allclose(estimate_no_v.load.m, 37 / 46, rtol=1e-6)


def test_current_method_low_load_warns(motor):
    with pytest.warns(UserWarning, match="unreliable below 50%"):
        motor.estimate(current=20, method="current")


def test_slip_method_doe_example(motor_slip):
    # sync 1800, rated 1750, measured 1770 rpm -> load 60% -> 15 hp
    assert motor_slip.poles == 4
    assert_allclose(motor_slip.synchronous_speed().to("rpm").m, 1800)
    estimate = motor_slip.estimate(speed=Q_(1770, "rpm"))
    assert estimate.method == "slip"
    assert_allclose(estimate.load.m, 0.6, rtol=1e-6)
    assert_allclose(estimate.power_output.to("hp").m, 15.0, rtol=1e-6)


def test_slip_method_voltage_compensated(motor_slip):
    estimate = motor_slip.estimate(speed=Q_(1770, "rpm"), voltage=450.8)
    assert_allclose(estimate.load.m, 0.6 * (450.8 / 460) ** 2, rtol=1e-6)


def test_slip_method_vfd(motor_slip):
    # 45 Hz: sync 1350 rpm, measured 1320 rpm -> load 60%,
    # power scaled by 45/60 -> 11.25 hp
    estimate = motor_slip.estimate(speed=Q_(1320, "rpm"), supply_frequency=Q_(45, "Hz"))
    assert_allclose(estimate.load.m, 0.6, rtol=1e-6)
    assert_allclose(estimate.power_output.to("hp").m, 11.25, rtol=1e-6)
    assert_allclose(estimate.power_output.m, 8389.12, rtol=1e-4)


def test_vfd_efficiency():
    motor = InductionMotor(
        rated_power=Q_(40, "hp"),
        efficiency=0.93,
        vfd_efficiency=0.97,
    )
    estimate = motor.estimate(input_power=Q_(22.9671681, "kW"))
    assert_allclose(estimate.power_output.m, 22967.1681 * 0.97 * 0.93, rtol=1e-6)


def test_efficiency_curve_iteration():
    motor = InductionMotor(
        rated_power=Q_(40, "hp"),
        efficiency_curve=[
            [0.25, 0.894],
            [0.50, 0.925],
            [0.75, 0.936],
            [1.00, 0.930],
        ],
    )
    input_power = Q_(22.9671681, "kW")
    estimate = motor.estimate(input_power=input_power)
    # self-consistency: load, efficiency and input power must close
    assert_allclose(
        estimate.load.m,
        (input_power * estimate.efficiency / motor.rated_power).to("dimensionless").m,
        atol=1e-6,
    )
    assert_allclose(
        estimate.efficiency.m,
        motor.efficiency_at_load(estimate.load.m).m,
        atol=1e-6,
    )
    # at ~77% load the interpolated efficiency is above the full-load value
    assert estimate.efficiency.m > 0.930


def test_efficiency_at_load_clamped():
    motor = InductionMotor(
        rated_power=Q_(40, "hp"),
        efficiency_curve=[[0.25, 0.894], [0.50, 0.925], [1.00, 0.930]],
    )
    assert_allclose(motor.efficiency_at_load(0.1).m, 0.894)
    assert_allclose(motor.efficiency_at_load(1.2).m, 0.930)


def test_efficiency_and_curve_raises():
    with pytest.raises(ValueError, match="either efficiency or efficiency_curve"):
        InductionMotor(
            rated_power=Q_(40, "hp"),
            efficiency=0.93,
            efficiency_curve=[[0.5, 0.925], [1.0, 0.93]],
        )


def test_method_auto_selection(motor_slip):
    # speed only -> slip; current only -> current
    assert motor_slip.estimate(speed=Q_(1770, "rpm")).method == "slip"
    motor_current = InductionMotor(
        rated_power=Q_(25, "hp"), rated_current=Q_(30, "ampere")
    )
    assert motor_current.estimate(current=25).method == "current"


def test_insufficient_measurements_raises(motor):
    with pytest.raises(ValueError, match="Insufficient measurements"):
        motor.estimate()
    with pytest.raises(ValueError, match="Unknown method"):
        motor.estimate(current=37, method="torque")


def test_poles_derivation():
    for rpm, expected_poles in [(1780, 4), (3550, 2), (1180, 6), (880, 8)]:
        motor = InductionMotor(
            rated_power=Q_(40, "hp"),
            rated_speed=Q_(rpm, "rpm"),
            rated_frequency=Q_(60, "Hz"),
        )
        assert motor.poles == expected_poles


def test_save_load_roundtrip(motor, tmp_path):
    for file_name in ["motor.toml", "motor.json"]:
        file = tmp_path / file_name
        motor.save(file)
        motor_loaded = InductionMotor.load(file)
        assert_allclose(motor_loaded.rated_power.m, motor.rated_power.m)
        assert_allclose(motor_loaded.rated_voltage.m, motor.rated_voltage.m)
        assert_allclose(motor_loaded.rated_speed.m, motor.rated_speed.m)
        assert_allclose(motor_loaded.efficiency.m, motor.efficiency.m)
        assert motor_loaded.poles == motor.poles
        estimate = motor_loaded.estimate(voltage=469.7, current=37, power_factor=0.763)
        assert_allclose(estimate.load.m, 0.71608, rtol=1e-4)


def test_save_load_efficiency_curve(tmp_path):
    motor = InductionMotor(
        rated_power=Q_(40, "hp"),
        efficiency_curve=[[0.25, 0.894], [0.50, 0.925], [1.00, 0.930]],
    )
    file = tmp_path / "motor.toml"
    motor.save(file)
    motor_loaded = InductionMotor.load(file)
    assert_allclose(motor_loaded.efficiency_curve, motor.efficiency_curve)


@pytest.fixture
def point_0():
    fluid = dict(CarbonDioxide=0.76064, Nitrogen=0.23581, Oxygen=0.00284)
    suc = State(p=Q_(1.839, "bar"), T=291.5, fluid=fluid)
    disch = State(p=Q_(5.902, "bar"), T=405.7, fluid=fluid)
    return Point(suc=suc, disch=disch, flow_v=1, speed=1, b=1, D=1)


def test_compare_with_point(point_0):
    # motor sized so that measurements give a driver power near the point's
    # shaft power (~319.2 kW gas power, zero mechanical losses)
    motor = InductionMotor(
        rated_power=Q_(400, "kW"),
        rated_voltage=Q_(4160, "volt"),
        rated_current=Q_(60, "ampere"),
        efficiency=0.95,
    )
    comparison = motor.compare(
        point_0,
        coupling_efficiency=0.98,
        gearbox_efficiency=0.97,
        input_power=Q_(350, "kW"),
    )
    assert isinstance(comparison, PowerComparison)
    driver_power = 350e3 * 0.95
    transmitted_power = driver_power * 0.98 * 0.97
    assert_allclose(comparison.driver_power.m, driver_power)
    assert_allclose(comparison.transmitted_power.m, transmitted_power)
    assert_allclose(comparison.point_power.m, point_0.power_shaft.m)
    assert_allclose(
        comparison.delta.m, transmitted_power - point_0.power_shaft.m, rtol=1e-6
    )
    assert_allclose(
        comparison.delta_ratio.m,
        (transmitted_power - point_0.power_shaft.m) / point_0.power_shaft.m,
        rtol=1e-6,
    )
    assert comparison.method == "input_power"


def test_estimate_repr(motor):
    estimate = motor.estimate(voltage=469.7, current=37, power_factor=0.763)
    assert isinstance(estimate, MotorEstimate)
    assert "input_power" in str(estimate)
    assert "22.97 kW" in str(estimate)
