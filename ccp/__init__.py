"""
ccp is a python library for calculation of centrifugal compressor performance.
It is based on the book of {cite}`ludtke2004process` and uses
[CoolProp](http://www.coolprop.org/)
[REFPROP](https://www.nist.gov/srd/refprop)
for the gas properties calculations.

```{code-block} python
import ccp

# ccp uses pint to handle units. Q_ is a pint quantity.
# If a pint quantity is not provided, SI units are assumed.
Q_ = ccp.Q_
ps = Q_(3, 'bar')
Ts = 300

# Define the fluid as a dictionary:
fluid = {
    "CarbonDioxide": 0.79585,
    "R134a": 0.16751,
    "Nitrogen": 0.02903,
    "Oxygen": 0.00761,
}

# Define suction and discharge states:

suc0 = ccp.State.define(fluid=fluid, p=ps, T=Ts)
disch0 = ccp.State.define(fluid=fluid, p=Q_(7.255, 'bar'), T=391.1)

# Create performance point(s):

point0 = ccp.Point(
    suc=suc0,
    disch=disch0,
    speed=Q_(7941, 'RPM'),
    flow_m=Q_(34203.6, 'kg/hr'),
    b=0.0285,
    D=0.365)
)
point1...

# Create an impeller with those points:

imp = Impeller([point0, point1, ...])
"""


###############################################################################
# set refprop path in the beginning to avoid strange behavior
###############################################################################

import os
import warnings
from pathlib import Path

import CoolProp.CoolProp as CP

# use _ to avoid polluting the namespace when importing

try:
    path = Path(os.environ["RPPREFIX"])
except KeyError:
    if os.path.exists("C:\\Users\\Public\\REFPROP"):
        os.environ["RPprefix"] = "C:\\Users\\Public\\REFPROP"
        path = Path(os.environ["RPPREFIX"])
    else:
        path = Path.cwd()

CP.set_config_string(CP.ALTERNATIVE_REFPROP_PATH, str(path))

if os.name == "posix":
    shared_library = "librefprop.so"
else:
    shared_library = "REFPRP64.DLL"

library_path = path / shared_library

if not library_path.is_file():
    warnings.warn(f"{library_path}.\nREFPROP not configured.")

__version__ = "0.1.0"

__version__full = (
    f"ccp: {__version__} | "
    + f'CP : {CP.get_global_param_string("version")} | '
    + f'REFPROP : {CP.get_global_param_string("REFPROP_version")}'
)

###############################################################################
# pint
###############################################################################

from pint import UnitRegistry

new_units = Path(__file__).parent / "config/new_units.txt"
ureg = UnitRegistry()
ureg.load_definitions(str(new_units))
Q_ = ureg.Quantity
warnings.filterwarnings("ignore", message="The unit of the quantity is stripped")

###############################################################################
# plotly theme
###############################################################################

from plotly import io as pio
import ccp.plotly_theme

pio.templates.default = "ccp"

###############################################################################
# imports
###############################################################################

from .config.units import check_units
from .config.fluids import fluid_list
from .state import State
from .point import Point
from .curve import Curve
from .impeller import Impeller, impeller_example
from .fo import FlowOrifice
from .data_io import read_csv
from .similarity import check_similarity

__all__ = [
    "check_units",
    "fluid_list",
    "State",
    "Point",
    "Curve",
    "Impeller",
    "FlowOrifice",
    "read_csv",
    "check_similarity",
    "impeller_example",
]
