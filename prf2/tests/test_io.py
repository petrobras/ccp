import numpy as np
from pathlib import Path
from numpy.testing import assert_allclose
from prf2.data_io.read_csv import _interpolated_curve_from_csv

test_dir = Path.cwd()
data_dir = test_dir / 'data'


def test_curve_from_csv():
    file = data_dir / 'eff_7229.csv'
    eff_interpolated_curve, flow_values = _interpolated_curve_from_csv(file)

    assert_allclose(eff_interpolated_curve.get_coeffs(),
                    np.array([65.15879847, 69.67076692, 69.28892986, 56.59599537]))
