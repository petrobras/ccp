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
from calculate_performance import calculate_performance

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


if __name__ == "__main__":
    app.run_server(debug=True, port=8888)
