"""Module to read points from csv files created with engauge."""
import csv
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


