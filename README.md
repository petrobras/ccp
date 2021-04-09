# <img src="https://ccp-centrifugal-compressor-performance.readthedocs.io/en/latest/_static/ccp.png" alt="drawing" width="40"/> Centrifugal Compressor Performance

[![PyPI Version](https://img.shields.io/pypi/v/ccp-performance.svg)](https://pypi.org/project/ccp-performance/)
[![License](https://img.shields.io/pypi/l/ccp-performance.svg)](https://github.com/raphaeltimbo/ccp/blob/master/LICENSE)
[![code style black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

ccp is a python library for calculation of centrifugal compressor performance. It is based on the book of [Ludtke04] and uses CoolProp REFPROP for the gas properties calculations.

Online documentation is available at [here](https://ccp-centrifugal-compressor-performance.readthedocs.io/en/latest/).

```python
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
```