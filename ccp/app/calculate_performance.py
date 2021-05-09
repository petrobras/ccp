import ccp
import pandas as pd
import numpy as np
from pathlib import Path

Q_ = ccp.Q_
CCP_PATH = Path(ccp.__file__).parent

# ----------------------
# Data
# ----------------------

df = pd.read_csv(
    CCP_PATH / "tests/data/UTGCA_1231_A_2019-01-01T00_00_00_2020-12-11T00_00_00_12h"
)
df = df.set_index("Unnamed: 0")
df.index.name = None

composition_fd = dict(
    n2=0.4,
    co2=0.22,
    methane=92.11,
    ethane=4.94,
    propane=1.71,
    ibutane=0.24,
    butane=0.3,
    ipentane=0.04,
    pentane=0.03,
    hexane=0.01,
)
suc_fd = ccp.State.define(p=Q_(3876, "kPa"), T=Q_(11, "degC"), fluid=composition_fd)

curve_name = "normal"
curve_path = Path(CCP_PATH / "tests/data")

imp_fd = ccp.Impeller.load_from_engauge_csv(
    suc=suc_fd,
    curve_name=curve_name,
    curve_path=curve_path,
    b=Q_(10.6, "mm"),
    D=Q_(390, "mm"),
    number_of_points=6,
    flow_units="kg/h",
    head_units="kJ/kg",
)

imp_fd.suc = imp_fd.points[0].suc
imp_fd.flow_v = imp_fd.points[0].flow_v
imp_fd.speed = imp_fd.points[0].speed

tags_a = {
    "Ts": "UTGCA_1231_TIT_218_A",  # Temperatura de sucção
    "ps": "UTGCA_1231_PIT_203_A",  # Pressão de sucção
    "Td": "UTGCA_1231_TIT_202_A",  # Temperatura de descarga
    "pd": "UTGCA_1231_PIT_204_A",  # Pressão de descarga
    "flow_v": "UTGCA_1231_FIT_201_A",  # Vazão
    "speed": "UTGCA_1231_SE_02_S_A",  # Rotação
}
tags_b = {
    "Ts": "UTGCA_1231_TIT_219_B",  # Temperatura de sucção
    "ps": "UTGCA_1231_PIT_207_B",  # Pressão de sucção
    "Td": "UTGCA_1231_TIT_205_B",  # Temperatura de descarga
    "pd": "UTGCA_1231_PIT_208_B",  # Pressão de descarga
    "flow_v": "UTGCA_1231_FIT_203_B",  # Vazão
    "speed": "UTGCA_1231_SE_02_S_B",  # Rotação
}
tags_c = {
    "Ts": "UTGCA_1231_TIT_220_C",  # Temperatura de sucção
    "ps": "UTGCA_1231_PIT_230_C",  # Pressão de sucção
    "Td": "UTGCA_1231_TIT_208_C",  # Temperatura de descarga
    "pd": "UTGCA_1231_PIT_212_C",  # Pressão de descarga
    "flow_v": "UTGCA_1231_FIT_205_C",  # Vazão
    "speed": "UTGCA_1231_SE_02_S_C",  # Rotação
}
tags_d = {
    "Ts": "UTGCA_1231_TIT_221_D",  # Temperatura de sucção
    "ps": "UTGCA_1231_PIT_224_D",  # Pressão de sucção
    "Td": "UTGCA_1231_TIT_213_D",  # Temperatura de descarga
    "pd": "UTGCA_1231_PIT_225_D",  # Pressão de descarga
    "flow_v": "UTGCA_1231_FIT_215_D",  # Vazão
    "speed": "UTGCA_1231_SE_02_S_D",  # Rotação
}
tags_e = {
    "Ts": "UTGCA_1231_TIT_222_E",  # Temperatura de sucção
    "ps": "UTGCA_1231_PIT_228_E",  # Pressão de sucção
    "Td": "UTGCA_1231_TIT_216_E",  # Temperatura de descarga
    "pd": "UTGCA_1231_PIT_229_E",  # Pressão de descarga
    "flow_v": "UTGCA_1231_FIT_216_E",  # Vazão
    "speed": "UTGCA_1231_SE_02_S_E",  # Rotação
}
tags_cromatografia = [
    # Cromatografia
    "UTGCA_1231_AI_002_C1",  # Analisador_METANO_AW-002',
    "UTGCA_1231_AI_002_C2",  # Analisador_ETANO_AW-002',
    "UTGCA_1231_AI_002_C3",  # CPR_Analisador_PROPANO_AW-002',
    "UTGCA_1231_AI_002_C6",  # Analisador_HEXANO_AW-002',
    "UTGCA_1231_AI_002_CO2",  # Analisador_GÁS CARBÔNICO_AW-002',
    "UTGCA_1231_AI_002_IC4",  # Analisador_I-BUTANO_AW-002',
    "UTGCA_1231_AI_002_IC5",  # Analisador_I-PENTANO_AW-002',
    "UTGCA_1231_AI_002_N2",  # Analisador_NITROGÊNIO_AW-002',
    "UTGCA_1231_AI_002_NC4",  # Analisador_N-BUTANO_AW-002',
    "UTGCA_1231_AI_002_NC5",  # Analisador_N-PENTANO_AW-002',
]
tags_dict = {
    "tags_a": tags_a,
    "tags_b": tags_b,
    "tags_c": tags_c,
    "tags_d": tags_d,
    "tags_e": tags_e,
}


