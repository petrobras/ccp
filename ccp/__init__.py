"""
ccp
===

Package to evaluate the performance of a centrifugal compressor.
Example of use:

Define the fluid as a dictionary:

fluid = {'CarbonDioxide': 0.79585,
         'R134a': 0.16751,
         'Nitrogen': 0.02903,
         'Oxygen': 0.00761}

Use pint quantity to define a value:
ps = Q_(3, 'bar')
Ts = 300

If a pint quantity is not provided, SI units are assumed.

Define suction and discharge states:

suc0 = State.define(fluid=fluid, p=ps, T=Ts)
disch0 = State.define(fluid=fluid, p=Q_(7.255, 'bar'), T=391.1)

Create performance point(s):

point0 = Point(suc=suc0, disch=disch0, speed=Q_(7941, 'RPM'),
              flow_m=Q_(34203.6, 'kg/hr')
point1...

Create a curve with the points:

curve = Curve(points)

Create an impeller that will hold and convert curves.

imp = Impeller(Curve, b=0.0285, D=0.365)
"""


###############################################################################
# set refprop _path in the beginning to avoid strange behavior
###############################################################################

import os as _os
import warnings as _warnings
from pathlib import Path as _Path

import CoolProp.CoolProp as _CP

# use _ to avoid polluting the namespace when importing

try:
    _path = _Path(_os.environ["RPPREFIX"])
except KeyError:
    if _os.path.exists("C:\\Users\\Public\\REFPROP"):
        _os.environ["RPprefix"] = "C:\\Users\\Public\\REFPROP"
        _path = _Path(_os.environ["RPPREFIX"])
    else:
        _path = _Path.cwd()

_CP.set_config_string(_CP.ALTERNATIVE_REFPROP_PATH, str(_path))

if _os.name is "posix":
    _shared_library = "librefprop.so"
else:
    _shared_library = "REFPRP64.DLL"

_library_path = _path / _shared_library

if not _library_path.is_file():
    raise FileNotFoundError(f"{_library_path}.\nREFPROP not configured.")

__version__ = "0.0.1"

__version__full = (
    f"ccp: {__version__} | "
    + f'CP : {_CP.get_global_param_string("version")} | '
    + f'REFPROP : {_CP.get_global_param_string("REFPROP_version")}'
)

###############################################################################
# pint
###############################################################################

from pint import UnitRegistry as _UnitRegistry

_new_units = _Path(__file__).parent / "config/new_units.txt"
ureg = _UnitRegistry()
ureg.load_definitions(str(_new_units))
Q_ = ureg.Quantity
_warnings.filterwarnings("ignore", message="The unit of the quantity is stripped")

###############################################################################
# plotly theme
###############################################################################

from plotly import io as _pio
import ccp.plotly_theme

_pio.templates.default = "ccp"

###############################################################################
# imports
###############################################################################

from .config.units import check_units
from .config.fluids import fluid_list
from .state import State
from .point import Point
from .curve import Curve
from .impeller import Impeller
from .fo import FlowOrifice
from .data_io import read_csv
from .similarity import check_similarity
