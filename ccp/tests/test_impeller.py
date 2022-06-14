import pytest
import numpy as np
import pickle
from pathlib import Path
from tempfile import tempdir
from numpy.testing import assert_allclose

import ccp
from ccp import ureg, Q_, State, Point, Curve, Impeller, impeller_example


@pytest.fixture
def points0():
    #  see Ludtke pg. 173 for values.
    fluid = dict(
        n2=0.0318,
        co2=0.0118,
        methane=0.8737,
        ethane=0.0545,
        propane=0.0178,
        ibutane=0.0032,
        nbutane=0.0045,
        ipentane=0.0011,
        npentane=0.0009,
        nhexane=0.0007,
    )
    suc = State.define(p=Q_(62.7, "bar"), T=Q_(31.2, "degC"), fluid=fluid)
    disch = State.define(p=Q_(76.82, "bar"), T=Q_(48.2, "degC"), fluid=fluid)
    disch1 = State.define(p=Q_(76.0, "bar"), T=Q_(48.0, "degC"), fluid=fluid)
    p0 = Point(
        suc=suc,
        disch=disch,
        flow_m=85.9,
        speed=Q_(13971, "RPM"),
        b=Q_(44.2, "mm"),
        D=0.318,
    )
    p1 = Point(
        suc=suc,
        disch=disch1,
        flow_m=86.9,
        speed=Q_(13971, "RPM"),
        b=Q_(44.2, "mm"),
        D=0.318,
    )
    return p0, p1


@pytest.fixture
def imp0(points0):
    p0, p1 = points0
    imp0 = Impeller([p0, p1])
    return imp0


@pytest.fixture
def imp1():
    fluid = dict(
        methane=0.69945,
        ethane=0.09729,
        propane=0.0557,
        nbutane=0.0178,
        ibutane=0.0102,
        npentane=0.0039,
        ipentane=0.0036,
        nhexane=0.0018,
        n2=0.0149,
        co2=0.09259,
        h2s=0.00017,
        water=0.002,
    )
    suc = State.define(p=Q_(1.6995, "MPa"), T=311.55, fluid=fluid)

    p0 = Point(
        suc=suc,
        flow_v=Q_(6501.67, "m**3/h"),
        speed=Q_(11145, "RPM"),
        head=Q_(179.275, "kJ/kg"),
        eff=0.826357,
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
    )
    p1 = Point(
        suc=suc,
        flow_v=Q_(7016.72, "m**3/h"),
        speed=Q_(11145, "RPM"),
        head=Q_(173.057, "kJ/kg"),
        eff=0.834625,
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
    )

    imp1 = Impeller([p0, p1])

    return imp1


def test_impeller_new_suction(imp1):
    new_suc = State.define(
        p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15}
    )
    imp2 = Impeller.convert_from(imp1, suc=new_suc, find="speed")
    p0 = imp1[0]
    new_p0 = imp2[0]

    assert_allclose(new_p0.eff, p0.eff, rtol=1e-4)
    assert_allclose(new_p0.phi, p0.phi, rtol=1e-2)
    assert_allclose(new_p0.psi, p0.psi, rtol=1e-2)
    assert_allclose(new_p0.head, 208933.668804, rtol=1e-2)
    assert_allclose(new_p0.power, 1101698.5104, rtol=1e-2)
    assert_allclose(new_p0.speed, 1257.17922, rtol=1e-3)


