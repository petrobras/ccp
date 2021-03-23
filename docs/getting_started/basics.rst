.. _starting

Basic Concepts
==============

The purpose of this section is to provide a basic understanding of the ccp objects and how they interact with each other.

The State
---------

The ``State`` class is the abstraction of a thermodynamic state.
To define the state we basically need the fluid composition and two thermodynamic properties:

.. python::
    s = ccp.State.define(p=100000, T=300, fluid={"Methane":0.7, "Ethane":0.3})
    # get the enthalpy
    s.h()

The Point
---------

The point is defined as a point in a centrifugal compressor performance map.
There are multiple ways to define a point, here is an example:

.. python::
    suc = ccp.State.define(p=100000, T=300, fluid={"Methane":0.7, "Ethane":0.3})
    disch = ccp.State.define(p=200000, T=350, fluid={"Methane":0.7, "Ethane":0.3})
    p = ccp.Point(suc=suc, disch=disch, flow_v=1, speed=100)

The thermodynamic states from suction and discharge, associated with the flow and speed are sufficient to define a point in the compressor performance map.
Other arguments could be used such as head, efficiency etc.

