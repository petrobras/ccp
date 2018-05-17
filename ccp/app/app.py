"""Module to implement bokeh app."""

from pathlib import Path
from itertools import groupby
from ipywidgets import interact
from scipy.interpolate import UnivariateSpline, interp1d
import numpy as np
import matplotlib.pyplot as plt

from bokeh.io import output_notebook, show, curdoc
from bokeh.layouts import column, widgetbox, layout
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool, Div, CustomJS
from bokeh.models.widgets import Slider, Button

from ccp import Q_
from ccp.data_io import read_csv
from ccp.config.utilities import r_getattr
from ccp.state import State
from ccp.impeller import Impeller

###############################################################################
# load imp
###############################################################################

home_path = Path.home()
case_string = home_path / ('Dropbox/trabalho/sequi-assessoramento'
                           '/pre-sal/dresser-rand/analise-curvas-dr/injection'
                           '/case-string/')

parameters = {'speed': 'RPM', 'flow_v': 'ft**3/min',
              'disch-temperature': 'degF', 'pressure-ratio': ''}

suc = State.define(p=Q_(14.6, 'psi'), T=Q_(90, 'degF'), fluid='air')

points = read_csv.load_case(case_string, parameters, suc)

imp = Impeller(points, b=Q_(10.745, 'mm'), D=Q_(325.6, 'mm'))
suc_n2 = State.define(p=Q_(2, 'bar'), T=Q_(40, 'degC'), fluid='n2')
imp.suc = suc_n2

imp.new.speed = imp.new.curves[0].speed
imp.new.flow_v = imp.new.curves[0].points[0].flow_v

###############################################################################
# app
###############################################################################

sources = ['head', 'eff', 'power']

speed_units = 'RPM'

bokeh_current_point_sources = {}
bokeh_current_curve_sources = {}
bokeh_sources = {}
bokeh_figures = {}

for s in sources:
    bokeh_current_point_sources[s] = r_getattr(
        imp.new.current_point, s + '_bokeh_source')()
    bokeh_current_curve_sources[s] = r_getattr(
        imp.new.current_curve, s + '_bokeh_source')(speed_units=speed_units)
    bokeh_sources[s] = r_getattr(
        imp, s + '_bokeh_source')(speed_units=speed_units)
    bokeh_figures[s] = figure(plot_width=500, plot_height=250)

    #  first plot
    bokeh_figures[s] = r_getattr(
        imp.new.current_point, s + '_bokeh_plot')(
        fig=bokeh_figures[s], source=bokeh_current_point_sources[s]
    )
    bokeh_figures[s] = r_getattr(
        imp.new.current_curve, s + '_bokeh_plot')(
        fig=bokeh_figures[s], source=bokeh_current_curve_sources[s],
        speed_units=speed_units
    )
    bokeh_figures[s] = r_getattr(
        imp.new, s + '_bokeh_plot')(
        fig=bokeh_figures[s], source=bokeh_sources[s], speed_units=speed_units
    )

download_source = imp.export_to_bokeh_source(sources, speed_units=speed_units)


def update_fig(attr, old, new):
    if (Ts.value != imp.new.suc.T().magnitude
            or ps.value != imp.new.suc.p().magnitude):
        new_suc = State.define(p=ps.value, T=Ts.value,
                               fluid=imp.new.suc.fluid)
        imp.suc = new_suc

    imp.new.flow_v = flow_v.value
    imp.new.speed = Q_(sp.value, speed_units)

    speeds = [curve.speed.to(speed_units).magnitude
              for curve in imp.new.curves]
    sp.start = round(min(speeds))
    sp.end = round(max(speeds))

    if imp.new.speed.to(speed_units).magnitude < sp.start:
        imp.new.speed = Q_(sp.start, speed_units)
        sp.value = sp.start
    elif imp.new.speed.to(speed_units).magnitude > sp.end:
        imp.new.speed = Q_(sp.end, speed_units)
        sp.value = sp.end

    flow_v.start = imp.new.current_curve.flow_v[0].magnitude
    flow_v.end = imp.new.current_curve.flow_v[-1].magnitude

    for s in sources:
        bokeh_current_point_sources[s].data = r_getattr(
            imp.new.current_point, s + '_bokeh_source')().data
        bokeh_current_curve_sources[s].data = r_getattr(
            imp.new.current_curve, s + '_bokeh_source')(
            speed_units=speed_units).data
        for d0, d1 in zip(
                bokeh_sources[s],
                r_getattr(imp.new, s + '_bokeh_source')(
                    speed_units=speed_units)):
            d0.data = d1.data

    #  update download source (check if this can be moved to on_click)
    download_source.data = imp.export_to_bokeh_source(
        sources, speed_units=speed_units).data


flow_v_start = imp.new.current_curve.flow_v[0].magnitude
flow_v_end = imp.new.current_curve.flow_v[-1].magnitude
flow_v_step = (flow_v_end - flow_v_start) / 10
flow_v = Slider(title='Suction flow (m³/s)', value=imp.new.flow_v.magnitude,
                start=flow_v_start, end=flow_v_end, step=flow_v_step)

Ts = Slider(title='Suction Temperature (K)',
            value=imp.new.current_point.suc.T().magnitude,
            start=imp.new.current_point.suc.T().magnitude - 20,
            end=imp.new.current_point.suc.T().magnitude + 20, step=0.1)

ps = Slider(title='Suction Pressure (Pa)',
            value=imp.new.current_point.suc.p().magnitude,
            start=imp.new.current_point.suc.p().magnitude - 1e5,
            end=imp.new.current_point.suc.p().magnitude + 12e5, step=1e4)

speeds = [curve.speed.to(speed_units).magnitude
          for curve in imp.new.curves]
sp = Slider(title='Speed (RPM)',
            value=imp.new.current_point.speed.to(speed_units).magnitude,
            start=round(min(speeds)),
            end=round(max(speeds)), step=10)

flow_v.on_change('value', update_fig)
Ts.on_change('value', update_fig)
ps.on_change('value', update_fig)
sp.on_change('value', update_fig)

button = Button(label='Download', button_type='success')
button.callback = CustomJS(args=dict(source=download_source),
                           code=open(str(Path.cwd() / 'download.js')).read())

inputs = widgetbox(ps, Ts, flow_v, sp, button)
# curves_html = Path.cwd() / 'curvas.html'
# desc = Div(text=open(curves_html).read(), width=1000)

curdoc().add_root(layout([bokeh_figures[sources[0]], inputs],
                         [bokeh_figures[sources[1]]],
                         [bokeh_figures[sources[2]]]))