class Data:
    def __init__(self, df):
        tags = ["a", "b", "c", "d", "e"]
        self.tags = tags

        for tag in tags:
            dfx = df[list(tags_dict[f"tags_{tag}"].values()) + tags_cromatografia]
            # eliminate errors such as 'comm fail'
            dfx = dfx.apply(pd.to_numeric, errors="coerce")
            # drop rows that have speed, flow etc. == 0.
            dfx = dfx[dfx != 0.0]
            dfx = dfx.dropna()
            setattr(self, f"df{tag}", dfx)


data = Data(df)


def calculate_performance(tag, time):
    # TODO get data from PI
    # TODO organize data into required format
    data_tag = getattr(data, f"df{tag}")

    # mean around required time
    # calculate fluctuation -> percent difference between the minimum and
    # maximum reading divided by the average of all readings (PTC 10 table 3.4)
    # 3 readings on a timespan of 15 minutes.

    # get 3 random samples
    random_sample = np.random.randint(0, len(data_tag))
    data_tag = data_tag.iloc[random_sample - 1 : random_sample + 2]
    sample_time = data_tag.index[1]
    data_tag = data_tag.mean()

    tags = tags_dict[f"tags_{tag}"]
    ps_st = Q_(data_tag[tags["ps"]], "kPa")
    pd_st = Q_(data_tag[tags["pd"]], "kPa")
    Ts_st = Q_(data_tag[tags["Ts"]], "degC")
    Td_st = Q_(data_tag[tags["Td"]], "degC")
    flow_v_st = Q_(data_tag[tags["flow_v"]], "m³/h")
    speed_st = Q_(data_tag[tags["speed"]], "rpm")

    composition_st = dict(
        methane=data_tag.UTGCA_1231_AI_002_C1,  # Analisador_METANO_AW-002',
        ethane=data_tag.UTGCA_1231_AI_002_C2,  # Analisador_ETANO_AW-002',
        propane=data_tag.UTGCA_1231_AI_002_C3,  # CPR_Analisador_PROPANO_AW-002',
        hexane=data_tag.UTGCA_1231_AI_002_C6,  # Analisador_HEXANO_AW-002',
        co2=data_tag.UTGCA_1231_AI_002_CO2,  # Analisador_GÁS CARBÔNICO_AW-002',
        ibutane=data_tag.UTGCA_1231_AI_002_IC4,  # Analisador_I-BUTANO_AW-002',
        ipentane=data_tag.UTGCA_1231_AI_002_IC5,  # Analisador_I-PENTANO_AW-002',
        nitrogen=data_tag.UTGCA_1231_AI_002_N2,  # Analisador_NITROGÊNIO_AW-002',
        nbutane=data_tag.UTGCA_1231_AI_002_NC4,  # Analisador_N-BUTANO_AW-002',
        npentane=data_tag.UTGCA_1231_AI_002_NC5,  # Analisador_N-PENTANO_AW-002',
    )

    suc_st = ccp.State.define(p=ps_st, T=Ts_st, fluid=composition_st)
    disch_st = ccp.State.define(p=pd_st, T=Td_st, fluid=composition_st)
    imp_st = ccp.Impeller.convert_from(imp_fd, suc=suc_st)

    point_st = ccp.Point(
        speed=speed_st,
        flow_v=flow_v_st,
        suc=suc_st,
        disch=disch_st,
        b=Q_(10.6, "mm"),
        D=Q_(390, "mm"),
    )

    return imp_st, point_st, sample_time
