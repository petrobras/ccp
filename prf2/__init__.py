"""
prf
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
# set refprop path in the beginning to avoid strange behavior
###############################################################################

import os as _os
from pathlib import Path as _Path
import CoolProp.CoolProp as _CP

# use _ to avoid polluting the namespace when importing
path = _os.environ['RPPREFIX']
_CP.set_config_string(_CP.ALTERNATIVE_REFPROP_PATH, path)

try:
    path = _Path(_os.environ['RPPREFIX'])
except KeyError:
    path = _Path.cwd()

if _os.name is 'posix':
    shared_library = 'librefprop.so'
else:
    shared_library = 'REFPRP64.DLL'

library_path = path / shared_library

if not library_path.is_file():
    raise FileNotFoundError(f'{library_path}.\nREFPROP not configured.')

__version__ = 'prf: 0.0.1 | ' \
              + f'CP : {_CP.get_global_param_string("version")} | ' \
              + f'REFPROP : {_CP.get_global_param_string("REFPROP_version")}'

###############################################################################
# imports
###############################################################################
