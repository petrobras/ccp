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

from .config.refprop import REFPROP
REFPROP = REFPROP()
REFPROP.set_refprop_path()
