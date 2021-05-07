import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from calculate_performance import calculate_performance

app = dash.Dash(external_stylesheets=[dbc.themes.FLATLY], title="ccp - Dashboard")
app.config.suppress_callback_exceptions = True


COMPRESSOR_TAGS = ["C-1231-A", "C-1231-B"]  # , "C-1231-C", "C-1231-D", "C-1231-E"]


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
store_int = dcc.Store(id="store-int")


app.layout = html.Div(
    [dcc.Location(id="url"), sidebar, content, store, interval, store_int]
)


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
                dbc.Tab(label="Intervalo", tab_id="intervalo"),
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
    [
        Input("tabs", "active_tab"),
        Input("store", "data"),
        Input("store-int", "data"),
        Input("url", "pathname"),
    ],
)
def render_tab_content(active_tab, data, data_int, pathname):
    """
    This callback takes the 'active_tab' property as input, as well as the
    stored graphs, and renders the tab content depending on what the value of
    'active_tab' is.
    """
    path = pathname.replace("/", "")
    if active_tab and data is not None:
        if active_tab == "atual":
            # TODO Insert sample time
            container = dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(html.P("Horário da medição: "), width=4),
                            dbc.Col(html.P(data[f"sample-time-{path}"]), width=4),
                        ]
                    ),
                    dbc.Row(dbc.Col(dcc.Graph(figure=data[f"head-{path}"]), width=12)),
                    dbc.Row(dbc.Col(dcc.Graph(figure=data[f"eff-{path}"]), width=12)),
                    dbc.Row(dbc.Col(dcc.Graph(figure=data[f"power-{path}"]), width=12)),
                ],
            )
            return container
        elif active_tab == "intervalo":
            if data_int is None:
                data_int = data
            container = dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.FormGroup(
                                    [
                                        dbc.Input(
                                            id="start-date",
                                            persistence=True,
                                            type="text",
                                        ),
                                        dbc.FormText("Data Inicial"),
                                        dbc.Popover(
                                            dbc.PopoverBody(
                                                "Data Inicial em formato aceito pelo PI."
                                            ),
                                            id="popover-start-date",
                                            target="start-date",
                                            trigger="hover",
                                            placement="bottom",
                                        ),
                                    ]
                                ),
                                width=4,
                            ),
                            dbc.Col(
                                dbc.FormGroup(
                                    [
                                        dbc.Input(
                                            id="end-date",
                                            persistence=True,
                                            type="text",
                                        ),
                                        dbc.FormText("Data Final"),
                                        dbc.Popover(
                                            dbc.PopoverBody(
                                                "Data Final em formato aceito pelo PI."
                                            ),
                                            id="popover-end-date",
                                            target="end-date",
                                            trigger="hover",
                                            placement="bottom",
                                        ),
                                    ]
                                ),
                                width=4,
                            ),
                            dbc.Col(
                                dbc.FormGroup(
                                    [
                                        dbc.Input(
                                            id="time-span",
                                            persistence=True,
                                            type="text",
                                        ),
                                        dbc.FormText("Tempo entre amostras"),
                                        dbc.Popover(
                                            dbc.PopoverBody(
                                                "Tempo entre amostras em formato aceito pelo PI (ex.: 1s, 2h etc.)."
                                            ),
                                            id="popover-time-span",
                                            target="time-span",
                                            trigger="hover",
                                            placement="bottom",
                                        ),
                                    ]
                                ),
                                width=4,
                            ),
                        ]
                    ),
                    dbc.Button("Calcular", color="primary", block=True, id="calcular"),
                    dbc.Row(
                        dbc.Col(dcc.Graph(figure=data_int[f"head-{path}"]), width=12)
                    ),
                    dbc.Row(
                        dbc.Col(dcc.Graph(figure=data_int[f"eff-{path}"]), width=12)
                    ),
                    dbc.Row(
                        dbc.Col(dcc.Graph(figure=data_int[f"power-{path}"]), width=12)
                    ),
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

    # generate 100 multivariate normal samples
    data = np.random.multivariate_normal([0, 0], [[1, 0.5], [0.5, 1]], 100)

    scatter = go.Figure(data=[go.Scatter(x=data[:, 0], y=data[:, 1], mode="markers")])
    hist_1 = go.Figure(data=[go.Histogram(x=data[:, 0])])
    hist_2 = go.Figure(data=[go.Histogram(x=data[:, 1])])

    results_dict = {}

    for ctag in COMPRESSOR_TAGS:
        print(f"Calculating {ctag}.")
        imp_op, point_op, sample_time = calculate_performance(
            ctag.split("-")[-1].lower(), n_intervals
        )

        results_dict[f"sample-time-{ctag}"] = sample_time

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


@app.callback(
    Output("store-int", "data"),
    Output("calcular", "n_clicks"),
    Input("calcular", "n_clicks"),
    Input("start-date", "value"),
    Input("end-date", "value"),
    Input("url", "pathname"),
    prevent_initial_call=True,
)
def generate_interval_fig(n_clicks, start_date, end_date, pathname):
    """
    This callback generates three simple graphs from random data.
    """
    # simulate expensive graph generation process
    print("running calc")
    print("n_clicks: ", n_clicks)

    results_dict = {}

    if n_clicks in [0, None]:
        return None, 0
    else:
        ctag = pathname.replace("/", "")

        print(f"Calculating {ctag} interval.")
        imp_op, point_op, sample_time = calculate_performance(
            ctag.split("-")[-1].lower(), 10
        )

        results_dict[f"sample-time-{ctag}"] = sample_time

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

        print(f"Calculating {ctag} interval ended.")
        n_clicks = 0

        # save figures in a dictionary for sending to the dcc.Store
    print("n_clicks: ", n_clicks)
    return results_dict, n_clicks


if __name__ == "__main__":
    app.run_server(debug=True, port=8880)
