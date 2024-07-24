import streamlit as st
from pathlib import Path

assets = Path(__file__).parent / "assets"
ccp_ico = assets / "ccp.png"
ccp_logo = assets / "ccp_logo.png"
css_path = assets / "style.css"

st.set_page_config(
    page_title="ccp",
    page_icon=str(ccp_ico),
)

icon, header = st.columns([2, 8])
icon.image(str(ccp_ico), width=100)

header.header("ccp - Centrifugal Compressor Peformance")

st.write("")
st.subheader("Ferramenta para o cálculo de performance de compressores centrífugos")
st.write("")
st.write(
    "Essa aplicação implementa o cálculo para o acompanhamento de testes de performance em fábrica conforme ASME PTC 10."
)
st.write(
    "As equações de estado utilizadas são as do REFPROP e a ferramenta leva em consideração o vazamento no pistão de balanceamento e division wall."
)
st.write(
    "Acessar as opções na barra de navegação ao lado (Straight-Through ou Back-To-Back)."
)
st.markdown(
    "Em caso de dúvidas, sugestões ou report de bugs, abrir um issue [aqui](https://codigo.petrobras.com.br/equipamentos-dinamicos/ccp/-/issues/new).",
    unsafe_allow_html=True,
)
