import os

FileName = os.path.basename(__file__)[:-3]

DEBUG_MODE = True
if DEBUG_MODE:
    FileName = "Beta_2section_back_to_back_export.xlsm"

import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
log_file = Path(__file__).parent / "log.txt"
handler = logging.FileHandler(log_file, mode="w")
logger.addHandler(handler)


def handle_exception(exc_type, exc_value, exc_traceback):
    TP_sheet["R23"].value = "ERRO!"
    AT_sheet["Z9"].value = "ERRO!"
    CF_sheet["L8"].value = "ERRO!"
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        logger.critical(
            "Exception occured:", exc_info=(exc_type, exc_value, exc_traceback)
        )


sys.excepthook = handle_exception

from xlwings import Book

wb = Book(FileName)  # connect to an existing file in the current working directory
AT_sheet = wb.sheets["Actual Test Data"]
TG_sheet = wb.sheets["Test Gas"]
TP_sheet = wb.sheets["Test Procedure Data"]
FD_sheet = wb.sheets["DataSheet"]
CF_sheet = wb.sheets["CalcFlow"]

if AT_sheet["Z13"].value != None:
    AT_sheet["Z9"].value = "Carregando bibliotecas..."
elif TP_sheet["R19"].value != None:
    TP_sheet["R23"].value = "Carregando bibliotecas..."
elif CF_sheet["L4"].value != None:
    CF_sheet["L8"].value = "Carregando bibliotecas..."

import os

try:
    aux = os.environ["RPprefix"]
except:
    os.environ["RPprefix"] = "C:\\Users\\Public\\REFPROP"
import ccp
from ccp import State, Q_
from ccp import compressor
import numpy as np
from scipy.optimize import newton
import multiprocessing

logger.critical("System Information:")
logger.critical(f"python: {sys.version}")
logger.critical(f"ccp: {ccp.__version__full}")

