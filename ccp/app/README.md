# ccp Streamlit Application

A web-based interface for centrifugal compressor performance calculations built with Streamlit.

## Overview

This application provides tools for:
- Performance test calculations following ASME PTC 10
- Performance curves conversion between different operating conditions
- Real-time online monitoring of compressor performance

The application uses REFPROP equations of state and accounts for leakage in balance pistons and division walls.

## Pages

### Home (`ccp_app.py`)
The main landing page with an overview of the application and navigation instructions.

### 1. Straight-Through (`pages/1_straight_through.py`)
Performance calculation for straight-through compressor configurations. Allows users to:
- Define gas compositions
- Input test data (pressures, temperatures, flows, speeds)
- Calculate performance parameters (head, efficiency, power)
- Compare against guarantee points
- Export results to Excel

### 2. Back-to-Back (`pages/2_back_to_back.py`)
Performance calculation for back-to-back compressor configurations with multiple sections. Similar functionality to straight-through but handles:
- Multiple compression sections
- Inter-stage conditions
- Division wall leakage calculations

### 3. Curves Conversion (`pages/3_curves_conversion.py`)
Convert performance curves between different operating conditions. Features:
- Load digitized curves from Engauge CSV files
- Define original and target suction conditions
- Convert curves to new operating conditions
- Visualize and export converted curves

### 4. Online Monitoring (`pages/4_online_monitoring.py`)
Real-time performance monitoring for operating compressors. Features:
- Configure PI tag mappings for process data
- Define design cases with performance curves
- Monitor compressor performance in real-time
- Compare actual vs. expected performance
- Support for both direct flow measurement and orifice-based calculation

## Running the Application

### Standard Mode

```bash
# Navigate to the app directory
cd ccp/app

# Run the main application
streamlit run ccp_app.py
```

Or run a specific page directly:

```bash
streamlit run pages/4_online_monitoring.py
```

### Testing Mode (with Mock Data)

For the Online Monitoring page, you can run with mock data for testing purposes:

```bash
streamlit run pages/4_online_monitoring.py -- testing=True
```

In testing mode:
- A warning banner is displayed at the top of the page
- The `example_online.ccp` session file is automatically loaded on startup
- Data is loaded from test parquet files instead of PI server
- The `fetch_pi_data_online()` function returns random 3-point samples for simulating real-time updates

This allows you to immediately test the monitoring functionality without manually loading a session file or configuring design cases.

### Windows Batch File

A batch file `ccp_app.bat` is provided for easy launching on Windows systems.

## Configuration

### Streamlit Settings

Streamlit configuration is stored in `.streamlit/` directory.

### Example Files

Several example session files are included:
- `example_straight.ccp` - Example straight-through compressor session
- `example_back_to_back.ccp` - Example back-to-back compressor session
- `example_online.ccp` - Example online monitoring session
- `curves-conversion-example.ccp` - Example curves conversion session

These can be loaded via the "Open File" option in each page's sidebar.

## Dependencies

See `requirements.txt` for Streamlit-specific dependencies. The main `ccp` package dependencies are defined in the project's root `pyproject.toml`.

## File Structure

```
ccp/app/
├── ccp_app.py              # Main application entry point
├── common.py               # Shared utilities and UI components
├── requirements.txt        # Streamlit dependencies
├── ccp_app.bat            # Windows batch launcher
├── __init__.py
├── assets/                 # Images, CSS, icons
├── data/                   # Application data files
├── pages/                  # Streamlit pages
│   ├── 1_straight_through.py
│   ├── 2_back_to_back.py
│   ├── 3_curves_conversion.py
│   ├── 4_online_monitoring.py
│   └── assets/
├── .streamlit/            # Streamlit configuration
└── *.ccp                  # Example session files
```
