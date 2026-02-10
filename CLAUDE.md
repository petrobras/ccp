# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **ccp** (Centrifugal Compressor Performance), a Python library for calculation of centrifugal compressor performance. It uses CoolProp/REFPROP for gas properties calculations and is based on process engineering principles.

## Key Components

### Core Classes
- **State**: Represents thermodynamic states with fluid properties (`ccp/state.py`)
- **Point**: Performance points with suction/discharge states (`ccp/point.py`)
- **Impeller**: Collection of performance points for analysis (`ccp/impeller.py`)
- **Curve**: Performance curves and interpolation (`ccp/curve.py`)
- **FlowOrifice**: Flow measurement calculations (`ccp/fo.py`)
- **Evaluation**: Performance evaluation utilities (`ccp/evaluation.py`)

### Configuration
- **Units**: Custom unit definitions in `ccp/config/new_units.txt`
- **Fluids**: Fluid property management in `ccp/config/fluids.py`
- **Plotly Theme**: Custom plotting theme in `ccp/plotly_theme.py`

### Applications
- **Streamlit App**: Web interface located in `ccp/app/` with example files and pages
- **Data I/O**: CSV/Excel reading utilities in `ccp/data_io/`

## Common Development Commands

### Package Manager
This project uses **uv** for package and environment management.

### Testing
```bash
uv run pytest                    # Run all tests with doctest modules
uv run pytest ccp/tests/         # Run unit tests only
```

### Development Setup
```bash
uv sync 
uv sync --all-extras 
```

### Running the App
```bash
uv run streamlit run ccp/app/ccp_app.py
```

### Code Formatting
Uses **Ruff** formatter - ensure all code follows Ruff formatting standards.

### Documentation
```bash
cd docs/
make html                           # Build full documentation
make EXECUTE_NOTEBOOKS='off' html  # Build docs without executing notebooks
```

## Dependencies and Environment

### Key Dependencies
- **CoolProp/REFPROP**: Gas property calculations
- **pint**: Unit handling (Q_ quantity objects)
- **plotly**: Plotting and visualization
- **pandas**: Data manipulation
- **streamlit**: Web application framework

### REFPROP Configuration
The library automatically configures REFPROP paths during initialization. REFPROP is optional but recommended for accurate gas property calculations.

## Code Architecture

### Unit System
- Uses **pint** for unit handling throughout
- `Q_` objects represent quantities with units
- SI units assumed when no units specified
- Custom units defined in `ccp/config/new_units.txt`
- **All unit conversions must use pint** - never use manual arithmetic (e.g., divide by 1000)
- Use `Q_(value, "unit").to("target_unit").m` for conversions
- Example: `Q_(head_joules, "J/kg").to("kJ/kg").m` instead of `head_joules / 1000`
- Default internal units (from `ccp/config/units.py`):
  - head: `J/kg` (joule/kilogram)
  - power: `W` (watt)
  - flow_v: `m³/s` (meter³/second)
  - pressure: `Pa` (pascal)
  - temperature: `K` (kelvin)

### Fluid Properties
- Fluids defined as dictionaries with component fractions
- State objects handle thermodynamic calculations
- Supports both CoolProp and REFPROP backends

### Performance Calculations
- Point objects contain suction/discharge states with geometric parameters
- Impeller objects analyze collections of points
- Curve objects handle interpolation and curve fitting
- All calculations follow established process engineering principles

## Testing Structure

Tests are located in `ccp/tests/` with test data in `ccp/tests/data/`. The test suite includes:
- Unit tests for all core classes
- Docstring examples (tested via pytest --doctest-modules)
- Integration tests using real compressor data

## Documentation Standards

Uses **Numpy docstring style** for all methods and classes. Examples in docstrings are tested automatically and must produce correct output.