if __name__ == "__main__":

    if DEBUG_MODE:
        AT_sheet["Z13"].value = "Calcular"

    global P_FD_eff, P2_FD_eff

    def reynolds_corr(P_AT, P_FD, rug=None):

        ReAT = P_AT.reynolds
        ReFD = P_FD.reynolds

        RCAT = 0.988 / ReAT**0.243
        RCFD = 0.988 / ReFD**0.243

        RBAT = np.log(0.000125 + 13.67 / ReAT) / np.log(rug + 13.67 / ReAT)
        RBFD = np.log(0.000125 + 13.67 / ReFD) / np.log(rug + 13.67 / ReFD)

        RAAT = 0.066 + 0.934 * (4.8e6 * b.to("ft").magnitude / ReAT) ** RCAT
        RAFD = 0.066 + 0.934 * (4.8e6 * b.to("ft").magnitude / ReFD) ** RCFD

        corr = RAFD / RAAT * RBFD / RBAT

        # correct efficiency
        eff = 1 - (1 - P_AT.eff) * corr

        #####Results_AT[i, 21].value = eff.m
        N_ratio = (P_FD.speed / P_AT.speed).to("dimensionless").m

        P_ATconv_temp = ccp.Point(
            suc=P_FD.suc,
            eff=eff,
            speed=P_FD.speed,
            flow_v=P_AT.flow_v * N_ratio,
            head=P_AT.head * N_ratio**2,
            b=P_FD.b,
            D=P_FD.D,
        )

        # correct head coeficient
        def update_h(h):
            global P_AT_reyn
            P_AT_reyn = ccp.Point(
                suc=P_FD.suc,
                eff=eff,
                speed=P_FD.speed,
                flow_v=P_AT.flow_v * N_ratio,
                head=h,
                b=P_FD.b,
                D=P_FD.D,
            )

            return P_AT_reyn.psi.m - P_AT.psi.m * eff.m / P_AT.eff.m

        newton(update_h, P_ATconv_temp.psi.m, tol=1)

        return P_AT_reyn

    if AT_sheet["Z13"].value != None:

        AT_sheet["Z13"].value = None
        AT_sheet["Z9"].value = "Calculando..."

        FD_sheet = wb.sheets["DataSheet"]
        ### Reading and writing SECTION 1 from the FD sheet

        Ps_FD = Q_(FD_sheet["T23"].value, "bar")
        Ts_FD = Q_(FD_sheet.range("T24").value, "degC")

        Pd_FD = Q_(FD_sheet.range("T31").value, "bar")
        Td_FD = Q_(FD_sheet.range("T32").value, "degC")

        eff_FD = Q_(FD_sheet.range("T41").value, "dimensionless")
        Pow_FD = Q_(FD_sheet.range("T35").value, "kW")
        H_FD = Q_(FD_sheet.range("T40").value, "J/kg")

        if FD_sheet.range("T21").value == None:
            V_test = True
            flow_v_FD = Q_(FD_sheet.range("T29").value, "m³/h")
        else:
            V_test = False
            flow_m_FD = Q_(FD_sheet.range("T21").value, "kg/h")

        # flow_m_FD = Q_(FD_sheet.range('T21').value,'kg/h')
        # flow_v_FD = Q_(FD_sheet.range('T29').value,'m**3/h')

        speed_FD = Q_(FD_sheet.range("T38").value, "rpm")

        D = Q_(FD_sheet.range("AB132").value, "mm")
        b = Q_(FD_sheet.range("AQ132").value, "mm")

        GasesFD = FD_sheet.range("B69:B85").value
        mol_fracFD = FD_sheet.range("K69:K85").value

        fluid_FD = {GasesFD[i]: mol_fracFD[i] for i in range(len(GasesFD))}

        sucFD = State.define(fluid=fluid_FD, p=Ps_FD, T=Ts_FD)

        if V_test:
            flow_m_FD = flow_v_FD * sucFD.rho()
            FD_sheet["AS34"].value = flow_m_FD.to("kg/h").magnitude
            FD_sheet["AQ34"].value = "Mass Flow"
            FD_sheet["AU34"].value = "kg/h"
        else:
            flow_v_FD = flow_m_FD / sucFD.rho()
            FD_sheet["AS34"].value = flow_v_FD.to("m³/h").magnitude
            FD_sheet["AQ34"].value = "Inlet Volume Flow"
            FD_sheet["AU34"].value = "m³/h"

        dischFD = State.define(fluid=fluid_FD, p=Pd_FD, T=Td_FD)

        P_FD = ccp.Point(
            speed=speed_FD, flow_m=flow_m_FD, suc=sucFD, disch=dischFD, b=b, D=D
        )

        def update_head(H):
            global P_FD_eff
            P_FD_eff = ccp.Point(
                speed=speed_FD,
                flow_m=flow_m_FD,
                suc=sucFD,
                eff=eff_FD,
                head=Q_(H, "J/kg"),
                b=b,
                D=D,
            )

            P = P_FD_eff.disch.p().to("Pa").magnitude

            return P - Pd_FD.to("Pa").magnitude

        newton(
            update_head,
            ccp.point.head_pol(suc=P_FD.suc, disch=P_FD.disch).to("J/kg").magnitude,
            tol=1,
        )

        max_H = max(
            [
                H_FD.to("kJ/kg").magnitude,
            ]
        )
        min_Pow = min(
            [
                Pow_FD.to("kW").magnitude,
            ]
        )

        FD_sheet["AS25"].value = P_FD.mach.magnitude
        FD_sheet["AS26"].value = P_FD.reynolds.magnitude
        FD_sheet["AS27"].value = 1 / P_FD.volume_ratio.magnitude
        FD_sheet["AS28"].value = P_FD_eff.head.to("J/kg").magnitude
        FD_sheet["AS29"].value = P_FD_eff.disch.T().to("degC").magnitude
        FD_sheet["AS30"].value = P_FD_eff.power.to("kW").magnitude
        FD_sheet["AS31"].value = P_FD.head.to("J/kg").magnitude
        FD_sheet["AS32"].value = P_FD.eff.magnitude
        FD_sheet["AS33"].value = P_FD.power.to("kW").magnitude

        ### Reading and writing SECTION 2 from the FD sheet
        Pd2_FD = Q_(FD_sheet.range("Z31").value, "bar")
        Td2_FD = Q_(FD_sheet.range("Z32").value, "degC")

        eff2_FD = Q_(FD_sheet.range("Z41").value, "dimensionless")
        Pow2_FD = Q_(FD_sheet.range("Z35").value, "kW")
        H2_FD = Q_(FD_sheet.range("Z40").value, "J/kg")

        D2 = Q_(FD_sheet.range("AB133").value, "mm")
        b2 = Q_(FD_sheet.range("AQ133").value, "mm")

        Ps2_FD = Q_(FD_sheet.range("Z23").value, "bar")
        Ts2_FD = Q_(FD_sheet.range("Z24").value, "degC")
        GasesFD = FD_sheet.range("B69:B85").value
        mol_frac2_FD = FD_sheet.range("Q69:Q85").value

        fluid2_FD = {GasesFD[i]: mol_frac2_FD[i] for i in range(len(GasesFD))}

        suc2FD = State.define(fluid=fluid2_FD, p=Ps2_FD, T=Ts2_FD)
        suc2FD_eff = suc2FD
        disch2FD = State.define(fluid=fluid2_FD, p=Pd2_FD, T=Td2_FD)
        if V_test:
            flow2_v_FD = Q_(FD_sheet.range("Z29").value, "m³/h")
            flow2_m_FD = flow2_v_FD * suc2FD.rho()
            FD_sheet["AT34"].value = flow2_m_FD.to("kg/h").magnitude
        else:
            flow2_m_FD = Q_(FD_sheet.range("Z21").value, "kg/h")
            flow2_v_FD = flow2_m_FD / suc2FD.rho()
            FD_sheet["AT34"].value = flow2_v_FD.to("m³/h").magnitude

        P2_FD = ccp.Point(
            speed=speed_FD,
            flow_m=flow2_m_FD,
            suc=suc2FD,
            disch=disch2FD,
            b=b2,
            D=D2,
        )

        def update_head2(H):
            global P2_FD_eff
            P2_FD_eff = ccp.Point(
                speed=speed_FD,
                flow_m=flow2_m_FD,
                suc=suc2FD_eff,
                eff=eff2_FD,
                head=Q_(H, "J/kg"),
                b=b,
                D=D,
            )

            P2 = P2_FD_eff.disch.p().to("Pa").magnitude

            return P2 - Pd2_FD.to("Pa").magnitude

        newton(
            update_head2,
            ccp.point.head_pol(suc=P2_FD.suc, disch=P2_FD.disch).to("J/kg").magnitude,
            tol=1,
        )

        max_H2 = max(
            [
                H2_FD.to("kJ/kg").magnitude,
            ]
        )
        min_Pow2 = min(
            [
                Pow2_FD.to("kW").magnitude,
            ]
        )

        FD_sheet["AT25"].value = P2_FD.mach.magnitude
        FD_sheet["AT26"].value = P2_FD.reynolds.magnitude
        FD_sheet["AT27"].value = P2_FD.volume_ratio.magnitude
        FD_sheet["AT28"].value = P2_FD_eff.head.to("J/kg").magnitude
        FD_sheet["AT29"].value = P2_FD_eff.disch.T().to("degC").magnitude
        FD_sheet["AT30"].value = P2_FD_eff.power.to("kW").magnitude
        FD_sheet["AT31"].value = P2_FD.head.to("J/kg").magnitude
        FD_sheet["AT32"].value = P2_FD.eff.magnitude
        FD_sheet["AT33"].value = P2_FD.power.to("kW").magnitude

        FD_sheet["K90"].value = sucFD.molar_mass().to("g/mol").magnitude
        FD_sheet["Q90"].value = suc2FD.molar_mass().to("g/mol").magnitude

        ### End of Reading and writing in the FD sheet

        Curva = FD_sheet["AP42:AS49"]
        Curva2 = FD_sheet["AP53:AS60"]

        for i in range(8):
            if Curva[i, 0].value == None or i == 7:
                Nc = i
                break

        for i in range(8):
            if Curva2[i, 0].value == None or i == 7:
                Nc2 = i
                break

        Curva = Curva[0 : Nc + 1, :]
        Curva2 = Curva2[0 : Nc2 + 1, :]

        ## Organização dos pontos da curva da primeira seção
        flow1_unit = FD_sheet["AP41"].value
        head1_unit = FD_sheet["AQ41"].value
        QFD = Q_(np.array(Curva[0:Nc, 0].value), flow1_unit)

        if Nc <= 0:
            Gar = [
                flow_v_FD.to("m³/h").magnitude,
                P_FD.head.to("kJ/kg").magnitude,
                None,
                P_FD.eff.magnitude,
            ]
            Curva[Nc, :].value = Gar
            Nc = Nc + 1
        elif Nc > 1 and min(abs(QFD.to("m³/h").m - flow_v_FD.to("m³/h").m)) == 0:
            Gar = [None, None, None, None]
            Curva[Nc, :].value = Gar
        else:
            Gar = [
                flow_v_FD.to("m³/h").magnitude,
                P_FD.head.to("kJ/kg").magnitude,
                None,
                P_FD.eff.magnitude,
            ]
            Curva[Nc, :].value = Gar
            Nc = Nc + 1

        QFD = np.array(Curva[0:Nc, 0].value)

        Id = list(np.argsort(QFD))

        if len(Id) > 1:
            Caux = Curva.value

            for i in range(Nc):
                Curva[i, :].value = Caux[Id[i]][:]

        ## Organização dos pontos da curva da segunda seção
        flow2_unit = FD_sheet["AP52"].value
        head2_unit = FD_sheet["AQ52"].value
        QFD2 = Q_(np.array(Curva2[0:Nc2, 0].value), flow2_unit)

        if Nc2 <= 0:
            Gar = [
                flow2_v_FD_v_FD.to("m³/h").magnitude,
                P2_FD.head.to("kJ/kg").magnitude,
                None,
                P2_FD.eff.magnitude,
            ]
            Curva2[Nc2, :].value = Gar
            Nc2 = Nc2 + 1
        elif Nc2 > 1 and min(abs(QFD2.to("m³/h").m - flow2_v_FD.to("m³/h").m)) == 0:
            Gar = [None, None, None, None]
            Curva2[Nc2, :].value = Gar
        else:
            Gar = [
                flow2_v_FD.to("m³/h").magnitude,
                P2_FD.head.to("kJ/kg").magnitude,
                None,
                P2_FD.eff.magnitude,
            ]
            Curva2[Nc2, :].value = Gar
            Nc2 = Nc2 + 1

        QFD2 = np.array(Curva2[0:Nc2, 0].value)

        Id2 = list(np.argsort(QFD2))

        if len(Id2) > 1:
            Caux2 = Curva2.value

            for i in range(Nc2):
                Curva2[i, :].value = Caux2[Id2[i]][:]

        ##################
        reynolds_correction = AT_sheet["C4"].value
        curve_shape = AT_sheet["C24"].value
        BL_leak = AT_sheet["C26"].value
        BF_leak = AT_sheet["C28"].value
        Div_leak = AT_sheet["C30"].value

        if curve_shape == "Yes":
            args_list = []
            P_exp = []
            for i in range(Nc):
                arg_dict = {
                    "eff": Curva[i, 3].value,
                    "flow_v": Q_(Curva[i, 0].value, flow1_unit),
                    "suc": sucFD,
                    "speed": speed_FD,
                    "head": Q_(Curva[i, 1].value, head1_unit),
                    "b": b,
                    "D": D,
                }
                args_list.append(arg_dict)

            with multiprocessing.Pool() as pool:
                P_exp += pool.map(ccp.impeller.create_points_parallel, args_list)

            imp_exp = P_exp

            args_list = []
            P2_exp = []
            for i in range(Nc2):
                arg_dict2 = {
                    "eff": Curva2[i, 3].value,
                    "flow_v": Q_(Curva2[i, 0].value, flow2_unit),
                    "suc": suc2FD,
                    "speed": speed_FD,
                    "head": Q_(Curva2[i, 1].value, head2_unit),
                    "b": b2,
                    "D": D2,
                }
                args_list.append(arg_dict2)

            with multiprocessing.Pool() as pool:
                P2_exp += pool.map(ccp.impeller.create_points_parallel, args_list)

            imp2_exp = P2_exp

        ### Reading and writing in the Actual Test Data Sheet

        Dados_AT_1 = AT_sheet["G7:W16"]
        Dados_AT_2 = AT_sheet["AE7:AO16"]

        for i in range(10):
            if Dados_AT_1[i, 5].value == None:
                N = i
                break

        Dados_AT_1 = Dados_AT_1[0:N, :]
        Dados_AT_2 = Dados_AT_2[0:N, :]

        P_AT = []
        P2_AT = []
        P_AT_Bal = []
        P_AT_Buf = []
        P2_AT_Bal = []
        P2_AT_Buf = []
        P_AT_Mdiv = []
        P_AT_M1d = []

        for i in range(N):

            speed_AT = Q_(Dados_AT_1[i, 16].value, AT_sheet.range("W6").value)
            N_ratio = speed_FD / speed_AT

            gas = int(Dados_AT_1[i, 15].value)

            GasesT = TG_sheet.range(
                TG_sheet.cells(5, 2 + 4 * (gas - 1)),
                TG_sheet.cells(21, 2 + 4 * (gas - 1)),
            ).value
            mol_fracT = TG_sheet.range(
                TG_sheet.cells(5, 4 + 4 * (gas - 1)),
                TG_sheet.cells(21, 4 + 4 * (gas - 1)),
            ).value

            fluid_AT = {}
            for count in range(len(GasesT)):
                if mol_fracT[count] > 0:
                    fluid_AT.update({GasesT[count]: mol_fracT[count]})

            Ps_AT = Q_(Dados_AT_1[i, 2].value, AT_sheet.range("I6").value)
            Ts_AT = Q_(Dados_AT_1[i, 3].value, AT_sheet.range("J6").value)

            Pd_AT = Q_(Dados_AT_1[i, 4].value, AT_sheet.range("K6").value)
            Td_AT = Q_(Dados_AT_1[i, 5].value, AT_sheet.range("L6").value)

            if Dados_AT_1[i, 1].value != None:
                V_test = True
                flow_v_AT = Q_(Dados_AT_1[i, 1].value, AT_sheet.range("H6").value)
            else:
                V_test = False
                flow_m_AT = Q_(Dados_AT_1[i, 0].value, AT_sheet.range("G6").value)

            sucAT = State.define(fluid=fluid_AT, p=Ps_AT, T=Ts_AT)
            dischAT = State.define(fluid=fluid_AT, p=Pd_AT, T=Td_AT)

            if V_test:
                flow_m_AT = flow_v_AT * sucAT.rho()
                Dados_AT_1[i, 0].value = flow_m_AT.to(AT_sheet["G6"].value).magnitude
            else:
                flow_v_AT = flow_m_AT / sucAT.rho()
                Dados_AT_1[i, 1].value = flow_v_AT.to(AT_sheet["H6"].value).magnitude

            if BL_leak == "Yes":
                P_AT_Bal.append(
                    [
                        None,
                        Q_(Dados_AT_1[i, 9].value, AT_sheet.range("P6").value),
                        Q_(Dados_AT_1[i, 10].value, AT_sheet.range("Q6").value),
                    ]
                )
                if Dados_AT_1[i, 8].value is not None:
                    P_AT_Bal[-1][0] = Q_(
                        Dados_AT_1[i, 8].value, AT_sheet.range("O6").value
                    )

            else:
                P_AT_Bal.append(
                    [
                        None,
                        Q_(
                            Dados_AT_2[i, 2].value, AT_sheet.range("AG6").value
                        ),  # Copying 2sec Suction info
                        Q_(Dados_AT_2[i, 3].value, AT_sheet.range("AH6").value),
                    ]
                )

            if BF_leak == "Yes":
                P_AT_Buf.append(
                    [
                        Q_(Dados_AT_1[i, 6].value, AT_sheet.range("M6").value),
                        Q_(Dados_AT_1[i, 7].value, AT_sheet.range("N6").value),
                    ]
                )
            else:
                P_AT_Buf.append(
                    [
                        None,
                        Q_(
                            Dados_AT_2[i, 3].value, AT_sheet.range("AH6").value
                        ),  # Copying 2sec Suction info
                    ]
                )
            fill_m_div = False
            fill_m1d = False
            if Div_leak == "Yes":
                div_f = Dados_AT_1[i, 11].value
                m1d_f = Dados_AT_1[i, 14].value
                if div_f is not None:
                    div_f = Q_(div_f, AT_sheet.range("R6").value)
                    m1d_f = None
                    fill_m1d = True
                else:
                    if m1d_f:
                        m1d_f = Q_(m1d_f, AT_sheet.range("U6").value)
                    fill_m_div = True

                P_AT_Mdiv.append(
                    [
                        div_f,
                        Q_(Dados_AT_1[i, 12].value, AT_sheet.range("S6").value),
                        Q_(Dados_AT_1[i, 13].value, AT_sheet.range("T6").value),
                    ]
                )
                P_AT_M1d.append(m1d_f)
            else:
                P_AT_Mdiv.append(
                    [
                        None,
                        Q_(
                            Dados_AT_2[i, 4].value, AT_sheet.range("AI6").value
                        ),  # Copying 2sec Disch info
                        Q_(Dados_AT_2[i, 5].value, AT_sheet.range("AJ6").value),
                    ]
                )
                P_AT_M1d.append(None)

            if AT_sheet["C8"].value == "Yes":
                Cas_Area = Q_(AT_sheet["D9"].value, "m**2")
                if AT_sheet["D11"].value == None:
                    Cas_Temperature = (sucAT.T() + dischAT.T()).to("kelvin") / 2
                else:
                    Cas_Temperature = Cas_Temperature = Q_(
                        AT_sheet["D11"].value, "degC"
                    ).to("kelvin")
                T_amb = Q_(AT_sheet["D13"].value, "degC").to("kelvin")
                heat_constant = Q_(AT_sheet["D15"].value, "W/m**2/kelvin")

            else:
                Cas_Area = None
                Cas_Temperature = None
                T_amb = None
                heat_constant = None

            P_AT.append(
                compressor.Point2Sec(
                    speed=speed_AT,
                    flow_m=flow_m_AT,
                    suc=sucAT,
                    disch=dischAT,
                    b=b,
                    D=D,
                    balance_line_flow_m=P_AT_Bal[-1][0],
                    seal_gas_flow_m=P_AT_Buf[-1][0],
                    seal_gas_temperature=P_AT_Buf[-1][1],
                    first_section_discharge_flow_m=P_AT_M1d[-1],
                    div_wall_flow_m=P_AT_Mdiv[-1][0],
                    end_seal_upstream_temperature=P_AT_Bal[-1][2],
                    end_seal_upstream_pressure=P_AT_Bal[-1][1],
                    div_wall_upstream_temperature=P_AT_Mdiv[-1][2],
                    div_wall_upstream_pressure=P_AT_Mdiv[-1][1],
                    casing_area=Cas_Area,
                    casing_temperature=Cas_Temperature,
                    ambient_temperature=T_amb,
                    convection_constant=heat_constant,
                )
            )

            ## Carregando dados da segunda seção

            speed2_AT = Q_(Dados_AT_2[i, 10].value, AT_sheet.range("AO6").value)
            N_ratio = speed_FD / speed2_AT

            gas2 = int(Dados_AT_2[i, 9].value)

            GasesT = TG_sheet.range(
                TG_sheet.cells(5, 2 + 4 * (gas - 1)),
                TG_sheet.cells(21, 2 + 4 * (gas - 1)),
            ).value
            mol_fracT = TG_sheet.range(
                TG_sheet.cells(5, 4 + 4 * (gas - 1)),
                TG_sheet.cells(21, 4 + 4 * (gas - 1)),
            ).value

            fluid2_AT = {}
            for count in range(len(GasesT)):
                if mol_fracT[count] > 0:
                    fluid2_AT.update({GasesT[count]: mol_fracT[count]})

            if Dados_AT_2[i, 1].value != None:
                V_test = True
                flow2_v_AT = Q_(Dados_AT_2[i, 1].value, AT_sheet.range("AF6").value)
            else:
                V_test = False
                flow2_m_AT = Q_(Dados_AT_2[i, 0].value, AT_sheet.range("AE6").value)

            Ps2_AT = Q_(Dados_AT_2[i, 2].value, AT_sheet.range("AG6").value)
            Ts2_AT = Q_(Dados_AT_2[i, 3].value, AT_sheet.range("AH6").value)

            Pd2_AT = Q_(Dados_AT_2[i, 4].value, AT_sheet.range("AI6").value)
            Td2_AT = Q_(Dados_AT_2[i, 5].value, AT_sheet.range("AJ6").value)

            suc2_AT = State.define(fluid=fluid2_AT, p=Ps2_AT, T=Ts2_AT)
            disch2_AT = State.define(fluid=fluid2_AT, p=Pd2_AT, T=Td2_AT)

            if BL_leak == "Yes":
                P2_AT_Bal.append(
                    [
                        Q_(Dados_AT_2[i, 6].value, AT_sheet.range("AK6").value),
                    ]
                )
            else:
                P2_AT_Bal.append(
                    [
                        None,
                    ]
                )

            if BF_leak == "Yes":
                P2_AT_Buf.append(
                    [
                        Q_(Dados_AT_2[i, 7].value, AT_sheet.range("AL6").value),
                    ]
                )
            else:
                P2_AT_Buf.append(
                    [
                        None,
                        Q_(
                            Dados_AT_2[i, 3].value, AT_sheet.range("AH6").value
                        ),  # Copying 2sec Suction info
                    ]
                )

            if V_test:
                flow2_m_AT = flow2_v_AT * suc2_AT.rho()
                Dados_AT_2[i, 0].value = flow2_m_AT.to(AT_sheet["AE6"].value).magnitude
            else:
                flow2_v_AT = flow2_m_AT / suc2_AT.rho()
                Dados_AT_2[i, 1].value = flow2_v_AT.to(AT_sheet["AF6"].value).magnitude

            if AT_sheet["C16"].value == "Yes":
                Cas_Area = Q_(AT_sheet["D17"].value, "m**2")
                if AT_sheet["D19"].value == None:
                    Cas_Temperature = (sucAT.T() + dischAT.T()).to("kelvin") / 2
                else:
                    Cas_Temperature = Cas_Temperature = Q_(
                        AT_sheet["D19"].value, "degC"
                    ).to("kelvin")
                T_amb = Q_(AT_sheet["D21"].value, "degC").to("kelvin")
                heat_constant = Q_(AT_sheet["D23"].value, "W/m**2/kelvin")

            else:
                Cas_Area = None
                Cas_Temperature = None
                T_amb = None
                heat_constant = None

            P2_AT.append(
                compressor.Point1Sec(
                    speed=speed2_AT,
                    flow_m=flow2_m_AT,
                    suc=suc2_AT,
                    disch=disch2_AT,
                    casing_area=Cas_Area,
                    casing_temperature=Cas_Temperature,
                    ambient_temperature=T_amb,
                    convection_constant=heat_constant,
                    balance_line_flow_m=P2_AT_Bal[-1][0],
                    seal_gas_flow_m=P2_AT_Buf[-1][0],
                    b=b2,
                    D=D2,
                )
            )

        if AT_sheet["Y3"].value == "Vazão Seção 1":
            QQ = np.array(Dados_AT_1[:, 1].value)
        else:
            QQ = []
            for i in range(N):
                QQ.append(P2_AT[i].flow_v.magnitude)

        Id = list(np.argsort(QQ))

        if len(Id) > 1:
            Daux = Dados_AT_1.value
            D2aux = Dados_AT_2.value
            Paux = [P for P in P_AT]
            P2aux = [P for P in P2_AT]
            for i in range(N):
                Dados_AT_1[i, :].value = Daux[Id[i]][:]
                Dados_AT_2[i, :].value = D2aux[Id[i]][:]
                P_AT[i] = Paux[Id[i]]
                P2_AT[i] = P2aux[Id[i]]
        logger.critical(
            f"P_FD: {P_FD} /// P_AT: {P_AT} /// P2_FD: {P2_FD} /// P2_AT: {P2_AT}"
        )
        imp_conv = compressor.BackToBack(
            guarantee_point_sec1=P_FD,
            test_points_sec1=P_AT,
            guarantee_point_sec2=P2_FD,
            test_points_sec2=P2_AT,
            speed=None,
            reynolds_correction=
        )

        P_AT = imp_conv.points_flange_t_sec1
        P2_AT = imp_conv.points_flange_t_sec2

        for i in range(N):
            if fill_m1d:
                Dados_AT_1[i, 14].value = (
                    P_AT[i].first_section_discharge_flow_m.to(AT_sheet["U6"].value).m
                )
            if fill_m_div:
                Dados_AT_1[i, 11].value = (
                    P_AT[i].div_wall_flow_m.to(AT_sheet["R6"].value).m
                )

        P_ATconv = []
        P2_ATconv = []

        Results_AT = AT_sheet["G22:AC32"]
        Results_AT.value = [[None] * len(Results_AT[0, :].value)] * 11
        Results_AT = Results_AT[0:N, :]

        Results2_AT = AT_sheet["G37:AC47"]
        Results2_AT.value = [[None] * len(Results2_AT[0, :].value)] * 11
        Results2_AT = Results2_AT[0:N, :]

        curve_shape = AT_sheet["C24"].value

        rug1 = AT_sheet["D5"].value
        rug2 = AT_sheet["D7"].value

        for i in range(N):
            P_ATconv.append(imp_conv.points_flange_sp_sec1[i])
            P2_ATconv.append(imp_conv.points_flange_sp_sec2[i])

            Results_AT[i, 21].value = ""
            Results2_AT[i, 21].value = ""

            ## Escrevendo resultados para a Seção 1
            Results_AT[i, 0].value = P_AT[i].volume_ratio.magnitude
            Results_AT[i, 1].value = (
                P_AT[i].volume_ratio.magnitude / P_FD.volume_ratio.magnitude
            )
            Results_AT[i, 2].value = P_AT[i].mach.magnitude
            Results_AT[i, 3].value = P_AT[i].mach.magnitude - P_FD.mach.magnitude
            Results_AT[i, 4].value = P_AT[i].reynolds.magnitude
            Results_AT[i, 5].value = (
                P_AT[i].reynolds.magnitude / P_FD.reynolds.magnitude
            )
            Results_AT[i, 6].value = P_AT[i].phi.magnitude
            Results_AT[i, 7].value = P_AT[i].phi.magnitude / P_FD.phi.magnitude
            Results_AT[i, 8].value = P_ATconv[i].disch.p().to("bar").magnitude
            Results_AT[i, 9].value = (
                P_ATconv[i].disch.p().to("bar").magnitude / Pd_FD.to("bar").magnitude
            )
            Results_AT[i, 10].value = P_AT[i].head.to("kJ/kg").magnitude
            Results_AT[i, 11].value = P_AT[i].head.to("kJ/kg").magnitude / max_H
            Results_AT[i, 12].value = P_ATconv[i].head.to("kJ/kg").magnitude
            Results_AT[i, 13].value = P_ATconv[i].head.to("kJ/kg").magnitude / max_H
            Results_AT[i, 14].value = P_ATconv[i].flow_v.to("m³/h").magnitude
            Results_AT[i, 15].value = (
                P_ATconv[i].flow_v.to("m³/h").magnitude
                / P_FD.flow_v.to("m³/h").magnitude
            )
            Results_AT[i, 16].value = P_AT[i].power.to("kW").magnitude
            Results_AT[i, 17].value = P_AT[i].power.to("kW").magnitude / min_Pow

            if AT_sheet["C25"].value == "Yes":

                HL_FD = Q_(
                    ((sucFD.T() + dischFD.T()).to("degC").magnitude * 0.8 / 2 - 25)
                    * 1.166
                    * AT_sheet["D26"].value,
                    "W",
                )
                HL_AT = Q_(
                    (
                        (P_AT[i].suc.T() + P_AT[i].disch.T()).to("degC").magnitude
                        * 0.8
                        / 2
                        - 25
                    )
                    * 1.166
                    * AT_sheet["D26"].value,
                    "W",
                )

                Results_AT[i, 18].value = (
                    (P_ATconv[i].power - HL_AT + HL_FD).to("kW").magnitude
                )
                Results_AT[i, 19].value = (P_ATconv[i].power - HL_AT + HL_FD).to(
                    "kW"
                ).magnitude / min_Pow

            else:
                Results_AT[i, 18].value = P_ATconv[i].power.to("kW").magnitude
                Results_AT[i, 19].value = P_ATconv[i].power.to("kW").magnitude / min_Pow

            Results_AT[i, 20].value = P_AT[i].eff.magnitude
            if P_AT[i].div_wall_flow_m:
                Results_AT[i, 22].value = (
                    imp_conv.points_flange_sp_sec1[i].div_wall_flow_m.to("kg/h").m
                )

            ## Escrevendo resultados para Seção 2

            Results2_AT[i, 0].value = P2_AT[i].volume_ratio.magnitude
            Results2_AT[i, 1].value = (
                P2_AT[i].volume_ratio.magnitude / P2_FD.volume_ratio.magnitude
            )
            Results2_AT[i, 2].value = P2_AT[i].mach.magnitude
            Results2_AT[i, 3].value = P2_AT[i].mach.magnitude - P2_FD.mach.magnitude
            Results2_AT[i, 4].value = P2_AT[i].reynolds.magnitude
            Results2_AT[i, 5].value = (
                P2_AT[i].reynolds.magnitude / P2_FD.reynolds.magnitude
            )
            Results2_AT[i, 6].value = P2_AT[i].phi.magnitude
            Results2_AT[i, 7].value = P2_AT[i].phi.magnitude / P2_FD.phi.magnitude
            Results2_AT[i, 8].value = P2_ATconv[i].disch.p().to("bar").magnitude
            Results2_AT[i, 9].value = (
                P2_ATconv[i].disch.p().to("bar").magnitude / Pd2_FD.to("bar").magnitude
            )
            Results2_AT[i, 10].value = P2_AT[i].head.to("kJ/kg").magnitude
            Results2_AT[i, 11].value = P2_AT[i].head.to("kJ/kg").magnitude / max_H2
            Results2_AT[i, 12].value = P2_ATconv[i].head.to("kJ/kg").magnitude
            Results2_AT[i, 13].value = P2_ATconv[i].head.to("kJ/kg").magnitude / max_H2
            Results2_AT[i, 14].value = P2_ATconv[i].flow_v.to("m³/h").magnitude
            Results2_AT[i, 15].value = (
                P2_ATconv[i].flow_v.to("m³/h").magnitude
                / P2_FD.flow_v.to("m³/h").magnitude
            )
            Results2_AT[i, 16].value = P2_AT[i].power.to("kW").magnitude
            Results2_AT[i, 17].value = P2_AT[i].power.to("kW").magnitude / min_Pow2

            if AT_sheet["C25"].value == "Yes":

                HL2_FD = Q_(
                    ((suc2FD.T() + disch2FD.T()).to("degC").magnitude * 0.8 / 2 - 25)
                    * 1.166
                    * AT_sheet["D28"].value,
                    "W",
                )
                HL2_AT = Q_(
                    (
                        (P2_AT[i].suc.T() + P2_AT[i].disch.T()).to("degC").magnitude
                        * 0.8
                        / 2
                        - 25
                    )
                    * 1.166
                    * AT_sheet["D28"].value,
                    "W",
                )

                Results2_AT[i, 18].value = (
                    (P2_ATconv[i].power - HL2_AT + HL2_FD).to("kW").magnitude
                )
                Results2_AT[i, 19].value = (P2_ATconv[i].power - HL2_AT + HL2_FD).to(
                    "kW"
                ).magnitude / min_Pow2

            else:
                Results2_AT[i, 18].value = P2_ATconv[i].power.to("kW").magnitude
                Results2_AT[i, 19].value = (
                    P2_ATconv[i].power.to("kW").magnitude / min_Pow2
                )

            Results2_AT[i, 20].value = P2_AT[i].eff.magnitude

        Phi = np.abs(1 - np.array(Results_AT[0:N, 7].value))
        Phi2 = np.abs(1 - np.array(Results2_AT[0:N, 7].value))

        IdG = []
        IdG2 = []

        for i in range(N):
            try:
                if Phi[i] < 0.04:
                    IdG.append(i)
            except:
                if Phi < 0.04:
                    IdG.append(i)
            try:
                if Phi2[i] < 0.04:
                    IdG2.append(i)
            except:
                if Phi2 < 0.04:
                    IdG2.append(i)

        if len(IdG) == 1:
            AT_sheet["G32:AC32"].value = Results_AT[IdG[0], :].value
        elif len(IdG) > 1:
            IdG = [int(k) for k in np.argsort(Phi)[0:2]]
            IdG = sorted(IdG)
            aux1 = np.array(Results_AT[IdG[0], :].value)
            aux2 = np.array(Results_AT[IdG[1], :].value)
            f = (1 - aux1[7]) / (aux2[7] - aux1[7])

            aux = aux1 + f * (aux2 - aux1)
            AT_sheet["G32:AC32"].value = aux
        else:

            AT_sheet["G32:AC32"].value = [None] * len(Results_AT[0, :].value)

        if len(IdG2) == 1:
            AT_sheet["G47:AC47"].value = Results2_AT[IdG2[0], :].value
        elif len(IdG2) > 1:
            IdG2 = [int(k) for k in np.argsort(Phi2)[0:2]]
            IdG2 = sorted(IdG2)
            aux1 = np.array(Results2_AT[IdG2[0], :].value)
            aux2 = np.array(Results2_AT[IdG2[1], :].value)
            f = (1 - aux1[7]) / (aux2[7] - aux1[7])

            aux = aux1 + f * (aux2 - aux1)
            AT_sheet["G47:AC47"].value = aux
        else:

            AT_sheet["G47:AC47"].value = [None] * len(Results2_AT[0, :].value)

        AT_sheet["Z9"].value = "Calculado"

    ###########################################
    ### INÍCIO DA ROTINA DE TEST PROCEDURE
    ############################################

    if TP_sheet["R19"].value != None:
        TP_sheet["R19"].value = None
        TP_sheet["R23"].value = "Calculando..."

        FD_sheet = wb.sheets["DataSheet"]

        ### Reading and writing SECTION 1 from the FD sheet

        Ps_FD = Q_(FD_sheet["T23"].value, "bar")
        Ts_FD = Q_(FD_sheet.range("T24").value, "degC")

        Pd_FD = Q_(FD_sheet.range("T31").value, "bar")
        Td_FD = Q_(FD_sheet.range("T32").value, "degC")

        eff_FD = Q_(FD_sheet.range("T41").value, "dimensionless")
        Pow_FD = Q_(FD_sheet.range("T35").value, "kW")
        H_FD = Q_(FD_sheet.range("T40").value, "J/kg")

        if FD_sheet.range("T21").value == None:
            V_test = True
            flow_v_FD = Q_(FD_sheet.range("T29").value, "m³/h")
        else:
            V_test = False
            flow_m_FD = Q_(FD_sheet.range("T21").value, "kg/h")

        # flow_m_FD = Q_(FD_sheet.range('T21').value,'kg/h')
        # flow_v_FD = Q_(FD_sheet.range('T29').value,'m**3/h')

        speed_FD = Q_(FD_sheet.range("T38").value, "rpm")

        D = Q_(FD_sheet.range("AB132").value, "mm")
        b = Q_(FD_sheet.range("AQ132").value, "mm")

        GasesFD = FD_sheet.range("B69:B85").value
        mol_fracFD = FD_sheet.range("K69:K85").value

        fluid_FD = {GasesFD[i]: mol_fracFD[i] for i in range(len(GasesFD))}

        sucFD = State.define(fluid=fluid_FD, p=Ps_FD, T=Ts_FD)

        if V_test:
            flow_m_FD = flow_v_FD * sucFD.rho()
            FD_sheet["AS34"].value = flow_m_FD.to("kg/h").magnitude
            FD_sheet["AQ34"].value = "Mass Flow"
            FD_sheet["AU34"].value = "kg/h"
        else:
            flow_v_FD = flow_m_FD / sucFD.rho()
            FD_sheet["AS34"].value = flow_v_FD.to("m³/h").magnitude
            FD_sheet["AQ34"].value = "Inlet Volume Flow"
            FD_sheet["AU34"].value = "m³/h"

        dischFD = State.define(fluid=fluid_FD, p=Pd_FD, T=Td_FD)

        P_FD = ccp.Point(
            speed=speed_FD, flow_m=flow_m_FD, suc=sucFD, disch=dischFD, b=b, D=D
        )

        def update_head(H):
            global P_FD_eff
            P_FD_eff = ccp.Point(
                speed=speed_FD,
                flow_m=flow_m_FD,
                suc=sucFD,
                eff=eff_FD,
                head=Q_(H, "J/kg"),
                b=b,
                D=D,
            )

            P = P_FD_eff.disch.p().to("Pa").magnitude

            return P - Pd_FD.to("Pa").magnitude

        newton(
            update_head,
            ccp.point.head_pol(suc=P_FD.suc, disch=P_FD.disch).to("J/kg").magnitude,
            tol=1,
        )

        max_H = max(
            [
                P_FD.head.to("kJ/kg").magnitude,
                P_FD_eff.head.to("kJ/kg").magnitude,
                H_FD.to("kJ/kg").magnitude,
            ]
        )
        min_Pow = min(
            [
                P_FD.power.to("kW").magnitude,
                P_FD_eff.power.to("kW").magnitude,
                Pow_FD.to("kW").magnitude,
            ]
        )

        FD_sheet["AS25"].value = P_FD.mach.magnitude
        FD_sheet["AS26"].value = P_FD.reynolds.magnitude
        FD_sheet["AS27"].value = 1 / P_FD.volume_ratio.magnitude
        FD_sheet["AS28"].value = P_FD_eff.head.to("J/kg").magnitude
        FD_sheet["AS29"].value = P_FD_eff.disch.T().to("degC").magnitude
        FD_sheet["AS30"].value = P_FD_eff.power.to("kW").magnitude
        FD_sheet["AS31"].value = P_FD.head.to("J/kg").magnitude
        FD_sheet["AS32"].value = P_FD.eff.magnitude
        FD_sheet["AS33"].value = P_FD.power.to("kW").magnitude

        ### Reading and writing SECTION 2 from the FD sheet
        Pd2_FD = Q_(FD_sheet.range("Z31").value, "bar")
        Td2_FD = Q_(FD_sheet.range("Z32").value, "degC")

        eff2_FD = Q_(FD_sheet.range("Z41").value, "dimensionless")
        Pow2_FD = Q_(FD_sheet.range("Z35").value, "kW")
        H2_FD = Q_(FD_sheet.range("Z40").value, "J/kg")

        D2 = Q_(FD_sheet.range("AB133").value, "mm")
        b2 = Q_(FD_sheet.range("AQ133").value, "mm")

        Ps2_FD = Q_(FD_sheet.range("Z23").value, "bar")
        Ts2_FD = Q_(FD_sheet.range("Z24").value, "degC")
        GasesFD = FD_sheet.range("B69:B85").value
        mol_frac2_FD = FD_sheet.range("Q69:Q85").value

        fluid2_FD = {GasesFD[i]: mol_frac2_FD[i] for i in range(len(GasesFD))}

        suc2FD = State.define(fluid=fluid2_FD, p=Ps2_FD, T=Ts2_FD)
        suc2FD_eff = suc2FD
        disch2FD = State.define(fluid=fluid2_FD, p=Pd2_FD, T=Td2_FD)
        if V_test:
            flow2_v_FD = Q_(FD_sheet.range("Z29").value, "m³/h")
            flow2_m_FD = flow2_v_FD * suc2FD.rho()
            FD_sheet["AT34"].value = flow2_m_FD.to("kg/h").magnitude
        else:
            flow2_m_FD = flow_m_FD
            flow2_v_FD = flow2_m_FD / suc2FD.rho()
            FD_sheet["AT34"].value = flow2_v_FD.to("m³/h").magnitude

        P2_FD = ccp.Point(
            speed=speed_FD,
            flow_m=flow2_m_FD,
            suc=suc2FD,
            disch=disch2FD,
            b=b2,
            D=D2,
        )

        def update_head2(H):
            global P2_FD_eff
            P2_FD_eff = ccp.Point(
                speed=speed_FD,
                flow_m=flow2_m_FD,
                suc=suc2FD_eff,
                eff=eff2_FD,
                head=Q_(H, "J/kg"),
                b=b,
                D=D,
            )

            P2 = P2_FD_eff.disch.p().to("Pa").magnitude

            return P2 - Pd2_FD.to("Pa").magnitude

        newton(
            update_head2,
            ccp.point.head_pol(suc=P2_FD.suc, disch=P2_FD.disch).to("J/kg").magnitude,
            tol=1,
        )

        max_H2 = max(
            [
                P2_FD.head.to("kJ/kg").magnitude,
                P2_FD_eff.head.to("kJ/kg").magnitude,
                H2_FD.to("kJ/kg").magnitude,
            ]
        )
        min_Pow2 = min(
            [
                P2_FD.power.to("kW").magnitude,
                P2_FD_eff.power.to("kW").magnitude,
                Pow2_FD.to("kW").magnitude,
            ]
        )

        FD_sheet["AT25"].value = P2_FD.mach.magnitude
        FD_sheet["AT26"].value = P2_FD.reynolds.magnitude
        FD_sheet["AT27"].value = P2_FD.volume_ratio.magnitude
        FD_sheet["AT28"].value = P2_FD_eff.head.to("J/kg").magnitude
        FD_sheet["AT29"].value = P2_FD_eff.disch.T().to("degC").magnitude
        FD_sheet["AT30"].value = P2_FD_eff.power.to("kW").magnitude
        FD_sheet["AT31"].value = P2_FD.head.to("J/kg").magnitude
        FD_sheet["AT32"].value = P2_FD.eff.magnitude
        FD_sheet["AT33"].value = P2_FD.power.to("kW").magnitude

        FD_sheet["K90"].value = sucFD.molar_mass().to("g/mol").magnitude
        FD_sheet["Q90"].value = suc2FD.molar_mass().to("g/mol").magnitude

        ### End of Reading and writing in the FD sheet

        ### Reading and writing SECTION 1 from the TP sheet

        Ps_TP = Q_(TP_sheet.range("L6").value, TP_sheet.range("M6").value)
        Ts_TP = Q_(TP_sheet.range("N6").value, TP_sheet.range("O6").value)

        Pd_TP = Q_(TP_sheet.range("P6").value, TP_sheet.range("Q6").value)

        if TP_sheet.range("F6").value == None:
            V_test = True
            flow_v_TP = Q_(TP_sheet.range("H6").value, TP_sheet.range("I6").value)
        else:
            V_test = False
            flow_m_TP = Q_(TP_sheet.range("F6").value, TP_sheet.range("G6").value)

        speed_TP = Q_(TP_sheet.range("J6").value, TP_sheet.range("K6").value)

        GasesT = TP_sheet.range("B4:B20").value
        mol_fracT = TP_sheet.range("D4:D20").value

        fluid_TP = {}
        for i in range(len(GasesT)):
            if mol_fracT[i] > 0:
                fluid_TP.update({GasesT[i]: mol_fracT[i]})

        sucTP = State.define(fluid=fluid_TP, p=Ps_TP, T=Ts_TP)
        dischTPk = State.define(fluid=fluid_TP, p=Pd_TP, s=sucTP.s())

        hd_TP = sucTP.h() + (dischTPk.h() - sucTP.h()) / ccp.point.eff_isentropic(
            suc=P_FD.suc, disch=P_FD.disch
        )
        dischTP = State.define(fluid=fluid_TP, p=Pd_TP, h=hd_TP)

        if V_test:
            flow_m_TP = flow_v_TP * sucTP.rho()
            TP_sheet["F6"].value = flow_m_TP.to(TP_sheet["G6"].value).magnitude
        else:
            flow_v_TP = flow_m_TP / sucTP.rho()
            TP_sheet["H6"].value = flow_v_TP.to(TP_sheet["I6"].value).magnitude

        P_TP = ccp.Point(
            speed=speed_TP, flow_m=flow_m_TP, suc=sucTP, disch=dischTP, b=b, D=D
        )

        # Heat loss consideration - power and efficiency  correction
        if TP_sheet["C25"].value == "Yes":
            Cas1_Area = Q_(TP_sheet["D26"].value, "m**2")
            if TP_sheet["D28"].value == None:
                Cas1_Temperature = (sucTP.T() + dischTP.T()).to("kelvin") / 2
            else:
                Cas1_Temperature = Cas_Temperature = Q_(
                    TP_sheet["D28"].value, "degC"
                ).to("kelvin")
            T_amb = Q_(TP_sheet["D30"].value, "degC").to("kelvin")
            heat_constant = Q_(TP_sheet["D32"].value, "W/(m²*degK)")
        else:
            Cas1_Area = None
            Cas1_Temperature = None
            T_amb = None
            heat_constant = None

        P_TP = ccp.Point(
            speed=speed_TP,
            flow_m=flow_m_TP,
            suc=sucTP,
            disch=dischTP,
            casing_area=Cas1_Area,
            casing_temperature=Cas1_Temperature,
            ambient_temperature=T_amb,
            convection_constant=heat_constant,
            b=b,
            D=D,
        )

        # P_TPconv = Imp_TP._calc_from_speed(point=P_TP,new_speed=P_FD.speed)

        if TP_sheet["C23"].value == "Yes":

            P_TPconv = reynolds_corr(
                P_AT=P_TP,
                P_FD=P_FD,
                rug=TP_sheet["D24"].value,
            )

            TP_sheet["H37"].value = P_TPconv.eff.m

        else:

            N_ratio = speed_FD / speed_TP

            P_TPconv = ccp.Point(
                suc=P_FD.suc,
                eff=P_TP.eff,
                speed=speed_FD,
                flow_v=P_TP.flow_v * N_ratio,
                head=P_TP.head * N_ratio**2,
                b=b,
                D=D,
            )
            TP_sheet["H37"].value = ""

        TP_sheet["R6"].value = dischTP.T().to(TP_sheet["S6"].value).magnitude
        TP_sheet["G19"].value = P_TP.volume_ratio.magnitude
        TP_sheet["H19"].value = (
            P_TP.volume_ratio.magnitude / P_FD.volume_ratio.magnitude
        )
        TP_sheet["G20"].value = P_TP.mach.magnitude
        TP_sheet["H21"].value = P_TP.mach.magnitude - P_FD.mach.magnitude
        TP_sheet["G22"].value = P_TP.reynolds.magnitude
        TP_sheet["H23"].value = P_TP.reynolds.magnitude / P_FD.reynolds.magnitude
        TP_sheet["G24"].value = P_TP.phi.magnitude
        TP_sheet["H25"].value = P_TP.phi.magnitude / P_FD.phi.magnitude
        TP_sheet["G26"].value = P_TP.psi.magnitude
        TP_sheet["H27"].value = P_TP.psi.magnitude / P_FD.psi.magnitude
        TP_sheet["G28"].value = P_TP.head.to("kJ/kg").magnitude
        TP_sheet["H29"].value = P_TP.head.to("kJ/kg").magnitude / max_H
        TP_sheet["G30"].value = P_TPconv.head.to("kJ/kg").magnitude
        TP_sheet["H31"].value = P_TPconv.head.to("kJ/kg").magnitude / max_H
        TP_sheet["G32"].value = P_TP.power.to("kW").magnitude
        TP_sheet["H33"].value = P_TP.power.to("kW").magnitude / min_Pow

        TP_sheet["G34"].value = P_TPconv.power.to("kW").magnitude
        TP_sheet["H35"].value = P_TPconv.power.to("kW").magnitude / min_Pow

        TP_sheet["G36"].value = P_TP.eff.magnitude

        ### Reading and writing SECTION 2 from the TP sheet

        Ps2_TP = Q_(TP_sheet.range("L14").value, TP_sheet.range("M14").value)
        Ts2_TP = Q_(TP_sheet.range("N14").value, TP_sheet.range("O14").value)

        Pd2_TP = Q_(TP_sheet.range("P14").value, TP_sheet.range("Q14").value)

        speed2_TP = Q_(TP_sheet.range("J14").value, TP_sheet.range("K14").value)

        if TP_sheet.range("F14").value == None:
            V_test = True
            flow2_v_TP = Q_(TP_sheet.range("H14").value, TP_sheet.range("I14").value)
        else:
            V_test = False
            flow2_m_TP = Q_(TP_sheet.range("F14").value, TP_sheet.range("G14").value)

        fluid2_TP = fluid_TP

        suc2TP = State.define(fluid=fluid2_TP, p=Ps2_TP, T=Ts2_TP)
        disch2TPk = State.define(fluid=fluid2_TP, p=Pd2_TP, s=suc2TP.s())

        hd2_TP = sucTP.h() + (disch2TPk.h() - suc2TP.h()) / ccp.point.eff_isentropic(
            suc=P2_FD.suc, disch=P2_FD.disch
        )
        disch2TP = State.define(fluid=fluid2_TP, p=Pd2_TP, h=hd2_TP)

        TP_sheet["R14"].value = disch2TP.T().to(TP_sheet.range("S14").value).magnitude

        if V_test:
            flow2_m_TP = flow2_v_TP * suc2TP.rho()
            TP_sheet["F14"].value = flow2_m_TP.to(TP_sheet["G14"].value).magnitude
        else:
            flow2_v_TP = flow2_m_TP / suc2TP.rho()
            TP_sheet["H14"].value = flow2_v_TP.to(TP_sheet["I14"].value).magnitude

        P2_TP = ccp.Point(
            speed=speed2_TP, flow_m=flow2_m_TP, suc=suc2TP, disch=disch2TP, b=b2, D=D2
        )

        # Heat loss consideration - power and efficiency  correction
        if TP_sheet["C33"].value == "Yes":
            Cas2_Area = Q_(TP_sheet["D34"].value, "m**2")
            if TP_sheet["D36"].value == None:
                Cas2_Temperature = (sucTP.T() + dischTP.T()).to("kelvin") / 2
            else:
                Cas2_Temperature = Cas_Temperature = Q_(
                    TP_sheet["D36"].value, "degC"
                ).to("kelvin")
            T_amb = Q_(TP_sheet["D38"].value, "degC").to("kelvin")
            heat_constant = Q_(TP_sheet["D40"].value, "W/(m²*degK)")
        else:
            Cas2_Area = None
            Cas2_Temperature = None
            T_amb = None
            heat_constant = None

        P2_TP = ccp.Point(
            speed=speed2_TP,
            flow_m=flow2_m_TP,
            suc=suc2TP,
            disch=disch2TP,
            casing_area=Cas2_Area,
            casing_temperature=Cas2_Temperature,
            ambient_temperature=T_amb,
            convection_constant=heat_constant,
            b=b2,
            D=D2,
        )

        if TP_sheet["C23"].value == "Yes":

            P2_TPconv = reynolds_corr(
                P_AT=P2_TP,
                P_FD=P2_FD,
                rug=TP_sheet["D24"].value,
            )
            TP_sheet["M37"].value = P2_TPconv.eff.m
        else:

            N2_ratio = speed_FD / speed2_TP

            P2_TPconv = ccp.Point(
                suc=P2_FD.suc,
                eff=P2_TP.eff,
                speed=speed_FD,
                flow_v=P2_TP.flow_v * N2_ratio,
                head=P2_TP.head * N2_ratio**2,
                b=b2,
                D=D2,
            )
            TP_sheet["M37"].value = ""

        TP_sheet["R14"].value = disch2TP.T().to(TP_sheet.range("S14").value).magnitude
        TP_sheet["L19"].value = P2_TP.volume_ratio.magnitude
        TP_sheet["M19"].value = (
            P2_TP.volume_ratio.magnitude / P2_FD.volume_ratio.magnitude
        )
        TP_sheet["L20"].value = P2_TP.mach.magnitude
        TP_sheet["M21"].value = P2_TP.mach.magnitude - P2_FD.mach.magnitude
        TP_sheet["L22"].value = P2_TP.reynolds.magnitude
        TP_sheet["M23"].value = P2_TP.reynolds.magnitude / P2_FD.reynolds.magnitude
        TP_sheet["L24"].value = P2_TP.phi.magnitude
        TP_sheet["M25"].value = P2_TP.phi.magnitude / P2_FD.phi.magnitude
        TP_sheet["L26"].value = P2_TP.psi.magnitude
        TP_sheet["M27"].value = P2_TP.psi.magnitude / P2_FD.psi.magnitude
        TP_sheet["L28"].value = P2_TP.head.to("kJ/kg").magnitude
        TP_sheet["M29"].value = P2_TP.head.to("kJ/kg").magnitude / max_H2
        TP_sheet["L30"].value = P2_TPconv.head.to("kJ/kg").magnitude
        TP_sheet["M31"].value = P2_TPconv.head.to("kJ/kg").magnitude / max_H2
        TP_sheet["L32"].value = P2_TP.power.to("kW").magnitude
        TP_sheet["M33"].value = P2_TP.power.to("kW").magnitude / min_Pow2
        TP_sheet["L34"].value = P2_TPconv.power.to("kW").magnitude
        TP_sheet["M35"].value = P2_TPconv.power.to("kW").magnitude / min_Pow2

        TP_sheet["L36"].value = P2_TP.eff.magnitude

        TP_sheet["R23"].value = "Calculado"

    if CF_sheet["L4"].value != None:
        global qm

        CF_sheet["L8"].value = "Calculando..."

        CF_sheet["L4"].value = None

        Units = CF_sheet["C4:I4"].value

        GasesT = AT_sheet.range("B4:B20").value
        mol_fracT = AT_sheet.range("D4:D20").value

        fluid_AT = {}
        for i in range(len(GasesT)):
            if mol_fracT[i] > 0:
                fluid_AT.update({GasesT[i]: mol_fracT[i]})

        i = 4
        data = np.array(CF_sheet[i, 2:8].value)

        while len(data[data == None]) == 0:

            # if len(data[data==None])==0:

            D = Q_(float(data[0]), Units[0])
            d = Q_(float(data[1]), Units[1])
            P1 = Q_(float(data[2]), Units[2])
            T1 = Q_(float(data[3]), Units[3])
            dP = Q_(float(data[4]), Units[4])
            tappings = data[5]

            P2 = P1 - dP

            State_FO = State.define(fluid=fluid_AT, p=P1, T=T1)

            beta = d / D
            mu = State_FO.viscosity()
            rho = State_FO.rho()
            k = State_FO.kv()

            e = 1 - (0.351 + 0.256 * (beta**4) + 0.93 * (beta**8)) * (
                1 - (P2 / P1) ** (1 / k)
            )

            if tappings == "corner":
                L1 = L2 = 0
            elif tappings == "D D/2":
                L1 = 1
                L2 = 0.47
            elif tappings == "flange":
                L1 = L2 = Q_(0.0254, "m") / D

            M2 = 2 * L2 / (1 - beta)

            def update_Re(Re):
                global qm

                Re = Q_(Re, "dimensionless")
                # calc C
                C = (
                    0.5961
                    + 0.0261 * beta**2
                    - 0.216 * beta**8
                    + 0.000521 * (1e6 * beta / Re) ** 0.7
                    + (0.0188 + 0.0063 * (19000 * beta / Re) ** 0.8)
                    * beta**3.5
                    * (1e6 / Re) ** 0.3
                    + (0.043 + 0.080 * np.e ** (-10 * L1) - 0.123 * np.e ** (-7 * L1))
                    * (1 - 0.11 * (19000 * beta / Re) ** 0.8)
                    * (beta**4 / (1 - beta**4))
                    - 0.031 * (M2 - 0.8 * M2**1.1) * beta**1.3
                )

                if D < Q_(71.12, "mm"):
                    C += 0.011 * (0.75 - beta) * (2.8 - D / Q_(25.4, "mm"))

                qm = (
                    C
                    / (np.sqrt(1 - beta**4))
                    * e
                    * (np.pi / 4)
                    * d**2
                    * np.sqrt(2 * dP * rho)
                )

                Re_qm = (4 * qm / (mu * np.pi * D)).to("dimensionless").magnitude

                return abs(Re_qm - Re.magnitude)

            newton(update_Re, 1e8, tol=1e-5)

            Re = D / mu * qm / (np.pi * D**2 / 4)

            CF_sheet[i, 8].value = qm.to(Units[-1]).magnitude

            i += 1
            data = np.array(CF_sheet[i, 2:8].value)

        CF_sheet["A1"].value = "Calculado!"