@pytest.fixture()
def imp2():
    points = [
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1263 rad/s"),
            flow_v=Q_("1.15 m³/s"),
            head=Q_("147634 J/kg"),
            eff=Q_("0.819"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1263 rad/s"),
            flow_v=Q_("1.26 m³/s"),
            head=Q_("144664 J/kg"),
            eff=Q_("0.829"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1263 rad/s"),
            flow_v=Q_("1.36 m³/s"),
            head=Q_("139945 J/kg"),
            eff=Q_("0.831"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1337 rad/s"),
            flow_v=Q_("1.22 m³/s"),
            head=Q_("166686 J/kg"),
            eff=Q_("0.814"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1337 rad/s"),
            flow_v=Q_("1.35 m³/s"),
            head=Q_("163620 J/kg"),
            eff=Q_("0.825"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State.define(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1337 rad/s"),
            flow_v=Q_("1.48 m³/s"),
            head=Q_("158536 J/kg"),
            eff=Q_("0.830"),
            b=0.010745,
            D=0.32560,
        ),
    ]

    imp2 = Impeller(points)

    return imp2


def test_impeller_disch_state(imp2):
    T_magnitude = np.array(
        [[482.850310, 477.243856, 471.29533], [506.668177, 500.418404, 493.30993]]
    )
    assert_allclose(
        imp2.disch.T().magnitude,
        T_magnitude,
    )


def test_impeller2_new_suction(imp2):
    new_suc = State.define(
        p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15}
    )
    imp2_new = Impeller.convert_from(imp2, suc=new_suc, find="speed")
    p0 = imp2[0]
    new_p0 = imp2_new[0]

    assert_allclose(new_p0.eff, p0.eff, rtol=1e-4)
    assert_allclose(new_p0.phi, p0.phi, rtol=1e-2)
    assert_allclose(new_p0.psi, p0.psi, rtol=1e-2)
    assert_allclose(new_p0.head, 151889.637082, rtol=1e-2)
    assert_allclose(new_p0.power, 483519.884306, rtol=1e-2)
    assert_allclose(new_p0.speed, 1281.074036, rtol=1e-3)
    assert_allclose(new_p0.mach_diff, -7.12032e-05, rtol=1e-3)
    assert_allclose(new_p0.reynolds_ratio, 0.999879, rtol=1e-3)
    assert_allclose(new_p0.volume_ratio_ratio, 0.999815, rtol=1e-5)


@pytest.fixture
def imp3():
    # faster to load than impeller_example
    composition_fd = dict(
        n2=0.4,
        co2=0.22,
        methane=92.11,
        ethane=4.94,
        propane=1.71,
        ibutane=0.24,
        butane=0.3,
        ipentane=0.04,
        pentane=0.03,
        hexane=0.01,
    )
    suc_fd = State.define(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)

    test_dir = Path(__file__).parent
    curve_path = test_dir / "data"
    curve_name = "normal"

    imp3 = Impeller.load_from_engauge_csv(
        suc=suc_fd,
        curve_name=curve_name,
        curve_path=curve_path,
        b=Q_(10.6, "mm"),
        D=Q_(390, "mm"),
        number_of_points=6,
        flow_units="kg/h",
        head_units="kJ/kg",
    )
    return imp3


def test_impeller_point(imp3):
    p0 = imp3.point(flow_m=Q_(90184, "kg/h"), speed=Q_(9300, "RPM"))
    assert_allclose(p0.eff, 0.782169, rtol=1e-4)
    assert_allclose(p0.head, 97729.49349, rtol=1e-4)
    assert_allclose(p0.power, 3130330.074989, rtol=1e-4)

    # test interpolation warning
    with pytest.warns(UserWarning) as record:
        p0 = imp3.point(flow_m=Q_(70000, "kg/h"), speed=Q_(9300, "RPM"))
        assert "Expected point is being extrapolated" in record[0].message.args[0]


def test_impeller_curve():
    imp = impeller_example()
    c0 = imp.curve(speed=900)
    p0 = c0[0]
    assert_allclose(p0.eff, 0.821433, rtol=1e-4)
    assert_allclose(p0.head, 137188.459805, rtol=1e-4)
    assert_allclose(p0.power, 2959311.563661, rtol=1e-4)


def test_impeller_plot():
    imp = impeller_example()
    fig = imp.eff_plot(flow_v=5, speed=900)
    expected_eff_curve = np.array(
        [
            0.82143291,
            0.82249497,
            0.82336864,
            0.82405925,
            0.82457212,
            0.82491257,
            0.82508593,
            0.82509751,
            0.82495263,
            0.82465663,
            0.82421449,
            0.82361161,
            0.82280301,
            0.82174109,
            0.82037827,
            0.81867002,
            0.81664285,
            0.81439426,
            0.81202483,
            0.80963514,
            0.80729315,
            0.80468743,
            0.80126177,
            0.79645593,
            0.78970962,
            0.78046257,
            0.76815452,
            0.75222518,
            0.7321143,
            0.70726161,
        ]
    )
    assert_allclose(fig.data[5]["y"], expected_eff_curve, rtol=1e-4)
    assert_allclose(fig.data[6]["y"], 0.8160188823236803, rtol=1e-4)


def test_impeller_plot_units():
    imp = impeller_example()
    fig = imp.disch.rho_plot(
        flow_v=Q_(20000, "m³/h"),
        speed=Q_(8594, "RPM"),
        flow_v_units="m³/h",
        speed_units="RPM",
        rho_units="g/cm³",
    )
    expected_rho_curve = np.array(
        [
            0.01104846,
            0.01102079,
            0.01099214,
            0.01096187,
            0.01092935,
            0.01089396,
            0.01085506,
            0.01081202,
            0.01076421,
            0.010711,
            0.01065176,
            0.01058655,
            0.01051647,
            0.0104427,
            0.01036643,
            0.01028881,
            0.01021025,
            0.01013039,
            0.01004887,
            0.00996531,
            0.00987906,
            0.00978643,
            0.00968174,
            0.00955929,
            0.00941338,
            0.00923831,
            0.00902836,
            0.00877783,
            0.00848102,
            0.00813222,
        ]
    )
    assert_allclose(fig.data[5]["y"], expected_rho_curve, rtol=1e-4)
    assert_allclose(fig.data[6]["y"], 0.008981, rtol=1e-4)


def test_save_load():
    composition_fd = dict(
        n2=0.4,
        co2=0.22,
        methane=92.11,
        ethane=4.94,
        propane=1.71,
        ibutane=0.24,
        butane=0.3,
        ipentane=0.04,
        pentane=0.03,
        hexane=0.01,
    )
    suc_fd = State.define(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)

    test_dir = Path(__file__).parent
    curve_path = test_dir / "data"
    curve_name = "normal"

    imp_fd = Impeller.load_from_engauge_csv(
        suc=suc_fd,
        curve_name=curve_name,
        curve_path=curve_path,
        b=Q_(10.6, "mm"),
        D=Q_(390, "mm"),
        number_of_points=6,
        flow_units="kg/h",
        head_units="kJ/kg",
    )
    file = Path(tempdir) / "imp.toml"
    imp_fd.save(file)

    imp_fd_loaded = Impeller.load(file)

    assert imp_fd == imp_fd_loaded


def test_load_from_dict_isis():
    head_curves_dict = {
        "CURVES": [
            {
                "z": 11373,
                "points": [
                    {"x": 94529, "y": 148.586},
                    {"x": 98641, "y": 148.211},
                    {"x": 101554, "y": 147.837},
                    {"x": 105837, "y": 147.463},
                    {"x": 110120, "y": 145.967},
                    {"x": 114230, "y": 144.097},
                    {"x": 118167, "y": 141.479},
                    {"x": 130152, "y": 134.001},
                    {"x": 134089, "y": 131.384},
                    {"x": 138026, "y": 128.393},
                    {"x": 140080, "y": 126.523},
                    {"x": 144016, "y": 123.158},
                    {"x": 150177, "y": 117.176},
                    {"x": 153942, "y": 113.811},
                    {"x": 157705, "y": 109.698},
                    {"x": 160100, "y": 106.708},
                    {"x": 163693, "y": 102.595},
                    {"x": 167113, "y": 97.735},
                    {"x": 170190, "y": 92.875},
                    {"x": 173609, "y": 87.641},
                    {"x": 177200, "y": 82.407},
                ],
            },
            {
                "z": 10463,
                "points": [
                    {"x": 86421, "y": 126.284},
                    {"x": 90209, "y": 125.784},
                    {"x": 94492, "y": 125.036},
                    {"x": 98604, "y": 124.661},
                    {"x": 100146, "y": 124.287},
                    {"x": 104256, "y": 122.417},
                    {"x": 110077, "y": 118.678},
                    {"x": 114187, "y": 116.435},
                    {"x": 118125, "y": 114.191},
                    {"x": 122063, "y": 111.948},
                    {"x": 126172, "y": 109.33},
                    {"x": 130109, "y": 106.339},
                    {"x": 134045, "y": 102.974},
                    {"x": 137639, "y": 99.609},
                    {"x": 140206, "y": 97.366},
                    {"x": 143971, "y": 94.001},
                    {"x": 147907, "y": 89.888},
                    {"x": 150130, "y": 87.271},
                    {"x": 153722, "y": 82.411},
                    {"x": 156458, "y": 78.672},
                    {"x": 160049, "y": 73.812},
                    {"x": 163469, "y": 68.952},
                ],
            },
            {
                "z": 9300,
                "points": [
                    {"x": 76859, "y": 100.028},
                    {"x": 81085, "y": 99.245},
                    {"x": 85368, "y": 98.497},
                    {"x": 89309, "y": 98.122},
                    {"x": 90166, "y": 97.748},
                    {"x": 94276, "y": 96.252},
                    {"x": 98386, "y": 94.009},
                    {"x": 102152, "y": 91.765},
                    {"x": 106262, "y": 89.522},
                    {"x": 110200, "y": 87.278},
                    {"x": 114310, "y": 85.035},
                    {"x": 118075, "y": 82.043},
                    {"x": 122184, "y": 79.052},
                    {"x": 126121, "y": 76.061},
                    {"x": 130056, "y": 72.322},
                    {"x": 133821, "y": 68.584},
                    {"x": 137241, "y": 64.097},
                    {"x": 141860, "y": 58.863},
                ],
            },
        ]
    }

    eff_curves_dict = {
        "CURVES": [
            {
                "z": 11373,
                "points": [
                    {"x": 94088, "y": 0.7515},
                    {"x": 97345, "y": 0.757113},
                    {"x": 104205, "y": 0.771707},
                    {"x": 107462, "y": 0.777695},
                    {"x": 110718, "y": 0.78256},
                    {"x": 114315, "y": 0.786678},
                    {"x": 117570, "y": 0.789673},
                    {"x": 121508, "y": 0.792669},
                    {"x": 134869, "y": 0.805772},
                    {"x": 138805, "y": 0.806898},
                    {"x": 142741, "y": 0.806527},
                    {"x": 145648, "y": 0.805033},
                    {"x": 149581, "y": 0.802044},
                    {"x": 150094, "y": 0.80167},
                    {"x": 153854, "y": 0.797933},
                    {"x": 157443, "y": 0.793073},
                    {"x": 160005, "y": 0.788213},
                    {"x": 162907, "y": 0.781856},
                    {"x": 165295, "y": 0.774377},
                    {"x": 167001, "y": 0.768768},
                    {"x": 169046, "y": 0.76054},
                    {"x": 172792, "y": 0.742214},
                    {"x": 174494, "y": 0.733613},
                    {"x": 177637, "y": 0.717055},
                ],
            },
            {
                "z": 10463,
                "points": [
                    {"x": 86559, "y": 0.751493},
                    {"x": 89817, "y": 0.757855},
                    {"x": 92732, "y": 0.764216},
                    {"x": 95820, "y": 0.7717},
                    {"x": 98735, "y": 0.777688},
                    {"x": 100449, "y": 0.780681},
                    {"x": 104047, "y": 0.785547},
                    {"x": 107815, "y": 0.788917},
                    {"x": 113125, "y": 0.793784},
                    {"x": 116894, "y": 0.797902},
                    {"x": 122375, "y": 0.803517},
                    {"x": 126484, "y": 0.805765},
                    {"x": 130591, "y": 0.806143},
                    {"x": 135295, "y": 0.804089},
                    {"x": 137945, "y": 0.801847},
                    {"x": 139654, "y": 0.800165},
                    {"x": 143243, "y": 0.79568},
                    {"x": 147000, "y": 0.788576},
                    {"x": 149903, "y": 0.781845},
                    {"x": 152120, "y": 0.774366},
                    {"x": 154761, "y": 0.763521},
                    {"x": 157570, "y": 0.749683},
                    {"x": 159016, "y": 0.740894},
                    {"x": 163440, "y": 0.716584},
                ],
            },
            {
                "z": 9300,
                "points": [
                    {"x": 76977, "y": 0.751485},
                    {"x": 79892, "y": 0.757847},
                    {"x": 80235, "y": 0.758595},
                    {"x": 82809, "y": 0.765704},
                    {"x": 85211, "y": 0.771691},
                    {"x": 87955, "y": 0.778427},
                    {"x": 90184, "y": 0.782169},
                    {"x": 93782, "y": 0.786661},
                    {"x": 97550, "y": 0.790404},
                    {"x": 101319, "y": 0.794522},
                    {"x": 104746, "y": 0.799388},
                    {"x": 110228, "y": 0.805751},
                    {"x": 114336, "y": 0.806877},
                    {"x": 118441, "y": 0.805384},
                    {"x": 124083, "y": 0.800339},
                    {"x": 127500, "y": 0.795105},
                    {"x": 132110, "y": 0.78501},
                    {"x": 136884, "y": 0.767994},
                    {"x": 138586, "y": 0.759392},
                    {"x": 140456, "y": 0.747424},
                    {"x": 141816, "y": 0.738448},
                    {"x": 145226, "y": 0.716758},
                ],
            },
        ]
    }

    composition_fd = dict(
        n2=0.4,
        co2=0.22,
        methane=92.11,
        ethane=4.94,
        propane=1.71,
        ibutane=0.24,
        butane=0.3,
        ipentane=0.04,
        pentane=0.03,
        hexane=0.01,
    )
    suc_fd = State.define(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)

    imp = ccp.Impeller.load_from_dict_isis(
        suc=suc_fd,
        head_curves=head_curves_dict,
        eff_curves=eff_curves_dict,
        b=Q_(10.6, "mm"),
        D=Q_(390, "mm"),
        number_of_points=6,
        flow_units="kg/h",
        head_units="kJ/kg",
    )
    p0 = imp.point(flow_m=Q_(90184, "kg/h"), speed=Q_(9300, "RPM"))
    assert_allclose(p0.eff, 0.782169, rtol=1e-4)
    assert_allclose(p0.head, 97729.49349, rtol=1e-4)
    assert_allclose(p0.power, 3130330.074989, rtol=1e-4)


def test_pickle(imp0):
    pickled_imp0 = pickle.loads(pickle.dumps(imp0))
    assert pickled_imp0 == imp0
    assert hasattr(imp0, "head_plot") is True
    assert hasattr(pickled_imp0, "head_plot") is True


def test_interpolation_warning():
    eff_curve = {
        1000: {
            "x": [
                9.1937,
                9.5582,
                10.4576,
                11.4588,
                12.7945,
                13.9998,
                14.8382,
                15.3756,
                15.4093,
                15.712,
                15.9811,
                16.2507,
                16.5203,
                16.7565,
                16.8578,
                17.0605,
                17.2634,
            ],
            "y": [
                0.662945,
                0.673879,
                0.684813,
                0.690723,
                0.696042,
                0.690427,
                0.681562,
                0.673288,
                0.672401,
                0.666491,
                0.660876,
                0.653784,
                0.646396,
                0.639303,
                0.635757,
                0.628665,
                0.620982,
            ],
        }
    }

    head_curve = {
        1000: {
            "x": [
                9.1623,
                9.9946,
                9.9948,
                10.7943,
                11.5938,
                12.3933,
                12.4933,
                13.293,
                14.0929,
                14.8597,
                14.993,
                15.7599,
                16.4936,
                17.2278,
            ],
            "y": [
                70.896,
                70.513,
                70.115,
                68.537,
                66.96,
                65.383,
                64.987,
                63.011,
                60.638,
                57.867,
                57.471,
                54.302,
                51.132,
                46.768,
            ],
        }
    }

    fluid = dict(
        n2=1,
    )
    suc = State.define(p=Q_(62.7, "bar"), T=Q_(31.2, "degC"), fluid=fluid)

    with pytest.warns(UserWarning) as record:
        ccp.Impeller.load_from_dict(
            suc=suc, head_curves=head_curve, eff_curves=eff_curve, b=1, D=1
        )
        assert "Head interpolation error in speed 1000 RPM" in record[0].message.args[0]

    # faster to load than impeller_example
    composition_fd = dict(
        n2=0.4,
        co2=0.22,
        methane=92.11,
        ethane=4.94,
        propane=1.71,
        ibutane=0.24,
        butane=0.3,
        ipentane=0.04,
        pentane=0.03,
        hexane=0.01,
    )
    suc_fd = State.define(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)


def test_univariate_spline():
    test_dir = Path(__file__).parent
    curve_path = test_dir / "data"
    curve_name = "normal"

    composition_fd = dict(
        n2=0.4,
        co2=0.22,
        methane=92.11,
        ethane=4.94,
        propane=1.71,
        ibutane=0.24,
        butane=0.3,
        ipentane=0.04,
        pentane=0.03,
        hexane=0.01,
    )
    suc_fd = State.define(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)
    imp3 = Impeller.load_from_engauge_csv(
        suc=suc_fd,
        curve_name=curve_name,
        curve_path=curve_path,
        b=Q_(10.6, "mm"),
        D=Q_(390, "mm"),
        number_of_points=6,
        flow_units="kg/h",
        head_units="kJ/kg",
        head_interpolation_method="UnivariateSpline",
        eff_interpolation_method="UnivariateSpline",
    )

    p0 = imp3.point(flow_m=Q_(90184, "kg/h"), speed=Q_(9300, "RPM"))
    assert_allclose(p0.eff, 0.782169, rtol=1e-2)
    assert_allclose(p0.head, 97729.49349, rtol=1e-2)
    assert_allclose(p0.power, 3130330.074989, rtol=1e-2)
