"""Module to read points from csv files created with engauge."""
import csv
import numpy as np
from scipy.interpolate import UnivariateSpline


def _interpolated_curve_from_csv(file):
    """Convert from csv file to interpolated curve.

    Function to convert from csv generated with engauge digitizer to an
    interpolated curve.
    """
    flow_values = []
    parameter = []

    with open(file) as csv_file:
        data = csv.reader(csv_file)
        next(data)
        for row in data:
            flow_values.append(float(row[0]))
            parameter.append(float(row[1]))

    parameter_interpolated_curve = UnivariateSpline(flow_values, parameter)

    return parameter_interpolated_curve, flow_values


def get_points_from_csv(case_path, speed, parameters, number_of_points=6):
    """Generate number of points from parameters interpolated curves."""
    parameters_curves = {}
    flow_all_values = []

    for param in parameters:
        param_file = case_path / f'{param}_{speed}.csv'
        param_curve, flow_values = _interpolated_curve_from_csv(param_file)
        flow_all_values += flow_values
        parameters_curves[param] = param_curve

    flow_v = np.linspace(min(flow_all_values), max(flow_all_values), number_of_points)

    parameters_values = {'flow_v': flow_v}

    for param in parameters:
        parameters_values[param] = parameters_curves[param](flow_v)

    return parameters_values


def get_case_speeds(case_path, parameter):
    """Get speed values for the given case path."""
    param_files = case_path.glob(f'*{parameter}*.csv')
    speed_values = [int(f.stem.split('_')[-1]) for f in param_files]

    return speed_values


