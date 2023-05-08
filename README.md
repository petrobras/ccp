# <img src="https://ccp-centrifugal-compressor-performance.readthedocs.io/en/latest/_static/ccp.png" alt="drawing" width="40"/> Centrifugal Compressor Performance

[![PyPI Version](https://img.shields.io/pypi/v/ccp-performance.svg)](https://pypi.org/project/ccp-performance/)
[![License](https://img.shields.io/pypi/l/ccp-performance.svg)](https://github.com/raphaeltimbo/ccp/blob/master/LICENSE)
[![code style black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

ccp is a python library for calculation of centrifugal compressor performance. It uses CoolProp/REFPROP for the gas properties calculations.

```python
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

suc0 = ccp.State(fluid=fluid, p=ps, T=Ts)
disch0 = ccp.State(fluid=fluid, p=Q_(7.255, 'bar'), T=391.1)
disch1 = ccp.State(fluid=fluid, p=Q_(6.754, 'bar'), T=382.1)

# Create performance point(s):

point0 = ccp.Point(
    suc=suc0,
    disch=disch0,
    speed=Q_(7941, 'RPM'),
    flow_m=Q_(34203.6, 'kg/hr'),
    b=0.0285,
    D=0.365,
)
point1 = ccp.Point(
    suc=suc0,
    disch=disch1,
    speed=Q_(7941, 'RPM'),
    flow_m=Q_(36204.8, 'kg/hr'),
    b=0.0285,
    D=0.365,
)

# Create an impeller with those points:

imp = ccp.Impeller([point0, point1])

# Get results from the Impeller with methods such as
imp.head_plot()
imp.disch.T_plot()
```

# Documentation 
Access the documentation [here](https://ccp-centrifugal-compressor-performance.readthedocs.io/en/stable/).

# Questions
If you have any questions, you can use the [Discussions](https://github.com/petrobras/ccp/discussions) area in the repository.

# Contributing to ccp
ROSS is a community-driven project. If you want to contribute to the project, please
check [CONTRIBUTING.md](https://github.com/petrobras/ccp/blob/master/CONTRIBUTING.md). 
