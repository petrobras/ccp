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
from bokeh.models import HoverTool, Div
from bokeh.models.widgets import Slider

from ccp.config.utilities import r_getattr


class App:
    def __init__(self, impeller, sources, widgets):
        self.impeller = impeller
        self.sources = sources
        self.widgets = widgets
        self.figures = None

        bokeh_sources = {}
        bokeh_figures = {}
        for s in sources:
            bokeh_sources[s] = r_getattr(impeller, s + '._bokeh_source')()
            bokeh_figures[s] = figure(plot_width=500, plot_heigth=250)
            #  first plot
            bokeh_figures[s] = r_getattr(
                impeller.new.current_point, s + '._bokeh_plot')(
                fig=bokeh_figures[s], source=bokeh_sources[s]
            )
            bokeh_figures[s] = r_getattr(
                impeller.new.current_curve, s + '._bokeh_plot')(
                fig=bokeh_figures[s], source=bokeh_sources[s]
            )
            bokeh_figures[s] = r_getattr(
                impeller.new, s + '._bokeh_plot')(
                fig=bokeh_figures[s], source=bokeh_sources[s]
            )





