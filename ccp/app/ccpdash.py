import ccp
import pandas as pd
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly.graph_objs as go
import time
from pathlib import Path
from dash.dependencies import Input, Output

app = dash.Dash(external_stylesheets=[dbc.themes.FLATLY], title="ccp - Dashboard")
app.config.suppress_callback_exceptions = True


COMPRESSOR_TAGS = ["C-1231-A", "C-1231-B", "C-1231-C", "C-1231-D", "C-1231-E"]


# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#f8f9fa",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}

sidebar = html.Div(
    [
        html.H1(
            [
                html.Img(
                    src="/assets/ccp.png", width=150, style={"display": "inline-block"}
                ),
                html.P("ccp Dashboard", className="lead", style={"font-size": 26}),
            ],
            style={"text-align": "center"},
            className="display-4",
        ),
        html.Hr(),
        html.P(
            "Monitoramento de Performance dos Compressores da UTGCA",
            className="lead",
            style={"fontSize": "0.8rem"},
        ),
        dbc.Nav(
            [
                dbc.NavLink(f"{ctag}", href=f"/{ctag}", active="exact")
                for ctag in COMPRESSOR_TAGS
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(id="page-content", style=CONTENT_STYLE)
interval = dcc.Interval(
    id="interval-component",
    interval=600 * 1000,  # in milliseconds
    n_intervals=0,
)
store = dcc.Store(id="store")


app.layout = html.Div([dcc.Location(id="url"), sidebar, content, store, interval])


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname[1:] in COMPRESSOR_TAGS:
        return page_layout()
    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )


def page_layout():
    page = [
        dbc.Tabs(
            [
                dbc.Tab(label="Atual", tab_id="atual"),
                dbc.Tab(label="Trend", tab_id="trend"),
            ],
            id="tabs",
            active_tab="atual",
        ),
        html.Div(id="tab-content", className="p-4"),
    ]
    return page


@app.callback(
    Output("tab-content", "children"),
    [Input("tabs", "active_tab"), Input("store", "data"), Input("url", "pathname")],
)
def render_tab_content(active_tab, data, pathname):
    """
    This callback takes the 'active_tab' property as input, as well as the
    stored graphs, and renders the tab content depending on what the value of
    'active_tab' is.
    """
    path = pathname.replace("/", "")
    if active_tab and data is not None:
        if active_tab == "atual":
            container = dbc.Container(
                [
                    dbc.Row(dbc.Col(dcc.Graph(figure=data[f"head-{path}"]), width=12)),
                    dbc.Row(dbc.Col(dcc.Graph(figure=data[f"eff-{path}"]), width=12)),
                    dbc.Row(dbc.Col(dcc.Graph(figure=data[f"power-{path}"]), width=12)),
                ],
            )
            return container
        elif active_tab == "trend":
            return dbc.Row(
                [
                    dbc.Col(dcc.Graph(figure=data["hist_1"]), width=6),
                    dbc.Col(dcc.Graph(figure=data["hist_2"]), width=6),
                ]
            )
    return "No tab selected"


@app.callback(Output("store", "data"), [Input("interval-component", "n_intervals")])
def generate_graphs(n_intervals):
    """
    This callback generates three simple graphs from random data.
    """
    # simulate expensive graph generation process
    print("running")
    print("n_intervals: ", n_intervals)
    global last_update

    # generate 100 multivariate normal samples
    data = np.random.multivariate_normal([0, 0], [[1, 0.5], [0.5, 1]], 100)

    scatter = go.Figure(data=[go.Scatter(x=data[:, 0], y=data[:, 1], mode="markers")])
    hist_1 = go.Figure(data=[go.Histogram(x=data[:, 0])])
    hist_2 = go.Figure(data=[go.Histogram(x=data[:, 1])])

    results_dict = {}

    for ctag in COMPRESSOR_TAGS:
        print(f"Calculating {ctag}.")
        imp_op, point_op = calculate_performance(
            ctag.split("-")[-1].lower(), n_intervals
        )

        for curve in ["head", "eff", "power"]:
            # Head
            fig = getattr(imp_op, f"{curve}_plot")(
                flow_v=point_op.flow_v, speed=point_op.speed, speed_units="RPM"
            )
            fig = getattr(point_op, f"{curve}_plot")(
                fig=fig, speed_units="RPM", name="Operation Point"
            )

            fig.for_each_trace(
                lambda trace: trace.update(name="Expected Point")
                if "Flow" in trace.name
                else ()
            )
            results_dict[f"{curve}-{ctag}"] = fig

    # save figures in a dictionary for sending to the dcc.Store
    return results_dict


# ----------------------
# Compressor Page with 'Atual' and 'Trend' tabs.
# ----------------------

Q_ = ccp.Q_
CCP_PATH = Path(ccp.__file__).parent

# ----------------------
# Data
# ----------------------

df = pd.read_csv(
    CCP_PATH / "tests/data/UTGCA_1231_A_2019-01-01T00_00_00_2020-12-11T00_00_00_12h"
)
df = df.set_index("Unnamed: 0")
df.index.name = None

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
suc_fd = ccp.State.define(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)

curve_name = "normal"
curve_path = Path(CCP_PATH / "tests/data")

imp_fd = ccp.Impeller.load_from_engauge_csv(
    suc=suc_fd,
    curve_name=curve_name,
    curve_path=curve_path,
    b=Q_(10.6, "mm"),
    D=Q_(390, "mm"),
    number_of_points=6,
    flow_units="kg/h",
    head_units="kJ/kg",
)

imp_fd.suc = imp_fd.points[0].suc
imp_fd.flow_v = imp_fd.points[0].flow_v
imp_fd.speed = imp_fd.points[0].speed

tags_a = [
    "UTGCA_1231_TIT_218_A",  # Temperatura de sucção
    "UTGCA_1231_PIT_203_A",  # Pressão de sucção
    "UTGCA_1231_TIT_202_A",  # Temperatura de descarga
    "UTGCA_1231_PIT_204_A",  # Pressão de descarga
    "UTGCA_1231_FIT_201_A",  # Vazão
    "UTGCA_1231_SE_02_S_A",  # Rotação
]
tags_b = [
    "UTGCA_1231_TIT_219_B",  # Temperatura de sucção
    "UTGCA_1231_PIT_207_B",  # Pressão de sucção
    "UTGCA_1231_TIT_205_B",  # Temperatura de descarga
    "UTGCA_1231_PIT_208_B",  # Pressão de descarga
    "UTGCA_1231_FIT_203_B",  # Vazão
    "UTGCA_1231_SE_02_S_B",  # Rotação
]
tags_c = [
    "UTGCA_1231_TIT_220_C",  # Temperatura de sucção
    "UTGCA_1231_PIT_230_C",  # Pressão de sucção
    "UTGCA_1231_TIT_208_C",  # Temperatura de descarga
    "UTGCA_1231_PIT_212_C",  # Pressão de descarga
    "UTGCA_1231_FIT_205_C",  # Vazão
    "UTGCA_1231_SE_02_S_C",  # Rotação
]
tags_d = [
    "UTGCA_1231_TIT_221_D",  # Temperatura de sucção
    "UTGCA_1231_PIT_224_D",  # Pressão de sucção
    "UTGCA_1231_TIT_213_D",  # Temperatura de descarga
    "UTGCA_1231_PIT_225_D",  # Pressão de descarga
    "UTGCA_1231_FIT_215_D",  # Vazão
    "UTGCA_1231_SE_02_S_D",  # Rotação
]
tags_e = [
    "UTGCA_1231_TIT_222_E",  # Temperatura de sucção
    "UTGCA_1231_PIT_228_E",  # Pressão de sucção
    "UTGCA_1231_TIT_216_E",  # Temperatura de descarga
    "UTGCA_1231_PIT_229_E",  # Pressão de descarga
    "UTGCA_1231_FIT_216_E",  # Vazão
    "UTGCA_1231_SE_02_S_E",  # Rotação
]
tags_cromatografia = [
    # Cromatografia
    "UTGCA_1231_AI_002_C1",  # Analisador_METANO_AW-002',
    "UTGCA_1231_AI_002_C2",  # Analisador_ETANO_AW-002',
    "UTGCA_1231_AI_002_C3",  # CPR_Analisador_PROPANO_AW-002',
    "UTGCA_1231_AI_002_C6",  # Analisador_HEXANO_AW-002',
    "UTGCA_1231_AI_002_CO2",  # Analisador_GÁS CARBÔNICO_AW-002',
    "UTGCA_1231_AI_002_IC4",  # Analisador_I-BUTANO_AW-002',
    "UTGCA_1231_AI_002_IC5",  # Analisador_I-PENTANO_AW-002',
    "UTGCA_1231_AI_002_N2",  # Analisador_NITROGÊNIO_AW-002',
    "UTGCA_1231_AI_002_NC4",  # Analisador_N-BUTANO_AW-002',
    "UTGCA_1231_AI_002_NC5",  # Analisador_N-PENTANO_AW-002',
]
tags = tags_a + tags_b + tags_c + tags_d + tags_e + tags_cromatografia
tags_dict = {
    "tags_a": tags_a,
    "tags_b": tags_b,
    "tags_c": tags_c,
    "tags_d": tags_d,
    "tags_e": tags_e,
}


class Data:
    def __init__(self, df):
        tags = ["a", "b", "c", "d", "e"]
        self.tags = tags

        for tag in tags:
            dfx = df[tags_dict[f"tags_{tag}"] + tags_cromatografia]
            # eliminate errors such as 'comm fail'
            dfx = dfx.apply(pd.to_numeric, errors="coerce")
            # drop rows that have speed, flow etc. == 0.
            dfx = dfx[dfx != 0.0]
            dfx = dfx.dropna()
            setattr(self, f"df{tag}", dfx)


data = Data(df)


def calculate_performance(tag, sample):
    ps_st = Q_(getattr(data, f"df{tag}")[tags_dict[f"tags_{tag}"][1]][sample], "kPa")
    pd_st = Q_(getattr(data, f"df{tag}")[tags_dict[f"tags_{tag}"][3]][sample], "kPa")
    Ts_st = Q_(getattr(data, f"df{tag}")[tags_dict[f"tags_{tag}"][0]][sample], "degC")
    Td_st = Q_(getattr(data, f"df{tag}")[tags_dict[f"tags_{tag}"][2]][sample], "degC")
    flow_v_st = Q_(
        getattr(data, f"df{tag}")[tags_dict[f"tags_{tag}"][4]][sample], "m**3/h"
    )
    speed_st = Q_(getattr(data, f"df{tag}")[tags_dict[f"tags_{tag}"][5]][sample], "rpm")

    composition_st = dict(
        methane=getattr(data, f"df{tag}").UTGCA_1231_AI_002_C1[
            sample
        ],  # Analisador_METANO_AW-002',
        ethane=getattr(data, f"df{tag}").UTGCA_1231_AI_002_C2[
            sample
        ],  # Analisador_ETANO_AW-002',
        propane=getattr(data, f"df{tag}").UTGCA_1231_AI_002_C3[
            sample
        ],  # CPR_Analisador_PROPANO_AW-002',
        hexane=getattr(data, f"df{tag}").UTGCA_1231_AI_002_C6[
            sample
        ],  # Analisador_HEXANO_AW-002',
        co2=getattr(data, f"df{tag}").UTGCA_1231_AI_002_CO2[
            sample
        ],  # Analisador_GÁS CARBÔNICO_AW-002',
        ibutane=getattr(data, f"df{tag}").UTGCA_1231_AI_002_IC4[
            sample
        ],  # Analisador_I-BUTANO_AW-002',
        ipentane=getattr(data, f"df{tag}").UTGCA_1231_AI_002_IC5[
            sample
        ],  # Analisador_I-PENTANO_AW-002',
        nitrogen=getattr(data, f"df{tag}").UTGCA_1231_AI_002_N2[
            sample
        ],  # Analisador_NITROGÊNIO_AW-002',
        nbutane=getattr(data, f"df{tag}").UTGCA_1231_AI_002_NC4[
            sample
        ],  # Analisador_N-BUTANO_AW-002',
        npentane=getattr(data, f"df{tag}").UTGCA_1231_AI_002_NC5[
            sample
        ],  # Analisador_N-PENTANO_AW-002',
    )

    suc_st = ccp.State.define(p=ps_st, T=Ts_st, fluid=composition_st)
    disch_st = ccp.State.define(p=pd_st, T=Td_st, fluid=composition_st)
    imp_st = ccp.Impeller.convert_from(imp_fd, suc=suc_st)

    point_st = ccp.Point(
        speed=speed_st,
        flow_v=flow_v_st,
        suc=suc_st,
        disch=disch_st,
        b=Q_(10.6, "mm"),
        D=Q_(390, "mm"),
    )

    return imp_st, point_st


if __name__ == "__main__":
    app.run_server(debug=True, port=8888)
