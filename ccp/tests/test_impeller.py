import pytest
import numpy as np
import pickle
import toml
from pathlib import Path
from tempfile import tempdir
from numpy.testing import assert_allclose

import ccp
from ccp import ureg, Q_, State, Point, Curve, Impeller, impeller_example


@pytest.fixture(scope="module")
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
    suc = State(p=Q_(62.7, "bar"), T=Q_(31.2, "degC"), fluid=fluid)
    disch = State(p=Q_(76.82, "bar"), T=Q_(48.2, "degC"), fluid=fluid)
    disch1 = State(p=Q_(76.0, "bar"), T=Q_(48.0, "degC"), fluid=fluid)
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


@pytest.fixture(scope="module")
def imp0(points0):
    p0, p1 = points0
    imp0 = Impeller([p0, p1])
    return imp0


@pytest.fixture(scope="module")
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
    suc = State(p=Q_(1.6995, "MPa"), T=311.55, fluid=fluid)

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


def test_impeller_phase_propagation():
    # a forced suction phase must propagate to every state held by the impeller
    # (suction and discharge of every point), survive construction (deepcopy)
    # and survive conversion to a new suction state.
    fluid = {"methane": 0.7, "ethane": 0.2, "propane": 0.1}
    points = []
    for flow_v, head, eff in [(0.4, 90, 0.42), (0.5, 88, 0.46), (0.6, 84, 0.45)]:
        suc = State(p=Q_(20, "bar"), T=Q_(310, "K"), fluid=fluid, phase="gas")
        points.append(
            Point(
                suc=suc,
                head=Q_(head, "kJ/kg"),
                eff=eff,
                flow_v=Q_(flow_v, "m**3/s"),
                speed=Q_(1000, "rad/s"),
                b=Q_(0.01, "m"),
                D=Q_(0.3, "m"),
            )
        )
    imp = Impeller(points)
    assert all(p.suc.phase == "gas" for p in imp.points)
    assert all(p.disch.phase == "gas" for p in imp.points)

    new_suc = State(p=Q_(25, "bar"), T=Q_(305, "K"), fluid=fluid, phase="gas")
    imp_conv = Impeller.convert_from(imp, suc=new_suc, find="speed")
    assert all(p.suc.phase == "gas" for p in imp_conv.points)
    assert all(p.disch.phase == "gas" for p in imp_conv.points)


def test_impeller_new_suction(imp1):
    new_suc = State(p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15})
    imp2 = Impeller.convert_from(imp1, suc=new_suc, find="speed")
    p0 = imp1[0]
    new_p0 = imp2[0]

    assert_allclose(new_p0.eff.m, p0.eff.m, rtol=1e-4)
    assert_allclose(new_p0.phi.m, p0.phi.m, rtol=1e-2)
    assert_allclose(new_p0.psi.m, p0.psi.m, rtol=1e-2)
    assert_allclose(new_p0.head.m, 206048.241451, rtol=1e-2)
    assert_allclose(new_p0.power.m, 1079069.932152, rtol=1e-2)
    assert_allclose(new_p0.speed.m, 1251.21885813, rtol=1e-3)


