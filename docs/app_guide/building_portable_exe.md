# Building the CCP Portable Executable

This guide describes how to build a standalone portable Windows executable for the CCP (Centrifugal Compressor Performance) Streamlit application.

## Overview

The build process creates a self-contained `.exe` file that bundles:
- Python interpreter
- All CCP package dependencies
- Streamlit web framework
- Electron desktop wrapper

The final application runs as a native Windows desktop app without requiring Python or any other dependencies to be installed on the target machine.

## Prerequisites

### Required Software

1. **Python 3.12+** (via Miniforge/Miniconda recommended)
2. **Node.js 18+** (for Electron packaging)
3. **uv** (Python package manager) - optional but recommended

### Python Environment Setup

```powershell
# Create virtual environment
cd c:\path\to\ccp
python -m venv .venv

# Activate environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -e .
pip install pyinstaller streamlit sentry-sdk
```

If using a corporate proxy/Nexus repository:
```powershell
pip install -e . --index-url http://your-nexus-server/repository/pypi-all/simple/ --trusted-host your-nexus-server
```

## Build Process

### Step 1: Build PyInstaller Executable

The PyInstaller spec file is located at `build/ccp_app.spec`.

```powershell
cd build
pyinstaller --distpath=pyinstaller_build --workpath=pyinstaller_work ccp_app.spec
```

### Step 2: Copy Required DLLs

If using Miniforge/Miniconda, some DLLs need to be copied manually:

```powershell
$dlls = @(
    "liblzma.dll",
    "libbz2.dll",
    "libcrypto-3-x64.dll",
    "libssl-3-x64.dll",
    "ffi-8.dll",
    "libexpat.dll",
    "sqlite3.dll"
)
$src = "C:\path\to\miniforge3\Library\bin"
$dst = "build\pyinstaller_build\ccp_streamlit"

foreach ($dll in $dlls) {
    Copy-Item (Join-Path $src $dll) $dst -Force
}
```

### Step 3: Test PyInstaller Build

```powershell
cd build\pyinstaller_build\ccp_streamlit
.\ccp_streamlit.exe
```

The application should start and display:
```
{"port": 8501}
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

### Step 4: Build Electron Wrapper

```powershell
cd build\electron

# Install Node.js dependencies (first time only)
npm install

# Build unpacked directory
npx electron-builder --win --dir

# Apply custom icon
node -e "const {rcedit} = require('rcedit'); rcedit('../dist/win-unpacked/CCP App.exe', { icon: 'icon.ico' }).then(() => console.log('Icon updated!'))"

# Build portable executable
npx electron-builder --win portable --prepackaged ../dist/win-unpacked
```

### Step 5: Verify Build

The final portable executable is located at:
```
build/dist/CCP-App-1.0.0-portable.exe
```

## Build Output

| File | Location | Size | Description |
|------|----------|------|-------------|
| Portable EXE | `build/dist/CCP-App-1.0.0-portable.exe` | ~164 MB | Single executable, extracts on first run |
| Unpacked App | `build/dist/win-unpacked/` | ~600 MB | Full application directory |
| ZIP Archive | `build/dist/CCP-App-1.0.0.zip` | ~248 MB | Compressed unpacked app |

## Configuration Files

### PyInstaller Spec (`build/ccp_app.spec`)

Key configurations:
- Entry point: `ccp/app/run_streamlit.py`
- Icon: `ccp/app/assets/favicon.ico`
- Hidden imports for Streamlit, CoolProp, scientific packages
- Data files for Streamlit, Altair, Plotly themes

### Electron Config (`build/electron/package.json`)

Key configurations:
- App ID: `com.petrobras.ccp`
- Product Name: `CCP App`
- Target: Windows portable
- Extra resources: PyInstaller build output

### Streamlit Launcher (`ccp/app/run_streamlit.py`)

The launcher script:
- Sets `CCP_STANDALONE=1` environment variable (disables Sentry)
- Patches Streamlit to output port as JSON for Electron
- Configures Streamlit in headless mode with minimal toolbar

## Troubleshooting

### Missing DLL Errors

If you see errors like `DLL load failed while importing _ctypes`:
- Ensure all required DLLs are copied from Miniforge/Miniconda
- Check that the DLL names match exactly (e.g., `ffi-8.dll` not `libffi-8.dll`)

### Corrupted Executable

If PyInstaller produces a corrupted executable (error code 4294967295):
- Delete `pyinstaller_work` and `pyinstaller_build` folders
- Ensure no antivirus is blocking the build
- Run build again from clean state

### Icon Not Showing

If the application icon shows default Electron icon:
- Ensure `icon.ico` contains multiple resolutions (16, 24, 32, 48, 64, 128, 256)
- Use `rcedit` to apply icon after electron-builder unpacks
- Rebuild the portable from the modified unpacked directory

### Electron Builder Symlink Errors

If you see "Cannot create symbolic link" errors:
- Add `signAndEditExecutable: false` to `package.json` win config
- Use `rcedit` manually to apply icon instead

## Distribution

### For End Users

Share one of:
1. **Portable EXE** (`CCP-App-1.0.0-portable.exe`) - Recommended
2. **ZIP Archive** (`CCP-App-1.0.0.zip`) - Faster startup

### System Requirements (End User)

- Windows 10/11 (64-bit)
- No Python installation required
- No Node.js installation required

### Optional: REFPROP Support

If REFPROP is installed on the target machine:
1. Set environment variable `RPPREFIX` to the REFPROP installation folder
2. The application will use REFPROP instead of CoolProp

## Automated Build Script

For convenience, you can create a build script:

```powershell
# build_app.ps1
param(
    [string]$MiniforgePath = "C:\Users\$env:USERNAME\miniforge3"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Activate virtual environment
& "$ProjectRoot\.venv\Scripts\Activate.ps1"

# Clean previous builds
Remove-Item -Recurse -Force "$ProjectRoot\build\pyinstaller_build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$ProjectRoot\build\pyinstaller_work" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$ProjectRoot\build\dist" -ErrorAction SilentlyContinue

# Build PyInstaller
Set-Location "$ProjectRoot\build"
pyinstaller --distpath=pyinstaller_build --workpath=pyinstaller_work ccp_app.spec

# Copy DLLs
$dlls = @("liblzma.dll", "libbz2.dll", "libcrypto-3-x64.dll", "libssl-3-x64.dll", "ffi-8.dll", "libexpat.dll", "sqlite3.dll")
$src = "$MiniforgePath\Library\bin"
$dst = "$ProjectRoot\build\pyinstaller_build\ccp_streamlit"
foreach ($dll in $dlls) {
    Copy-Item (Join-Path $src $dll) $dst -Force
}

# Build Electron
Set-Location "$ProjectRoot\build\electron"
npx electron-builder --win --dir
node -e "const {rcedit} = require('rcedit'); rcedit('../dist/win-unpacked/CCP App.exe', { icon: 'icon.ico' }).then(() => console.log('Icon updated!'))"
npx electron-builder --win portable --prepackaged ../dist/win-unpacked

Write-Host "Build complete! Output: $ProjectRoot\build\dist\CCP-App-1.0.0-portable.exe"
```
