"""Micro-benchmarks of the ccp hot paths.

Run from the repository root::

    uv run python benchmarks/bench_hot_paths.py [REFPROP|HEOS] [--json out.json]

Every timed call gets slightly different inputs: REFPROP caches the result
of the previous flash, so repeating identical inputs under-reports the cost
of a flash by an order of magnitude. Serial numbers use
``ccp.config.PARALLEL = False``; the last rows time the multiprocessing
paths with the configured pool.
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

import ccp
from ccp import Q_, State, Point, Impeller

FLUID_NG = dict(
    n2=0.4,
    co2=0.22,
    methane=92.11,
    ethane=4.94,
    propane=1.71,
    ibutane=0.24,
    butane=0.3,
    ipentane=0.04,
    pentane=0.03,
    hexane=0.01,
)
FLUID_CO2_N2 = {"CarbonDioxide": 0.8, "Nitrogen": 0.2}
DATA_DIR = Path(ccp.__file__).parent / "tests" / "data"


def timeit(fn, n):
    """Median wall time (s) of ``fn(i)`` over ``n`` calls with distinct ``i``."""
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        fn(i)
        times.append(time.perf_counter() - t0)
    return statistics.median(times)


def perturb(value, i, scale=1e-3):
    return value * (1 + scale * (i + 1))


def bench(eos):
    ccp.config.EOS = eos
    rows = []

    def add(name, seconds, unit="ms"):
        factor = {"ms": 1e3, "s": 1.0}[unit]
        rows.append((name, seconds * factor, unit))
        print(f"{name:58s} {seconds * factor:10.2f} {unit}")

    ccp.config.PARALLEL = False
    for label, fluid in [("2-comp CO2/N2", FLUID_CO2_N2), ("10-comp NG", FLUID_NG)]:
        add(
            f"State(p, T) {label}",
            timeit(lambda i: State(p=perturb(3876e3, i), T=perturb(284.15, i), fluid=fluid), 20),
        )
        state = State(p=3876e3, T=284.15, fluid=fluid)
        p0, T0, h0, s0, rho0 = state.p(), state.T(), state.h(), state.s(), state.rho()
        add(
            f"update(p, T) {label}",
            timeit(lambda i: state.update(p=perturb(p0, i), T=perturb(T0, i)), 40),
        )
        add(
            f"update(p, h) {label} (equilibrium flash)",
            timeit(lambda i: state.update(p=perturb(p0, i), h=perturb(h0, i, 1e-4)), 40),
        )
        with State.single_phase_solver():
            add(
                f"update(p, h) {label} (inside a point solver)",
                timeit(lambda i: state.update(p=perturb(p0, i), h=perturb(h0, i, 1e-4)), 40),
            )
        add(
            f"update(rho, T) {label}",
            timeit(lambda i: state.update(rho=perturb(rho0, i), T=perturb(T0, i)), 40),
        )

    suc = State(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=FLUID_NG)
    point_kwargs = dict(
        flow_v=Q_(6501.67, "m**3/h"), speed=Q_(11145, "RPM"), b=Q_(28.5, "mm"), D=Q_(365, "mm")
    )
    add(
        "Point(suc, head, eff) 10-comp NG",
        timeit(
            lambda i: Point(
                suc=suc, head=Q_(perturb(80, i), "kJ/kg"), eff=perturb(0.8, i, 1e-4), **point_kwargs
            ),
            20,
        ),
    )
    disch = State(p=Q_(90, "bar"), T=Q_(380, "K"), fluid=FLUID_NG)
    add(
        "Point(suc, disch) 10-comp NG",
        timeit(
            lambda i: Point(
                suc=suc,
                disch=State(p=Q_(perturb(90, i), "bar"), T=Q_(perturb(380, i), "K"), fluid=FLUID_NG),
                **point_kwargs,
            ),
            20,
        ),
    )
    point = Point(suc=suc, head=Q_(80, "kJ/kg"), eff=0.8, **point_kwargs)
    new_suc = State(p=Q_(10, "bar"), T=Q_(40, "degC"), fluid={"co2": 0.7, "n2": 0.3})
    add(
        "Point.convert_from(find='speed') NG -> CO2/N2",
        timeit(
            lambda i: Point.convert_from(
                point,
                suc=State(p=Q_(perturb(10, i), "bar"), T=Q_(40, "degC"), fluid={"co2": 0.7, "n2": 0.3}),
                find="speed",
            ),
            10,
        ),
    )
    converted = Point.convert_from(point, suc=new_suc, find="speed")
    add(
        "Point.convert_from(find='volume_ratio')",
        timeit(
            lambda i: Point.convert_from(
                converted, suc=converted.suc, find="volume_ratio", speed=converted.speed * perturb(0.98, i)
            ),
            10,
        ),
    )

    def load(i):
        return Impeller.load_from_engauge_csv(
            suc=State(p=Q_(perturb(3876, i), "kPa"), T=Q_(11, "degC"), fluid=FLUID_NG),
            curve_name="normal",
            curve_path=DATA_DIR,
            b=Q_(10.6, "mm"),
            D=Q_(390, "mm"),
            number_of_points=6,
            flow_units="kg/hr",
            head_units="kJ/kg",
        )

    add("Impeller.load_from_engauge_csv 3x6 points, serial", timeit(load, 3))
    imp = load(0)
    add(
        "Impeller.convert_from(find='speed'), serial",
        timeit(
            lambda i: Impeller.convert_from(
                imp, suc=State(p=Q_(perturb(10, i), "bar"), T=Q_(40, "degC"), fluid={"co2": 0.7, "n2": 0.3})
            ),
            3,
        ),
    )
    add(
        "Impeller.convert_from(speed='same'), serial",
        timeit(
            lambda i: Impeller.convert_from(
                imp,
                suc=State(p=Q_(perturb(10, i), "bar"), T=Q_(40, "degC"), fluid={"co2": 0.7, "n2": 0.3}),
                speed="same",
            ),
            3,
        ),
    )
    add("Impeller(points) re-construction", timeit(lambda i: Impeller(imp.points), 5))
    speeds = np.array([c.speed.m for c in imp.curves])
    add(
        "Impeller.point() between curves (new speed each call)",
        timeit(
            lambda i: imp.point(
                flow_v=imp.points[3].flow_v, speed=Q_(speeds[0] + (speeds[1] - speeds[0]) * (0.3 + 0.01 * i), "rad/s")
            ),
            10,
        ),
    )
    add(
        "Impeller.point() same speed (cached curve)",
        timeit(lambda i: imp.point(flow_v=imp.points[3].flow_v * perturb(1, i), speed=Q_(speeds[1] * 1.01, "rad/s")), 10),
    )
    add(
        "Impeller.curve() between curves",
        timeit(lambda i: imp.curve(Q_(speeds[0] + (speeds[1] - speeds[0]) * (0.3 + 0.01 * i), "rad/s")), 5),
    )
    import pickle

    blob = pickle.dumps(imp)
    add("pickle.loads(impeller)", timeit(lambda i: pickle.loads(blob), 10))

    ccp.config.PARALLEL = True
    ccp.parallel.warm_up()
    add(
        "Impeller.convert_from(speed='same'), parallel (warm pool)",
        timeit(
            lambda i: Impeller.convert_from(
                imp,
                suc=State(p=Q_(perturb(10, i), "bar"), T=Q_(40, "degC"), fluid={"co2": 0.7, "n2": 0.3}),
                speed="same",
            ),
            3,
        ),
    )
    add("Impeller.load_from_engauge_csv, parallel (warm pool)", timeit(load, 3))
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("eos", nargs="?", default="REFPROP", choices=["REFPROP", "HEOS"])
    parser.add_argument("--json", type=Path, help="write the results to this file")
    args = parser.parse_args()
    print(f"ccp {ccp.__version__} | EOS {args.eos} | python {sys.version.split()[0]}")
    rows = bench(args.eos)
    if args.json:
        args.json.write_text(
            json.dumps(
                {"ccp": ccp.__version__, "eos": args.eos, "results": [dict(name=n, value=v, unit=u) for n, v, u in rows]},
                indent=2,
            )
        )
