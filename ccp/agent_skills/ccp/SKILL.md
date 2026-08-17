---
name: ccp
description: >-
  Centrifugal compressor performance analysis with ccp (the ccp-performance
  Python package). Use when computing thermodynamic states with REFPROP or
  CoolProp (gas mixtures, equations of state), defining compressor operating
  points (suction/discharge, polytropic head and efficiency, Schultz,
  Huntington, Mallen-Saville, Sandberg-Colby methods), building impellers and
  performance maps (head/efficiency/power curves, Engauge digitized curves),
  converting curves to new suction conditions by similitude, checking ASME PTC
  10 similarity limits (Mach, Reynolds, volume ratio), measuring flow with
  orifice plates (ISO 5167), or evaluating operational data against expected
  performance.
license: Apache-2.0
---

# ccp Cookbook

Concise recipes for centrifugal compressor performance analysis with ccp. Each file is self-contained — read only the recipe you need.

> Skill version: development (repo checkout)

| Recipe | File | Key Methods |
|--------|------|-------------|
| Thermodynamic states and fluids | [states_and_fluids.md](states_and_fluids.md) | `State`, `fluid_list`, `plot_envelope` |
| Performance points | [points.md](points.md) | `Point`, `ccp.config.POLYTROPIC_METHOD` |
| Impellers and performance maps | [impellers.md](impellers.md) | `Impeller`, `point`, `curve`, `head_plot`, `save`/`load` |
| Importing curves from charts (Engauge) | [engauge_import.md](engauge_import.md) | `Impeller.load_from_engauge_csv` |
| Converting to new suction conditions | [conversion.md](conversion.md) | `Impeller.convert_from`, `Point.convert_from` |
| Similarity and ASME PTC 10 limits | [similarity.md](similarity.md) | `check_similarity`, `similarity_table`, `plot_similarity` |
| Flow orifice metering | [flow_orifice.md](flow_orifice.md) | `FlowOrifice` |
| Evaluating operational data | [evaluation.md](evaluation.md) | `Evaluation` |
| Common gotchas | [gotchas.md](gotchas.md) | — |

All values are SI internally: pressure in Pa, temperature in K, head in J/kg, power in W, volumetric flow in m³/s, mass flow in kg/s, speed in rad/s. Convert with `ccp.Q_(value, "unit")`, e.g. `ccp.Q_(7941, "RPM").to("rad/s").m`.

If the recipes disagree with the installed ccp (missing methods, changed signatures), the skill may be stale — compare the version above with `python -c "import ccp; print(ccp.__version__)"` and re-run `ccp-install-skill` after upgrading.
