import streamlit as st
from pathlib import Path


assets = Path(__file__).parent / "assets"
ccp_ico = assets / "favicon.ico"
ccp_logo = assets / "ccp.png"

st.set_page_config(
    page_title="Hello",
    page_icon=str(ccp_ico),
)

st.markdown(
    """
 # ccp - Centrifugal Compressor Performance
ccp is a python library for calculation of centrifugal compressor performance.
The code uses 
[CoolProp](http://www.coolprop.org/) / 
[REFPROP](https://www.nist.gov/srd/refprop)
for the gas properties calculations.
"""
)
