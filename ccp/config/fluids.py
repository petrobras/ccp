"""Module to organize fluids."""
from warnings import warn
import CoolProp.CoolProp as CP


class Fluid:
    def __init__(self, name):
        self.name = name
        self.possible_names = []

    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__}"


_fluid_list = CP.get_global_param_string("fluids_list").split(",")
fluid_list = {name: Fluid(name) for name in _fluid_list}

# define possible names
fluid_list["IsoButane"].possible_names.extend(
    ["isobutane", "i-butane", "ibutane", "isobutan", "iso-butane"]
)
fluid_list["n-Butane"].possible_names.extend(["butane", "n-butane", "nbutane"])
fluid_list["trans-2-Butene"].possible_names.extend(["trans-butene", "trans-butene-2"])
fluid_list["IsoButene"].possible_names.extend(["i-butene", "ibutene", "iso-butene"])
fluid_list["cis-2-Butene"].possible_names.extend(["cis-butene", "cis-butene-2"])
fluid_list["n-Pentane"].possible_names.extend(["pentane", "n-pentane", "npentane"])
fluid_list["Isopentane"].possible_names.extend(
    ["i-pentane", "ipentane", "iso-pentane", "isopentane"]
)
fluid_list["n-Hexane"].possible_names.extend(["hexane", "n-hexane", "nhexane"])
fluid_list["Isohexane"].possible_names.extend(["isohexane", "i-hexane", "iso-hexane"])
fluid_list["n-Heptane"].possible_names.extend(["heptane", "n-heptane"])
fluid_list["n-Octane"].possible_names.extend(["octane", "n-octane"])
fluid_list["n-Undecane"].possible_names.extend(["undecane", "n-undecane"])
fluid_list["n-Dodecane"].possible_names.extend(["dodecane", "n-dodecane"])
fluid_list["HydrogenSulfide"].possible_names.extend(["hydrogen sulfide", "h2s"])
fluid_list["CarbonMonoxide"].possible_names.extend(["carbon monoxide", "co"])
fluid_list["CarbonDioxide"].possible_names.extend(["carbon dioxide"])
fluid_list["Nitrogen"].possible_names.extend(["n2"])
fluid_list["Oxygen"].possible_names.extend(["o2"])
fluid_list["Hydrogen"].possible_names.extend(["h2"])
fluid_list["Propylene"].possible_names.extend(["propene"])
fluid_list["Ethylene"].possible_names.extend(["ethene"])
fluid_list["R1234ze(E)"].possible_names.extend(["r1234ze", "r1234zee"])
fluid_list["R134a"].possible_names.extend(["r134a"])


def get_name(name):
    """Seach for compatible fluid name."""

    for k, v in fluid_list.items():
        if name.lower() in v.possible_names:
            name = k

    fluid_name = CP.get_REFPROPname(name)

    if fluid_name == "":
        raise ValueError(f"Fluid {name} not available. See ccp.fluid_list. ")

    return fluid_name


###############################################################################
# Helper functions
###############################################################################


def normalize_mix(molar_fractions):
    """
    Normalize the molar fractions so that the sum is 1.

    Parameters
    ----------
    molar_fractions : list
        Molar fractions of the components.

    Returns
    -------
    molar_fractions: list
        Molar fractions list will be modified in place.
    """
    total = sum(sorted(list(molar_fractions)))

    if not ((0.95 < total < 1.05) or (95 < total < 105)):
        warn(f"Molar fraction far from 1 or 100% -> Total: {total}")

    molar_fractions_dict = {k: v for k, v in enumerate(molar_fractions)}
    molar_fractions_dict = dict(
        sorted(molar_fractions_dict.items(), key=lambda item: -item[1])
    )

    # skip component with highest fraction
    molar_fractions_dict_iter = iter(molar_fractions_dict.items())
    next(molar_fractions_dict_iter)

    normalized_total = 0
    for k, v in molar_fractions_dict_iter:
        if v != 0:
            new_fraction = 1.0 - (1.0 - v / total)
            molar_fractions_dict[k] = new_fraction
            normalized_total += new_fraction

    # adjust component with highest fraction so that sum == 1.0
    molar_fractions_dict[next(iter(molar_fractions_dict))] = 1.0 - normalized_total

    for k, v in molar_fractions_dict.items():
        molar_fractions[k] = molar_fractions_dict[k]
