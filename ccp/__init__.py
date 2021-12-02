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
    "CarbonDioxide": 0.8,
    "Nitrogen": 0.2,
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

import os as _os
import warnings as _warnings
from pathlib import Path as _Path

import CoolProp.CoolProp as _CP
from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary as _REFPROPFunctionLibrary

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
try:
    _RP = _REFPROPFunctionLibrary(_path)
    _RP.SETPATHdll(str(_path))
except TypeError:
    _RP = _REFPROPFunctionLibrary

if _os.name == "posix":
    _shared_library = "librefprop.so"
else:
    _shared_library = "REFPRP64.DLL"

_library_path = _path / _shared_library

if not _library_path.is_file():
    _warnings.warn(f"{_library_path}.\nREFPROP not configured.")

__version__ = "0.1.12"

__version__full = (
    f"ccp: {__version__} | "
    + f'CP : {_CP.get_global_param_string("version")} | '
    + f'REFPROP : {_CP.get_global_param_string("REFPROP_version")}'
)

###############################################################################
# pint
###############################################################################
import pint as _pint

_new_units = _Path(__file__).parent / "config/new_units.txt"
ureg = _pint.get_application_registry()
if isinstance(ureg.get(), _pint.registry.LazyRegistry):
    ureg = _pint.UnitRegistry()
    ureg.load_definitions(str(_new_units))
    # set ureg to make pickle possible
    _pint.set_application_registry(ureg)

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

from .config.fluids import fluid_list
from .state import State
from .point import Point
from .curve import Curve
from .impeller import Impeller, impeller_example
from .fo import FlowOrifice
from .similarity import check_similarity

__all__ = [
    "State",
    "Point",
    "Curve",
    "Impeller",
    "FlowOrifice",
    "fluid_list",
    "check_similarity",
    "impeller_example",
]
