@echo off
call %HOMEPATH%\anaconda3\Scripts\activate.bat
set CCP_ENV=%CCP_ENV% || base
call conda activate %CCP_ENV%
streamlit run "ccp_app.py"
pause