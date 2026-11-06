# Version 0.5.1

Version 0.5.1 lets a compressor point run with a suction at or inside the phase
envelope again, with a warning, so data accepted by versions before 0.5.0 can
be migrated. It also adds an ideal gas model.

## Changes

- **A two-phase suction emits a `PhaseWarning` instead of a `ValueError`**
  ([#183](https://github.com/petrobras/ccp/pull/183)) —
  `Point` raised a `ValueError` in 0.5.0 for a suction with vapour quality
  between 0 and 1, which also stopped `Impeller.load_from_dict`,
  `Impeller.load_from_engauge_csv`, `Impeller.convert_from` and `Impeller.load`
  on data that earlier versions accepted. These now calculate with the
  equilibrium two-phase states of the global composition, as those versions
  did, and warn once per state, from the main process.

  This is not a wet gas model. The result assumes the liquid travels with the
  gas, evaporates as the equilibrium dictates and does not change the impeller
  aerodynamics. The efficiency of a measured point is sensitive to this: more
  than one point with 0.4 % of liquid by mass, between evaporating the liquid
  and ignoring it. The flash has a single liquid phase, so it does not represent
  water and hydrocarbon condensing separately, and the dew point of a rich gas
  can move several kelvin with hundredths of a percent of heavy components, so
  check the composition first. See
  [#182](https://github.com/petrobras/ccp/issues/182) for the future wet gas
  model.

  To keep the 0.5.0 behaviour, turn the warning into an error:
  `warnings.filterwarnings("error", category=ccp.point.PhaseWarning)`.

## Bug fixes

- **Points pickled by older versions**
  ([#183](https://github.com/petrobras/ccp/pull/183)) — `Impeller.point` and `Impeller(points)`
  raised `AttributeError: _extrapolated` on points pickled by versions that did
  not have the attribute.

## New features

- **Ideal gas model** ([#181](https://github.com/petrobras/ccp/pull/181)) — a
  state can be built with `EOS="ideal"` or `EOS="ideal:k=<k>"`.
