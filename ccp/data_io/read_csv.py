"""Module to read points from csv files created with engauge.

The csv files should be generated with engauge with the following procedure:
Inside engauge digitizer:
 - Edit -> Paste as new
 - On Axis Point -> add 3 reference points
 - Settings -> Curves -> With 'New', add how many curves will be collected
 - Segment fill
 - Select the curve (e.g. Curve1)
 - Select the points
 - Select the next curve and points...
 - Settings -> Export Setup -> Select:
 - Raws X's and Y's ; All curves on each line
Files should be saved with the following convention:
    - <curve-name>-head.csv
    - <curve-name>-eff.csv
"""
import csv


def read_data_from_engauge_csv(file_path):
    """Generate curves dict from file_path."""
    curves = {}

    with open(str(file_path)) as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            if row:
                if row[0] == "x":
                    current_curve = row[1]
                    curves[current_curve] = {"x": [], "y": []}
                else:
                    curves[current_curve]["x"].append(float(row[0].replace(",", ".")))
                    curves[current_curve]["y"].append(float(row[1].replace(",", ".")))

    return curves
