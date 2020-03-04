import cProfile
import subprocess
import sys
from pathlib import Path

from ccp import Q_, State, Point, Impeller, read_csv


def generate_label(caller):
    """Generates a label to the cprofile output file."""
    commit_number = subprocess.check_output(["git", "describe", "--always"])
    commit_number = str(commit_number, "utf-8").strip("\n")

    increment = 0
    label = Path(caller + "_" + commit_number + "_" + str(increment) + ".prof")

    while label.exists():
        increment += 1
        label = Path(caller + "_" + commit_number + "_" + str(increment) + ".prof")

    return label


def state():
    State.define(
        rho=0.9280595769591103, p=Q_(1, "bar"), fluid={"Methane": 0.5, "Ethane": 0.5}
    )


def impeller():
    fluid = dict(
        methane=0.69945,
        ethane=0.09729,
        propane=0.0557,
        nbutane=0.0178,
        ibutane=0.0102,
        npentane=0.0039,
        ipentane=0.0036,
        nhexane=0.0018,
        n2=0.0149,
        co2=0.09259,
        h2s=0.00017,
        water=0.002,
    )
    suc = State.define(p=Q_(1.6995, "MPa"), T=311.55, fluid=fluid)

    p0 = Point(
        suc=suc,
        flow_v=Q_(6501.67, "m**3/h"),
        speed=Q_(11145, "RPM"),
        head=Q_(179.275, "kJ/kg"),
        eff=0.826357,
    )
    p1 = Point(
        suc=suc,
        flow_v=Q_(7016.72, "m**3/h"),
        speed=Q_(11145, "RPM"),
        head=Q_(173.057, "kJ/kg"),
        eff=0.834625,
    )

    imp1 = Impeller([p0, p1], b=Q_(28.5, "mm"), D=Q_(365, "mm"))


def create_prf_points():
    case_a = Path().home() / "ccp/ccp/tests/data/"
    fluid = {
        "methane": 0.7878,
        "ethane": 0.0917,
        "propane": 0.0562,
        "butane": 0.0146,
        "isobutane": 0.0086,
        "pentane": 0.0028,
        "isopentane": 0.0023,
        "hexane": 0.0008,
        "heptane": 0,
        "octane": 0,
        "nonane": 0,
        "decane": 0,
        "undecane": 0,
        "dodecane": 0,
        "nitrogen": 0.0049,
        "hydrogen sulfide": 0.00003,
        "carbon dioxide": 0.0303,
        "water": 0.00001,
    }
    suc = State.define(p=Q_(250.5, "bar"), T=Q_(40, "degC"), fluid=fluid)
    parameters = dict(flow_v="m**3/min", speed="RPM", head="m*kgf/kg", eff=None)
    read_csv.create_prf_points(case_a, parameters, suc, 7229)


if __name__ == "__main__":
    func = sys.argv[1]
    file_name = generate_label(func)
    cProfile.run(func + "()", file_name)
