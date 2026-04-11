"""Smoke tests for :mod:`apps.core.services.ccp_service`."""

import ccp
import pytest

from apps.core.services import ccp_service


@pytest.fixture
def simple_composition():
    return {"methane": 0.9, "ethane": 0.1}


def test_build_gas_state(simple_composition):
    state = ccp_service.build_gas_state(
        simple_composition, p=ccp.Q_(1.0, "bar"), T=ccp.Q_(300.0, "degK")
    )
    assert isinstance(state, ccp.State)
    assert pytest.approx(state.p().to("bar").m, rel=1e-6) == 1.0


def test_build_gas_state_rejects_empty_composition():
    with pytest.raises(ValueError):
        ccp_service.build_gas_state({}, p=ccp.Q_(1, "bar"), T=ccp.Q_(300, "degK"))


def test_polytropic_method_applied_via_wrapper(simple_composition):
    original = ccp.config.POLYTROPIC_METHOD
    try:
        ccp_service._apply_polytropic_method("Huntington")
        assert ccp.config.POLYTROPIC_METHOD == "huntington"
        ccp_service._apply_polytropic_method("mallen_saville")
        assert ccp.config.POLYTROPIC_METHOD == "mallen_saville"
        ccp_service._apply_polytropic_method(None)
        assert ccp.config.POLYTROPIC_METHOD == "mallen_saville"
    finally:
        ccp.config.POLYTROPIC_METHOD = original


def test_polytropic_methods_returns_dict():
    mapping = ccp_service.polytropic_methods()
    assert "Schultz" in mapping
    assert mapping["Schultz"] == "schultz"


def test_build_point_1sec_forwards_kwargs(simple_composition):
    suc = ccp_service.build_gas_state(
        simple_composition, p=ccp.Q_(1.826, "bar"), T=ccp.Q_(296.7, "degK")
    )
    disch = ccp_service.build_gas_state(
        simple_composition, p=ccp.Q_(6.142, "bar"), T=ccp.Q_(392.1, "degK")
    )
    point = ccp_service.build_point_1sec(
        flow_m=ccp.Q_(7.737, "kg/s"),
        speed=ccp.Q_(7894, "RPM"),
        b=ccp.Q_(28.5, "mm"),
        D=ccp.Q_(365, "mm"),
        suc=suc,
        disch=disch,
        balance_line_flow_m=ccp.Q_(0.1076, "kg/s"),
        seal_gas_flow_m=ccp.Q_(0.04982, "kg/s"),
        seal_gas_temperature=ccp.Q_(297.7, "degK"),
        oil_flow_journal_bearing_de=ccp.Q_(27.084, "l/min"),
        oil_flow_journal_bearing_nde=ccp.Q_(47.984, "l/min"),
        oil_flow_thrust_bearing_nde=ccp.Q_(33.52, "l/min"),
        oil_inlet_temperature=ccp.Q_(42.184, "degC"),
        oil_outlet_temperature_de=ccp.Q_(48.111, "degC"),
        oil_outlet_temperature_nde=ccp.Q_(46.879, "degC"),
        oil_specific_heat_de=ccp.Q_(2.02, "kJ/kg/degK"),
        oil_specific_heat_nde=ccp.Q_(2.02, "kJ/kg/degK"),
        oil_density_de=ccp.Q_(846.9, "kg/m³"),
        oil_density_nde=ccp.Q_(846.9, "kg/m³"),
        casing_area=7.5,
        casing_temperature=ccp.Q_(31.309, "degC"),
        ambient_temperature=ccp.Q_(0, "degC"),
        polytropic_method="Schultz",
    )
    assert isinstance(point, ccp.compressor.Point1Sec)
    assert ccp.config.POLYTROPIC_METHOD == "schultz"


def test_service_package_importable():
    from apps.core import services

    assert hasattr(services, "ccp_service")
    assert hasattr(services, "gas_composition")
    assert hasattr(services, "parameter_map")
    assert hasattr(services, "unit_helpers")
    assert hasattr(services, "polytropic_methods")