@pytest.fixture(scope="module")
def imp2():
    points = [
        Point(
            suc=State(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1263 rad/s"),
            flow_v=Q_("1.15 m³/s"),
            head=Q_("147634 J/kg"),
            eff=Q_("0.819"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1263 rad/s"),
            flow_v=Q_("1.26 m³/s"),
            head=Q_("144664 J/kg"),
            eff=Q_("0.829"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1263 rad/s"),
            flow_v=Q_("1.36 m³/s"),
            head=Q_("139945 J/kg"),
            eff=Q_("0.831"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1337 rad/s"),
            flow_v=Q_("1.22 m³/s"),
            head=Q_("166686 J/kg"),
            eff=Q_("0.814"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
            speed=Q_("1337 rad/s"),
            flow_v=Q_("1.35 m³/s"),
            head=Q_("163620 J/kg"),
            eff=Q_("0.825"),
            b=0.010745,
            D=0.32560,
        ),
        Point(
            suc=State(p=Q_("100663 Pa"), T=Q_("305 K"), fluid={"AIR": 1.00000}),
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
        [[482.851207, 477.244663, 471.296077], [506.669295, 500.419423, 493.31087]]
    )
    assert_allclose(
        imp2.disch.T().magnitude,
        T_magnitude,
        rtol=1e-6,
    )


def test_impeller2_new_suction(imp2):
    new_suc = State(p=Q_(0.2, "MPa"), T=301.58, fluid={"n2": 1 - 1e-15, "co2": 1e-15})
    imp2_new = Impeller.convert_from(imp2, suc=new_suc, find="speed")
    p0 = imp2[0]
    new_p0 = imp2_new[0]

    assert_allclose(new_p0.eff.m, p0.eff.m, rtol=1e-4)
    assert_allclose(new_p0.phi.m, p0.phi.m, rtol=1e-2)
    assert_allclose(new_p0.psi.m, p0.psi.m, rtol=1e-2)
    assert_allclose(new_p0.head.m, 151834.04770322054, rtol=1e-2)
    assert_allclose(new_p0.power.m, 483254.4668173015, rtol=1e-2)
    assert_allclose(new_p0.speed.m, 1280.8395878181923, rtol=1e-3)
    # expected values from the bracketed solvers (the previous secant stopped
    # at 0.1 K on temperature, which moved mach_diff by 3e-6)
    assert_allclose(new_p0.mach_diff.m, 0.001481968383949428, rtol=1e-3)
    assert_allclose(new_p0.reynolds_ratio.m, 2.058786255989304, rtol=1e-3)
    assert_allclose(new_p0.volume_ratio_ratio.m, 0.999846036412339, rtol=1e-5)


@pytest.fixture(scope="module")
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
    suc_fd = State(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)

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
    assert_allclose(p0.eff.m, 0.782169, rtol=1e-4)
    assert_allclose(p0.head.m, 97729.49349, rtol=1e-4)
    assert_allclose(p0.power.m, 3130330.074989, rtol=1e-4)

    # test interpolation warning
    with pytest.warns(UserWarning) as record:
        p0 = imp3.point(flow_m=Q_(70000, "kg/h"), speed=Q_(9300, "RPM"))
        assert "Expected point is being extrapolated" in record[0].message.args[0]


def test_conversion(imp3):
    new_suc = ccp.State(p=Q_(2000, "kPa"), T=300, fluid={"co2": 1})
    new_imp3 = ccp.Impeller.convert_from(imp3, suc=new_suc)

    # fmt: off
    expected_data = (
        {
            'name': '5828.0 RPM',
            'x': np.array([0.41907986906403094, 0.4312604707683831, 0.44344107247273523, 0.4556216741770874, 0.4678022758814395, 0.4799828775857916, 0.4921634792901438, 0.5043440809944959, 0.5165246826988481, 0.5287052844032002, 0.5408858861075523, 0.5530664878119045, 0.5652470895162567, 0.5774276912206088, 0.5896082929249609, 0.6017888946293131, 0.6139694963336652, 0.6261500980380174, 0.6383306997423694, 0.6505113014467216, 0.6626919031510737, 0.6748725048554258, 0.687053106559778, 0.6992337082641302, 0.7114143099684823, 0.7235949116728344, 0.7357755133771866, 0.7479561150815387, 0.7601367167858908, 0.772317318490243]),
            'y': np.array([39275.522190957, 39333.60207602415, 39294.31950919314, 39167.35580918408, 38962.392294717065, 38689.110284512215, 38357.19109728961, 37976.31605176939, 37556.166466671624, 37106.42366071646, 36636.76895262398, 36156.88366111428, 35676.264605113094, 35197.236174039426, 34712.80551769576, 34215.35709907861, 33697.27538118444, 33150.944827009705, 32568.957190159355, 31947.005905935173, 31283.17209035111, 30575.598278860685, 29822.427006917394, 29021.800809974757, 28171.862223486292, 27270.753782905507, 26316.618023685878, 25307.597481280955, 24241.834691144224, 23117.472188729185])
        },
        {
            'name': '6533.0 RPM',
            'x': np.array([0.46953625131398635, 0.4839168816822186, 0.4982975120504508, 0.512678142418683, 0.5270587727869153, 0.5414394031551475, 0.5558200335233797, 0.570200663891612, 0.5845812942598442, 0.5989619246280764, 0.6133425549963086, 0.6277231853645409, 0.642103815732773, 0.6564844461010053, 0.6708650764692374, 0.6852457068374698, 0.6996263372057019, 0.7140069675739342, 0.7283875979421663, 0.7427682283103987, 0.7571488586786308, 0.7715294890468631, 0.7859101194150953, 0.8002907497833276, 0.8146713801515597, 0.8290520105197919, 0.8434326408880242, 0.8578132712562564, 0.8721939016244886, 0.8865745319927208]),
            'y': np.array([49230.575470348005, 49337.023011110505, 49307.37798106305, 49154.87994002802, 48892.76844782776, 48534.28306428465, 48092.66334922106, 47581.148862459384, 47012.97916382197, 46401.39381313119, 45759.632370209416, 45100.934394879034, 44438.29466396273, 43775.192015170986, 43102.743744730906, 42411.24100624566, 41690.97495331847, 40932.23673955253, 40125.539965013064, 39264.72668793774, 38346.20122025648, 37366.43378396195, 36321.89460104686, 35209.05389350391, 34024.381883325805, 32764.348792505232, 31425.4248430349, 30004.080256907506, 28496.78525611574, 26900.010062652313])
        },
        {
            'name': '7077.0 RPM',
            'x': np.array([0.5110261793384848, 0.5264372665662657, 0.5418483537940465, 0.5572594410218272, 0.5726705282496081, 0.5880816154773889, 0.6034927027051697, 0.6189037899329506, 0.6343148771607313, 0.6497259643885122, 0.665137051616293, 0.6805481388440738, 0.6959592260718546, 0.7113703132996354, 0.7267814005274162, 0.7421924877551971, 0.7576035749829779, 0.7730146622107588, 0.7884257494385396, 0.8038368366663203, 0.8192479238941012, 0.8346590111218819, 0.8500700983496627, 0.8654811855774436, 0.8808922728052244, 0.8963033600330053, 0.9117144472607861, 0.9271255344885669, 0.9425366217163478, 0.9579477089441285]),
            'y': np.array([57538.74402232518, 57631.51453940353, 57587.11386309768, 57417.41980528569, 57134.31017784557, 56749.66279265536, 56275.35546159306, 55723.265996536735, 55105.27220936438, 54433.25191195404, 53719.08291618374, 52974.643033931505, 52211.60353642246, 51433.60642699986, 50633.86340603506, 49804.88909919584, 48939.198132149984, 48029.30513056527, 47067.85940732015, 46049.525595037994, 44970.51972347256, 43827.09772969925, 42615.5155507935, 41332.02912383073, 39972.894385886364, 38534.36727403582, 37012.70372535454, 35404.159676917945, 33704.99106580144, 31911.45382908048])
        },
    )
    # fmt: on
    fig = new_imp3.head_plot()
    for exp_data, act_data in zip(expected_data, fig.data):
        assert exp_data["name"] == act_data["name"]
        assert_allclose(exp_data["x"], act_data["x"])
        assert_allclose(exp_data["y"], act_data["y"])


def test_conversion_same_speed(imp3):
    new_suc = ccp.State(p=Q_(2000, "kPa"), T=300, fluid={"co2": 1})
    new_imp3 = ccp.Impeller.convert_from(imp3, suc=new_suc, speed="same")

    # fmt: off
    expected_data = (
        {
            'name': '9300.0 RPM<br>(extrapolated)',
            'x': np.array([0.6715213352867991, 0.6917724971486379, 0.7120236590104767, 0.7322748208723154, 0.7525259827341543, 0.772777144595993, 0.7930283064578318, 0.8132794683196706, 0.8335306301815094, 0.8537817920433481, 0.874032953905187, 0.8942841157670257, 0.9145352776288644, 0.9347864394907033, 0.9550376013525421, 0.9752887632143808, 0.9955399250762196, 1.0157910869380584, 1.0360422487998973, 1.0562934106617359, 1.0765445725235747, 1.0967957343854136, 1.1170468962472524, 1.1372980581090912, 1.1575492199709299, 1.1778003818327687, 1.1980515436946075, 1.2183027055564462, 1.238553867418285, 1.2588050292801238]),
            'y': np.array([99355.91111436444, 99516.10403142382, 99439.43448078593, 99146.41265677699, 98657.54875372333, 97993.35296595108, 97174.3354877866, 96221.00651355612, 95153.87623758588, 93993.45485420211, 92760.2525577311, 91474.77954249909, 90157.18935558358, 88813.77088226701, 87432.80232177007, 86001.35818884894, 84506.51299825976, 82935.34126475861, 81275.15007631414, 79516.72650525741, 77653.53652277293, 75679.1150106268, 73586.99685058488, 71370.71692441328, 69023.81011387796, 66539.81130074486, 63912.25536677998, 61134.67719374939, 58200.61166341897, 55103.59365755477])
        },
        {
            'name': '10463.0 RPM<br>(extrapolated)',
            'x': np.array([0.7554976054952451, 0.7782812513619569, 0.8010648972286686, 0.8238485430953804, 0.846632188962092, 0.8694158348288038, 0.8921994806955156, 0.9149831265622272, 0.937766772428939, 0.9605504182956508, 0.9833340641623625, 1.0061177100290744, 1.028901355895786, 1.0516850017624977, 1.0744686476292094, 1.0972522934959212, 1.120035939362633, 1.1428195852293446, 1.1656032310960565, 1.1883868769627681, 1.2111705228294798, 1.2339541686961915, 1.2567378145629033, 1.279521460429615, 1.302305106296327, 1.3250887521630386, 1.3478723980297502, 1.370656043896462, 1.3934396897631738, 1.4162233356298854]),
            'y': np.array([125759.34415152195, 125962.10769081373, 125865.06351602363, 125494.17232297696, 124875.39480749909, 124034.69166541539, 122998.02359255114, 121791.35128473172, 120440.63543778245, 118971.83674752872, 117410.91590979588, 115783.8336204092, 114116.09915037603, 112415.67263090242, 110667.71723988338, 108855.87259645299, 106963.77831974541, 104975.07402889481, 102873.69372164168, 100647.9761719115, 98289.6509590591, 95790.53488573007, 93142.4447545701, 90337.19736822482, 87366.60952933984, 84222.49804056087, 80896.6797045335, 77380.97132390336, 73667.18970131609, 69747.15163941738])
        },
        {
            'name': '11373.0 RPM<br>(extrapolated)',
            'x': np.array([0.8212056071200824, 0.8459708182872536, 0.8707360294544249, 0.8955012406215961, 0.9202664517887673, 0.9450316629559385, 0.9697968741231098, 0.994562085290281, 1.0193272964574522, 1.0440925076246235, 1.0688577187917947, 1.093622929958966, 1.1183881411261374, 1.1431533522933086, 1.1679185634604798, 1.192683774627651, 1.2174489857948223, 1.2422141969619935, 1.2669794081291648, 1.291744619296336, 1.3165098304635072, 1.3412750416306785, 1.3660402527978497, 1.390805463965021, 1.4155706751321921, 1.4403358862993634, 1.4651010974665346, 1.4898663086337058, 1.514631519800877, 1.5393967309680483]),
            'y': np.array([148586.0, 148825.56727392686, 148710.90855132736, 148272.69666988152, 147541.6044672694, 146548.30478117097, 145323.47044926623, 143897.77430923525, 142301.889198758, 140566.4879555145, 138722.24341718474, 136799.8284214488, 134829.3824427724, 132820.3104606691, 130755.082612335, 128614.36893411809, 126378.83946236654, 124029.16423342846, 121546.36109510012, 118916.65218499518, 116130.26591333418, 113177.53374558162, 110048.78714720192, 106734.35758365956, 103224.57652041904, 99509.7754229448, 95580.28575670131, 91426.43898715306, 87038.56657976448, 82407.00000000003])
        }
    )
    # fmt: on
    fig = new_imp3.head_plot()
    for exp_data, act_data in zip(expected_data, fig.data):
        assert exp_data["name"] == act_data["name"]
        assert_allclose(exp_data["x"], act_data["x"])
        assert_allclose(exp_data["y"], act_data["y"])


def test_impeller_from_head_power(imp3):
    power_curves = {
        "9300": {
            "x1": [
                0.6687254072219386,
                0.7814575495418031,
                0.8941896918616675,
                1.0069218341815322,
                1.1196539765013964,
                1.2323861188212613,
            ],
            "x2": [
                2845523.5289321193,
                3127163.481562522,
                3277265.886285639,
                3346260.869968239,
                3319180.7261240287,
                3142302.6300651073,
            ],
            "x3": 0,
        },
        "10463": {
            "x1": [
                0.7519675035883937,
                0.8855457880957917,
                1.0191240726031896,
                1.1527023571105877,
                1.2862806416179855,
                1.4198589261253836,
            ],
            "x2": [
                4039983.5025886875,
                4470035.337140464,
                4679947.907538627,
                4766159.261322699,
                4692484.023962905,
                4371204.02452897,
            ],
            "x3": 0,
        },
        "11373": {
            "x1": [
                0.8212056071200831,
                0.9648438318896764,
                1.1084820566592695,
                1.2521202814288628,
                1.3957585061984559,
                1.5393967309680492,
            ],
            "x2": [
                5186828.999320385,
                5736177.6673671715,
                6014264.5749985445,
                6112605.998368464,
                6014767.215796105,
                5638319.478855415,
            ],
            "x3": 0,
        },
    }
    head_curves = {
        "9300": {
            "x1": [
                0.6687254072219386,
                0.7814575495418031,
                0.8941896918616675,
                1.0069218341815322,
                1.1196539765013964,
                1.2323861188212613,
            ],
            "x2": [
                100005.53018307277,
                97847.01562084591,
                91329.28298253928,
                83829.8663013647,
                73474.29567438488,
                58862.99999999999,
            ],
            "x3": 0,
        },
        "10463": {
            "x1": [
                0.7519675035883937,
                0.8855457880957917,
                1.0191240726031896,
                1.1527023571105877,
                1.2862806416179855,
                1.4198589261253836,
            ],
            "x2": [
                126268.4360992984,
                123591.84090157163,
                114656.18023528619,
                104172.92098119784,
                89712.83917676227,
                68994.16001570634,
            ],
            "x3": 0,
        },
        "11373": {
            "x1": [
                0.8212056071200831,
                0.9648438318896764,
                1.1084820566592695,
                1.2521202814288628,
                1.3957585061984559,
                1.5393967309680492,
            ],
            "x2": [
                148586.0,
                145585.48779110302,
                135621.6175049271,
                123053.00341798295,
                106048.3388840925,
                82407.00000000001,
            ],
            "x3": 0,
        },
    }

    imp = Impeller.load_from_dict(
        suc=imp3.points[0].suc,
        b=imp3.points[0].b,
        D=imp3.points[0].D,
        head_curves=head_curves,
        power_curves=power_curves,
        number_of_points=6,
        flow_units="m³/s",
        head_units="J/kg",
    )

    assert_allclose(imp.head.m, imp3.head.m)
    assert_allclose(imp.power.m, imp3.power.m)
    assert_allclose(imp.eff.m, imp3.eff.m)


@pytest.fixture(scope="module")
def imp_example():
    return impeller_example()


def test_impeller_curve(imp_example):
    imp = imp_example
    c0 = imp.curve(speed=900)
    p0 = c0[0]
    assert_allclose(p0.eff.m, 0.8171352367889275, rtol=1e-4)
    assert_allclose(p0.head.m, 136655.77330491223, rtol=1e-4)
    assert_allclose(p0.power.m, 2963324.773894661, rtol=1e-4)


def test_impeller_plot(imp_example):
    imp = imp_example
    fig = imp.eff_plot(flow_v=5, speed=900)
    expected_eff_curve = np.array(
        [
            0.8171352367889275,
            0.8181575986115578,
            0.8189898683850445,
            0.8196380345371307,
            0.8201080854955587,
            0.820406009688071,
            0.8205377955424102,
            0.820509431486319,
            0.8203269059475393,
            0.8199962073538144,
            0.8195230016060672,
            0.8188936029960678,
            0.818064330821399,
            0.816988924165089,
            0.8156211221101669,
            0.8139176445983592,
            0.811903771321443,
            0.8096733417212449,
            0.80732317609829,
            0.8049500947531023,
            0.8026191225728222,
            0.8000256627639851,
            0.7966266529327367,
            0.7918750562585511,
            0.7852238359209005,
            0.7761259550992585,
            0.7640343769730978,
            0.7484020647218917,
            0.7286819815251133,
            0.7043270905622353,
        ]
    )
    assert_allclose(fig.data[5]["y"], expected_eff_curve, rtol=1e-4)
    assert_allclose(fig.data[6]["y"], 0.8110849213647002, rtol=1e-4)


def test_impeller_plot_units(imp_example):
    imp = imp_example
    fig = imp.disch.rho_plot(
        flow_v=Q_(20000, "m³/h"),
        speed=Q_(8594, "RPM"),
        flow_v_units="m³/h",
        speed_units="RPM",
        rho_units="g/cm³",
    )
    expected_rho_curve = np.array(
        [
            0.01098769931866185,
            0.01096066793443475,
            0.010932324221719244,
            0.010902115784752477,
            0.010869490227771596,
            0.010833895155013745,
            0.010794778170716075,
            0.010751586879115723,
            0.010703768884449837,
            0.010650771790955565,
            0.010592053196182193,
            0.010527670296407518,
            0.01045860966593854,
            0.010385937825579387,
            0.010310721296134188,
            0.010233998337485175,
            0.01015615720831074,
            0.010076936166085466,
            0.00999604520736202,
            0.00991319432869308,
            0.009827829992969222,
            0.009736335084259164,
            0.009633115984165917,
            0.009512546132584733,
            0.009368998969410857,
            0.009196847934539534,
            0.008990466467866016,
            0.008744228009285551,
            0.008452505998693384,
            0.008109673875984762,
        ]
    )
    assert_allclose(fig.data[5]["y"], expected_rho_curve, rtol=1e-4)
    assert_allclose(fig.data[6]["y"], 0.008918054668713014, rtol=1e-4)


@pytest.mark.parametrize("file_format", ["toml", "json"])
def test_save_load(imp3, file_format):
    # imp3 is built with the same parameters this test used to build inline
    imp_fd = imp3
    file = Path(tempdir) / f"imp.{file_format}"
    imp_fd.save(file)

    imp_fd_loaded = Impeller.load(file)

    assert imp_fd == imp_fd_loaded
    assert hash(imp_fd) == hash(imp_fd_loaded)


def test_load_legacy_flat_file(imp3):
    # files saved before the "points"/"version" structure store the point
    # dicts at the top level of the file
    file = Path(tempdir) / "imp_legacy.toml"
    with open(file, mode="w") as f:
        toml.dump({f"Point{i}": p.to_dict() for i, p in enumerate(imp3.points)}, f)

    imp_loaded = Impeller.load(file)

    assert imp_loaded == imp3


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
    suc_fd = State(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)

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
    assert_allclose(p0.eff.m, 0.782169, rtol=1e-4)
    assert_allclose(p0.head.m, 97729.49349, rtol=1e-4)
    assert_allclose(p0.power.m, 3130330.074989, rtol=1e-4)


def test_pickle(imp0):
    pickled_imp0 = pickle.loads(pickle.dumps(imp0))
    assert pickled_imp0 == imp0
    assert hasattr(imp0, "head_plot") is True
    assert hasattr(pickled_imp0, "head_plot") is True


def test_curve_data_matches_curve(imp2):
    speed = Q_(
        (imp2.curves[0].speed.m + imp2.curves[1].speed.m) / 2, imp2.curves[0].speed.units
    )
    data = imp2._curve_data(speed)
    assert data["points"] is None  # interpolated without building points
    curve = imp2.curve(speed)
    assert_allclose(curve.flow_v.m, data["flow_v"])
    assert_allclose(curve.head.m, data["head"])
    assert_allclose(curve.eff.m, data["eff"])
    for name in ["phi_ratio", "psi_ratio", "reynolds_ratio", "mach_diff", "volume_ratio_ratio"]:
        assert_allclose([getattr(p, name).m for p in curve], data[name])
    assert float(speed.to("rad/s").m) in imp2._curve_cache
    # the cache is derived data and is not pickled
    assert "_curve_cache" not in pickle.loads(pickle.dumps(imp2)).__dict__
    # fan-law extrapolation above the map builds its points once
    high = imp2.curves[-1].speed * 1.1
    data = imp2._curve_data(high)
    assert data["extrapolated"] is True
    assert len(data["points"]) == len(imp2.curves[-1])
    curve = imp2.curve(high)
    assert_allclose(curve.head.m, data["head"])


def test_point_uses_interpolated_curve_data(imp2):
    speed = Q_(
        (imp2.curves[0].speed.m + imp2.curves[1].speed.m) / 2, imp2.curves[0].speed.units
    )
    curve = imp2.curve(speed)
    flow_v = (curve.flow_v[1] + curve.flow_v[2]) / 2
    point = imp2.point(flow_v=flow_v, speed=speed)
    head = np.interp(flow_v.m, curve.flow_v.m, curve.head.m)
    eff = np.interp(flow_v.m, curve.flow_v.m, curve.eff.m)
    assert_allclose(point.head.m, head)
    assert_allclose(point.eff.m, eff)
    assert point.speed == curve.speed


def test_point_record_converts_like_the_point(imp2):
    from ccp.impeller import _PointRecord

    new_suc = State(p=Q_(12, "bar"), T=Q_(35, "degC"), fluid={"co2": 0.7, "n2": 0.3})
    original = imp2.points[2]
    from_point = Point.convert_from(original, suc=new_suc, find="speed")
    from_record = Point.convert_from(_PointRecord(original), suc=new_suc, find="speed")
    assert_allclose(from_record.head.m, from_point.head.m)
    assert_allclose(from_record.speed.m, from_point.speed.m)
    assert_allclose(from_record.reynolds_ratio.m, from_point.reynolds_ratio.m)
    assert_allclose(from_record.mach_diff.m, from_point.mach_diff.m)
    assert_allclose(from_record.disch.T().m, from_point.disch.T().m)
