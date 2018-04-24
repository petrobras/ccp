"""Module to read points from csv files created with engauge."""
import csv
import numpy as np
from scipy.interpolate import UnivariateSpline
from tqdm import tqdm
from ccp import Q_, Point


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


def create_prf_points(case_path, parameters, suc, speed):
    """Create points for each speed."""
    parameters_names = [k for k, v in parameters.items()
                        if k not in ['speed', 'flow_v']]

    points_values = get_points_from_csv(case_path, speed, parameters_names)

    points = []
    for i in tqdm(range(len(points_values[parameters_names[0]]))):
        kwargs = {'suc': suc}
        for name, unit in parameters.items():
            if name == 'speed':
                kwargs[name] = Q_(speed, unit)
            elif name == 'eff':
                parameter_magnitude = points_values[name][i]
                if parameter_magnitude > 1:
                    parameter_magnitude /= 100
                kwargs[name] = Q_(parameter_magnitude, unit)
            else:
                parameter_magnitude = points_values[name][i]
                kwargs[name] = Q_(parameter_magnitude, unit)

        points.append(Point(**kwargs))

    return points


def load_case(case_path, parameters, suc):
    """Load from case path, given parameters and suction conditions."""

    param = None
    for p in ['head', 'eff']:
        if p in parameters:
            param = p
        if param is not None:
            break

    speed_values = get_case_speeds(case_path, param)

    points = []
    for speed in tqdm(speed_values,
                      desc='Getting points for each speed', unit='speed'):
        points += create_prf_points(case_path, parameters, suc, speed)

    return points


