import numpy as np
import csv


def _read_data_from_engauge_csv(file_path):
    """Create dict from a csv generated from engauge."""
    curves_dict = {}

    with open(str(file_path)) as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            if row[0] == 'x':
                current_curve = row[1]
                curves_dict[current_curve] = {'x': [], 'y': []}
            else:
                curves_dict[current_curve]['x'].append(float(row[0]))
                curves_dict[current_curve]['y'].append(float(row[1]))

    return curves_dict
