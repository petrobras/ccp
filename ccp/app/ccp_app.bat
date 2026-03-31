@echo off
if exist %HOMEPATH%\miniforge3\Scripts\activate.bat (
    call %HOMEPATH%\miniforge3\Scripts\activate.bat
) else if exist %HOMEPATH%\miniforge\Scripts\activate.bat (
    call %HOMEPATH%\miniforge\Scripts\activate.bat
) else (
    echo Could not find miniforge installation.
    pause
    exit /b 1
)
if defined CCP_ENV (
    call conda activate %CCP_ENV%
) else (
    call conda activate ccp
)
streamlit run "ccp_app.py"
pause