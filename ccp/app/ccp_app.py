import streamlit as st

st.set_page_config(
    page_title="Hello",
    page_icon="👋",
)

icon, header = st.columns([2, 8])
icon.image("./assets/ccp.png", width=100)
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
