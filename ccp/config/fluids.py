from typing import List, Tuple
from warnings import warn
import CoolProp.CoolProp as CP


class Fluid:
    """Class to represent a fluid."""

    def __init__(self, name: str):
        self.name = name
        self.possible_names: List[str] = []

    def __repr__(self):
        return f"{type(self).__name__}({self.name})"


fluid_list = {
    name: Fluid(name) for name in CP.get_global_param_string("fluids_list").split(",")
}

# Define possible names for each fluid
fluid_aliases = {
    "n-Propane": ["propane", "n-propane", "npropane"],
    "IsoButane": ["isobutane", "i-butane", "ibutane", "isobutan", "iso-butane"],
    "n-Butane": ["butane", "n-butane", "nbutane"],
    "trans-2-Butene": ["trans-butene", "trans-butene-2"],
    "IsoButene": ["i-butene", "ibutene", "iso-butene"],
    "cis-2-Butene": ["cis-butene", "cis-butene-2"],
    "n-Pentane": ["pentane", "n-pentane", "npentane"],
    "Isopentane": ["i-pentane", "ipentane", "iso-pentane", "isopentane"],
    "n-Hexane": ["hexane", "n-hexane", "nhexane"],
    "Isohexane": ["isohexane", "i-hexane", "iso-hexane"],
    "n-Heptane": ["heptane", "n-heptane"],
    "n-Octane": ["octane", "n-octane"],
    "n-Undecane": ["undecane", "n-undecane"],
    "n-Dodecane": ["dodecane", "n-dodecane"],
    "HydrogenSulfide": ["hydrogen sulfide", "h2s"],
    "CarbonMonoxide": ["carbon monoxide", "co"],
    "CarbonDioxide": ["carbon dioxide", "co2"],
    "Nitrogen": ["n2"],
    "Oxygen": ["o2"],
    "Hydrogen": ["h2"],
    "Water": ["water", "h2o"],
    "Propylene": ["propene"],
    "Ethylene": ["ethene"],
    "R1234ze(E)": ["r1234ze", "r1234zee"],
    "R134a": ["r134a"],
    "EthylBenzene": ["ethylbenzene", "e-benzene", "ebenzene"],
}

for fluid, aliases in fluid_aliases.items():
    fluid_list[fluid].possible_names.extend(aliases)


def get_fluid_name(name: str) -> str:
    """Search for a compatible fluid name."""
    for fluid in fluid_list.values():
        if name.lower() in fluid.possible_names:
            return fluid.name

    raise ValueError(f"Fluid {name} not available. See ccp.fluid_list.")


def normalize_mix(molar_fractions: List[float]) -> List[float]:
    """
    Normalize the molar fractions so that the sum is 1.

    Parameters
    ----------
    molar_fractions : list
        Molar fractions of the components.

    Returns
    -------
    molar_fractions: list
        Normalized molar fractions.
    """
    total = sum(molar_fractions)

    if not ((0.95 < total < 1.05) or (95 < total < 105)):
        warn(f"Molar fraction far from 1 or 100% -> Total: {total}")

    normalized_total = sum(sorted(molar_fractions))  # Calculate the total again

    if normalized_total != 1.0:
        normalized_fractions = [x / normalized_total for x in molar_fractions]
        return normalized_fractions

    return molar_fractions
