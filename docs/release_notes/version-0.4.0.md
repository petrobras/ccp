# Version 0.4.0

Version 0.4.0 brings a major internal rework of how performance points are
computed, new conversion and serialization capabilities, and important
robustness fixes for dense fluids and REFPROP.

## Highlights

- `Point` is now built by a constraint-propagation solver, accepting any
  sufficient combination of inputs instead of a fixed list of argument
  combinations.
- New Gaussian-process surrogate method for `Impeller.convert_from`, robust
  for dense CO₂-rich conditions where the similarity method could fail.
- `Point`, `Curve` and `Impeller` objects can now be saved to and loaded from
  JSON and TOML files.
- Compatibility with CoolProp 8.

## New features

- **Constraint-propagation point solver**
  ([#138](https://github.com/petrobras/ccp/pull/138)) — the ~46
  `_calc_from_<args>` methods that previously resolved a `Point` from its
  keyword arguments were replaced by a set of small thermodynamic relations
  and a fixpoint engine (`ccp/point_solver.py`) that keeps applying them until
  the point is fully defined. Any sufficient combination of inputs now works,
  including combinations that previously had no dedicated method.

- **Gaussian-process surrogate conversion**
  ([#144](https://github.com/petrobras/ccp/pull/144)) — a new data-driven
  conversion method:

  ```python
  converted = ccp.Impeller.convert_from(
      [imp_case_a, imp_case_b, imp_case_c],
      suc=target_suc,
      method="gp_surrogate",
  )
  ```

  It fits `ψ, η = f(φ, M_tip)` over the points of all supplied measured maps
  and re-dimensionalizes the prediction at the target suction. Unlike
  `method="similarity"`, it pools multiple maps and avoids the dense-fluid
  flash, so it stays robust for dense / supercritical CO₂-rich suctions.

- **Save/load to JSON and TOML**
  ([#145](https://github.com/petrobras/ccp/pull/145),
  [#148](https://github.com/petrobras/ccp/pull/148)) — `Point`, `Curve`,
  `Impeller`, `StraightThrough` and `BackToBack` can be saved to `.json` or
  `.toml` files, with the file extension selecting the format
  (`point.save("point.json")`). Public `to_dict()` / `from_dict()` methods
  provide an in-memory representation, and `pathlib.Path` objects are accepted
  as file names.

- **Improved extrapolation for curve conversion**
  ([#136](https://github.com/petrobras/ccp/pull/136)) — speed extrapolation is
  now based on fan-law similarity (constant head coefficient ψ) referenced to
  the closest available speed curve. This makes it possible to convert maps
  that contain a single curve (fixed-speed compressors).

- **`disch_p` curve type in impeller loaders**
  ([#142](https://github.com/petrobras/ccp/pull/142)) —
  `Impeller.load_from_engauge_csv` and `Impeller.load_from_dict` now accept
  discharge-pressure curves directly (`disch_p_curves`, `disch_p_units`),
  so a map can be loaded from measured discharge pressure and temperature
  without first converting to a pressure ratio.

- **`ccp.REFPROP_AVAILABLE`**
  ([#151](https://github.com/petrobras/ccp/pull/151)) — a new flag indicating
  whether REFPROP was successfully loaded, useful to assert the intended
  backend is active instead of silently falling back to CoolProp's HEOS.

## Bug fixes

- **Forced phase is preserved through `Point` and `Impeller`**
  ([#140](https://github.com/petrobras/ccp/pull/140)) — a phase forced on a
  `State` (e.g. `State(..., phase="gas")`) was silently dropped when the state
  entered a `Point` or `Impeller` (copies and pickling lost `phase` and
  `EOS`). The forced phase now propagates end-to-end, including through
  conversion and save/load.

- **Robust `convert_from` for dense fluids**
  ([#141](https://github.com/petrobras/ccp/pull/141)) — converting maps to
  dense, CO₂-rich, near-critical suction conditions frequently failed with
  `ValueError: Could not calculate point`. The isentropic discharge seed no
  longer converges to a spurious liquid-like `(rho, s)` flash root, and the
  efficiency solve was made robust for these conditions.

- **REFPROP concurrency fixes**
  ([#150](https://github.com/petrobras/ccp/pull/150)) — intermittent
  "state cannot be generated" failures, deadlocks and process crashes during
  curve conversion were traced to concurrent entry into the REFPROP Fortran
  DLL (GIL-releasing ctypes calls, fork-based multiprocessing pools).
  Direct REFPROP calls now hold the GIL, fallbacks are coherent, and
  multiprocessing pools no longer use fork.

- **numpy 2.4 / CoolProp 7.2 compatibility**
  ([#146](https://github.com/petrobras/ccp/pull/146)) — `Impeller.curve` no
  longer passes 1-element arrays into CoolProp scalar inputs (a hard
  `TypeError` under numpy 2.4), and `Evaluation` handles CoolProp 7.2 raising
  on NaN pressures for rows with sensor dropouts.

- **CoolProp 8 compatibility**
  ([#152](https://github.com/petrobras/ccp/pull/152)) — fluid-name resolution
  handles the exception type changed in CoolProp 8, and ccp now works with
  both CoolProp 7 and 8.

## API changes

- `Point`, `Curve` and `Impeller` `save`/`load` no longer take a `file_type`
  argument — the format is determined by the file extension, and an
  unsupported or missing extension raises a `ValueError`
  ([#148](https://github.com/petrobras/ccp/pull/148)).
- The private `_dict_to_save` / `_dict_from_load` methods were replaced by
  public `to_dict()` / `from_dict()`
  ([#148](https://github.com/petrobras/ccp/pull/148)).
- The private `Point._calc_from_<args>` methods were removed in favor of the
  point solver ([#138](https://github.com/petrobras/ccp/pull/138)).

## Infrastructure and testing

- GitHub Actions CI runs the full test suite with a private REFPROP build
  ([#151](https://github.com/petrobras/ccp/pull/151)).
- The test suite was reorganized with a `slow` marker for heavy integration
  modules and `pytest-xdist` parallelization, cutting the full run from
  about 1 h to about 7 min and adding a ~40 s fast tier for development
  ([#147](https://github.com/petrobras/ccp/pull/147)).
- Expected test values were re-baselined after the interpolation and
  dependency changes
  ([#137](https://github.com/petrobras/ccp/pull/137),
  [#143](https://github.com/petrobras/ccp/pull/143),
  [#146](https://github.com/petrobras/ccp/pull/146)).
