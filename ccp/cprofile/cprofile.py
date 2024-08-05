"""Make a cProfile from main ccp functions.

To use it:
$ python cprofile.py <function name>

This will create a .prof file that can be visualized with snakeviz
$ pip install snakeviz
$ snakeviz <prof file name>.prof

"""

import cProfile
import subprocess
import sys
from pathlib import Path

from ccp import Q_, State, Point, Impeller


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
    State(rho=0.9280595769591103, p=Q_(1, "bar"), fluid={"Methane": 0.5, "Ethane": 0.5})


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
    suc = State(p=Q_(1.6995, "MPa"), T=311.55, fluid=fluid)

    p0 = Point(
        suc=suc,
        flow_v=Q_(6501.67, "m**3/h"),
        speed=Q_(11145, "RPM"),
        head=Q_(179.275, "kJ/kg"),
        eff=0.826357,
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
    )
    p1 = Point(
        suc=suc,
        flow_v=Q_(7016.72, "m**3/h"),
        speed=Q_(11145, "RPM"),
        head=Q_(173.057, "kJ/kg"),
        eff=0.834625,
        b=Q_(28.5, "mm"),
        D=Q_(365, "mm"),
    )

    imp1 = Impeller(
        [p0, p1],
    )


def create_ccp_points():
    composition_fd = dict(
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
    suc_fd = State(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)

    test_dir = Path.home() / "ccp/ccp/tests"
    curve_path = test_dir / "data"
    curve_name = "normal"

    imp_fd = Impeller.load_from_engauge_csv(
        suc=suc_fd,
        curve_name=curve_name,
        curve_path=curve_path,
        b=Q_(10.6, "mm"),
        D=Q_(390, "mm"),
        number_of_points=6,
        flow_units="kg/hr",
        head_units="kJ/kg",
    )
    new_fluid = {"co2": 0.7, "n2": 0.3}
    new_suc = State(p=Q_(10, "bar"), T=Q_(40, "degC"), fluid=new_fluid)
    imp_conv = Impeller.convert_from(imp_fd, suc=new_suc, find="speed")


if __name__ == "__main__":
    func = sys.argv[1]
    func_path = os.path.abspath(func)
    file_name = generate_label(func_path)
    cProfile.run(func_path + "()", file_name)
