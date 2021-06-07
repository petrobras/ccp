import os

FileName = os.path.basename(__file__)[:-3]


from xlwings import Book

wb = Book(FileName)  # connect to an existing file in the current working directory
AT_sheet = wb.sheets["Actual Test Data"]
TP_sheet = wb.sheets["Test Procedure Data"]
FD_sheet = wb.sheets["DataSheet"]
CF_sheet = wb.sheets["CalcFlow"]

AT_sheet["T11"].value = "Carregando bibliotecas..."
TP_sheet["R23"].value = "Carregando bibliotecas..."
CF_sheet["A1"].value = "Carregando bibliotecas..."

import xlwings as xw
import os
from time import sleep

try:
    aux = os.environ["RPprefix"]
except:
    os.environ["RPprefix"] = "C:\\Users\\Public\\REFPROP"
import ccp
from ccp import State, Q_
import numpy as np
from scipy.optimize import newton

global P_FD_eff, P2_FD_eff


AT_sheet["T7"].value = None
TP_sheet["R19"].value = None
FD_sheet["A1"].value = None
FD_sheet["AN5"].value = "Yes"
CF_sheet["K4"].value = None

FD_status = FD_sheet["A1:AV158"].value

AT_sheet["T11"].value = "READY!"
TP_sheet["R23"].value = "READY!"

Open_file = True

while Open_file:

    wb = xw.Book(
        FileName
    )  # connect to an existing file in the current working directory

    AT_sheet = wb.sheets["Actual Test Data"]
    TP_sheet = wb.sheets["Test Procedure Data"]
    FD_sheet = wb.sheets["DataSheet"]
    CF_sheet = wb.sheets["CalcFlow"]

    if FD_sheet["A1"].value != None:
        FD_sheet["A1"].value = None
        Open_file = False

    if AT_sheet["T7"].value != None:

        AT_sheet["T7"].value = None
        AT_sheet["T11"].value = "Calculando..."

        if FD_sheet["AN5"].value == "Yes":

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

            # Processando dados de projeto do Side Stream

            SS_config = FD_sheet.range("W18").value

            Ps2_FD = Pd_FD * 0.995
            if SS_config == "IN":
                TSS_FD = Q_(FD_sheet.range("W24").value, "degC")
            else:
                TSS_FD = Td_FD

            Pd2_FD = Q_(FD_sheet.range("Z31").value, "bar")
            Td2_FD = Q_(FD_sheet.range("Z32").value, "degC")

            eff2_FD = Q_(FD_sheet.range("Z41").value, "dimensionless")
            Pow2_FD = Q_(FD_sheet.range("Z35").value, "kW")
            H2_FD = Q_(FD_sheet.range("Z40").value, "J/kg")

            if FD_sheet.range("W21").value == None:
                V_test = True
                flowSS_v_FD = Q_(FD_sheet.range("W29").value, "m³/h")
            else:
                V_test = False
                flowSS_m_FD = Q_(FD_sheet.range("W21").value, "kg/h")

            D2 = Q_(FD_sheet.range("AB133").value, "mm")
            b2 = Q_(FD_sheet.range("AQ133").value, "mm")

            if SS_config == "IN":
                GasesFD = FD_sheet.range("B69:B85").value
                mol_fracSS_FD = FD_sheet.range("N69:N85").value

                fluidSS_FD = {GasesFD[i]: mol_fracSS_FD[i] for i in range(len(GasesFD))}
            else:
                fluidSS_FD = fluid_FD

            SS_FD = State.define(fluid=fluidSS_FD, p=Ps2_FD, T=TSS_FD)

            if V_test:
                flowSS_m_FD = flowSS_v_FD * SS_FD.rho()
                FD_sheet["AS36"].value = flowSS_m_FD.to("kg/h").magnitude
                FD_sheet["AQ36"].value = "SS Mass Flow"
                FD_sheet["AU36"].value = "kg/h"
            else:
                flowSS_v_FD = flowSS_m_FD / SS_FD.rho()
                FD_sheet["AS36"].value = flowSS_v_FD.to("m³/h").magnitude
                FD_sheet["AQ36"].value = "SS Volume Flow"
                FD_sheet["AU36"].value = "m³/h"

            if SS_config == "IN":
                flow2_m_FD = flow_m_FD + flowSS_m_FD
                RSS = flowSS_m_FD / flow2_m_FD
                R1 = flow_m_FD / flow2_m_FD

                fluid2_FD = {
                    GasesFD[i]: mol_fracSS_FD[i] * RSS + mol_fracFD[i] * R1
                    for i in range(len(GasesFD))
                }
                h2_FD = dischFD.h() * R1 + SS_FD.h() * RSS
                h2_FD_eff = P_FD_eff.disch.h() * R1 + SS_FD.h() * RSS

                suc2FD = State.define(fluid=fluid2_FD, p=Ps2_FD, h=h2_FD)
                suc2FD_eff = State.define(fluid=fluid2_FD, p=Ps2_FD, h=h2_FD_eff)
                disch2FD = State.define(fluid=fluid2_FD, p=Pd2_FD, T=Td2_FD)
                FD_sheet["AT35"].value = suc2FD.T().to("degC").magnitude
            else:
                fluid2_FD = fluid_FD
                flow2_m_FD = flow_m_FD - flowSS_m_FD

                suc2FD = State.define(fluid=fluid2_FD, p=Ps2_FD, T=Td_FD)
                suc2_eff = P_FD_eff.disch
                disch2FD = State.define(fluid=fluid2_FD, p=Pd2_FD, T=Td2_FD)
                FD_sheet["AT35"].value = suc2FD.T().to("degC").magnitude

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
                ccp.point.head_pol(suc=P2_FD.suc, disch=P2_FD.disch)
                .to("J/kg")
                .magnitude,
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

            if V_test:

                FD_sheet["AT34"].value = P2_FD.flow_m.to("kg/h").magnitude
            else:

                FD_sheet["AT34"].value = P2_FD.flow_v.to("m³/h").magnitude

            Q1d_FD = flow_m_FD / dischFD.rho()
            FD_sheet["AS37"].value = (
                flowSS_v_FD.to("m³/h").magnitude / Q1d_FD.to("m³/h").magnitude
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
            FD_sheet["N90"].value = SS_FD.molar_mass().to("g/mol").magnitude

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

        QFD = np.array(Curva[0:Nc, 0].value)

        if Nc > 0 and min(abs(QFD - flow_v_FD.to("m³/h").magnitude)) == 0:
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

        QFD2 = np.array(Curva2[0:Nc2, 0].value)

        if Nc2 > 0 and min(abs(QFD2 - P2_FD.flow_v.to("m³/h").magnitude)) == 0:
            Gar = [None, None, None, None]
            Curva2[Nc2, :].value = Gar

        else:
            Gar = [
                P2_FD.flow_v.to("m³/h").magnitude,
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

        ### Reading and writing in the Actual Test Data Sheet

        Dados_AT = AT_sheet["G7:S16"]

        for i in range(10):
            if Dados_AT[i, 5].value == None:
                N = i
                break

        Dados_AT = Dados_AT[0:N, :]

        speed_AT = Q_(AT_sheet.range("H4").value, AT_sheet.range("I4").value)
        N_ratio = speed_FD / speed_AT

        GasesT = AT_sheet.range("B4:B20").value
        mol_fracT = AT_sheet.range("D4:D20").value

        P_AT = []
        P2_AT = []

        fluid_AT = {}
        for i in range(len(GasesT)):
            if mol_fracT[i] > 0:
                fluid_AT.update({GasesT[i]: mol_fracT[i]})

        for i in range(N):

            Ps_AT = Q_(Dados_AT[i, 2].value, AT_sheet.range("I6").value)
            Ts_AT = Q_(Dados_AT[i, 3].value, AT_sheet.range("J6").value)

            Pd_AT = Q_(Dados_AT[i, 4].value, AT_sheet.range("K6").value)
            Td_AT = Q_(Dados_AT[i, 5].value, AT_sheet.range("L6").value)

            if Dados_AT[i, 1].value != None:
                V_test = True
                flow_v_AT = Q_(Dados_AT[i, 1].value, AT_sheet.range("H6").value)
            else:
                V_test = False
                flow_m_AT = Q_(Dados_AT[i, 0].value, AT_sheet.range("G6").value)

            sucAT = State.define(fluid=fluid_AT, p=Ps_AT, T=Ts_AT)
            dischAT = State.define(fluid=fluid_AT, p=Pd_AT, T=Td_AT)

            if V_test:
                flow_m_AT = flow_v_AT * sucAT.rho()
                Dados_AT[i, 0].value = flow_m_AT.to(AT_sheet["G6"].value).magnitude
            else:
                flow_v_AT = flow_m_AT / sucAT.rho()
                Dados_AT[i, 1].value = flow_v_AT.to(AT_sheet["H6"].value).magnitude

            P_AT.append(
                ccp.Point(
                    speed=speed_AT, flow_m=flow_m_AT, suc=sucAT, disch=dischAT, b=b, D=D
                )
            )

            ## Carregando dados da segunda seção

            Ps2_AT = Pd_AT * 0.995

            if SS_config == "IN":
                TSS_AT = Q_(Dados_AT[i, 8].value, AT_sheet.range("O6").value)
            else:
                TSS_AT = Td_AT

            Pd2_AT = Q_(Dados_AT[i, 9].value, AT_sheet.range("P6").value)
            Td2_AT = Q_(Dados_AT[i, 10].value, AT_sheet.range("Q6").value)

            if Dados_AT[i, 7].value != None:
                V_test = True
                flowSS_v_AT = Q_(Dados_AT[i, 7].value, AT_sheet.range("N6").value)
            else:
                V_test = False
                flowSS_m_AT = Q_(Dados_AT[i, 6].value, AT_sheet.range("M6").value)

            fluidSS_AT = fluid_AT

            SS_AT = State.define(fluid=fluidSS_AT, p=Ps2_AT, T=TSS_AT)

            if V_test:
                flowSS_m_AT = flowSS_v_AT * SS_AT.rho()
                Dados_AT[i, 6].value = flowSS_m_AT.to(
                    AT_sheet.range("M6").value
                ).magnitude
            else:
                flowSS_v_AT = flowSS_m_AT / SS_AT.rho()
                Dados_AT[i, 7].value = flowSS_v_AT.to(
                    AT_sheet.range("N6").value
                ).magnitude

            if SS_config == "IN":
                flow2_m_AT = flow_m_AT + flowSS_m_AT
                RSS = flowSS_m_AT / flow2_m_AT
                R1 = flow_m_AT / flow2_m_AT

                fluid2_AT = fluid_AT
                h2_AT = dischAT.h() * R1 + SS_AT.h() * RSS

                suc2AT = State.define(fluid=fluid2_AT, p=Ps2_AT, h=h2_AT)
                disch2AT = State.define(fluid=fluid2_AT, p=Pd2_AT, T=Td2_AT)

            else:
                fluid2_AT = fluid_AT
                flow2_m_AT = flow_m_AT - flowSS_m_AT

                suc2AT = State.define(fluid=fluid2_AT, p=Ps2_AT, T=Td_AT)
                disch2FD = State.define(fluid=fluid2_AT, p=Pd2_AT, T=Td2_AT)

            Dados_AT[i, 11].value = suc2AT.T().to(AT_sheet.range("R6").value).magnitude

            Q1d_AT = flow_m_AT / dischAT.rho()
            Dados_AT[i, 12].value = (
                flowSS_v_AT.to("m³/h").magnitude
                / Q1d_AT.to("m³/h").magnitude
                / (flowSS_v_FD.to("m³/h").magnitude / Q1d_FD.to("m³/h").magnitude)
            )

            P2_AT.append(
                ccp.Point(
                    speed=speed_AT,
                    flow_m=flow2_m_AT,
                    suc=suc2AT,
                    disch=disch2AT,
                    b=b2,
                    D=D2,
                )
            )

        speed_AT

        if AT_sheet["U3"].value == "Vazão Seção 1":
            QQ = np.array(Dados_AT[:, 1].value)

        else:
            QQ = []
            for i in range(N):
                QQ.append(P2_AT[i].flow_v.magnitude)

        Id = list(np.argsort(QQ))

        if len(Id) > 1:
            Daux = Dados_AT.value
            Paux = [P for P in P_AT]
            P2aux = [P for P in P2_AT]
            for i in range(N):
                Dados_AT[i, :].value = Daux[Id[i]][:]
                P_AT[i] = Paux[Id[i]]
                P2_AT[i] = P2aux[Id[i]]

        P_ATconv = []
        P2_ATconv = []

        Results_AT = AT_sheet["G22:AB32"]
        Results_AT.value = [[None] * len(Results_AT[0, :].value)] * 11
        Results_AT = Results_AT[0:N, :]

        Results2_AT = AT_sheet["G37:AB47"]
        Results2_AT.value = [[None] * len(Results2_AT[0, :].value)] * 11
        Results2_AT = Results2_AT[0:N, :]

        for i in range(N):

            if AT_sheet["C23"].value == "Yes":
                rug = AT_sheet["D24"].value

                ReAT = P_AT[i].reynolds
                Re2AT = P2_AT[i].reynolds
                ReFD = P_FD.reynolds
                Re2FD = P2_FD.reynolds

                RCAT = 0.988 / ReAT ** 0.243
                RC2AT = 0.988 / Re2AT ** 0.243
                RCFD = 0.988 / ReFD ** 0.243
                RC2FD = 0.988 / Re2FD ** 0.243

                RBAT = np.log(0.000125 + 13.67 / ReAT) / np.log(rug + 13.67 / ReAT)
                RB2AT = np.log(0.000125 + 13.67 / Re2AT) / np.log(rug + 13.67 / Re2AT)
                RBFD = np.log(0.000125 + 13.67 / ReFD) / np.log(rug + 13.67 / ReFD)
                RB2FD = np.log(0.000125 + 13.67 / Re2FD) / np.log(rug + 13.67 / Re2FD)

                RAAT = 0.066 + 0.934 * (4.8e6 * b.to("ft").magnitude / ReAT) ** RCAT
                RA2AT = 0.066 + 0.934 * (4.8e6 * b2.to("ft").magnitude / Re2AT) ** RC2AT
                RAFD = 0.066 + 0.934 * (4.8e6 * b.to("ft").magnitude / ReFD) ** RCFD
                RA2FD = 0.066 + 0.934 * (4.8e6 * b2.to("ft").magnitude / Re2FD) ** RC2FD

                corr = RAFD / RAAT * RBFD / RBAT
                corr2 = RA2FD / RA2AT * RB2FD / RB2AT

                if abs(1 - P_AT[i].phi.magnitude / P_FD.phi.magnitude) < 0.04:
                    eff = 1 - (1 - P_AT[i].eff) * corr
                else:
                    eff = P_AT[i].eff

                if abs(1 - P2_AT[i].phi.magnitude / P2_FD.phi.magnitude) < 0.04:
                    eff2 = 1 - (1 - P2_AT[i].eff) * corr2
                else:
                    eff2 = P2_AT[i].eff

                Results_AT[i, 21].value = eff.magnitude
                Results2_AT[i, 21].value = eff2.magnitude

                P_ATconv.append(
                    ccp.Point(
                        suc=P_FD.suc,
                        eff=eff,
                        speed=speed_FD,
                        flow_v=P_AT[i].flow_v * N_ratio,
                        head=P_AT[i].head * N_ratio ** 2,
                        b=b,
                        D=D,
                    )
                )

                if SS_config == "IN":
                    flow2_m_ATconv = P_ATconv[i].flow_m + flowSS_m_FD
                    RSS = flowSS_m_FD / flow2_m_ATconv
                    R1 = P_ATconv[i].flow_m / flow2_m_ATconv

                    fluid2_ATconv = {
                        GasesFD[i]: mol_fracSS_FD[i] * RSS + mol_fracFD[i] * R1
                        for i in range(len(GasesFD))
                    }
                    h2_ATconv = P_ATconv[i].disch.h() * R1 + SS_FD.h() * RSS

                    suc2ATconv = State.define(
                        fluid=fluid2_ATconv,
                        p=P_ATconv[i].disch.p() * 0.995,
                        h=h2_ATconv,
                    )

                else:
                    fluid2_ATconv = fluid_FD
                    flow2_m_ATconv = P_ATconv[i].flow_m - flowSS_m_FD

                    suc2ATconv = P_ATconv[i].disch

                P2_ATconv.append(
                    ccp.Point(
                        suc=suc2ATconv,
                        eff=eff2,
                        speed=speed_FD,
                        flow_v=P2_AT[i].flow_v * N_ratio,
                        head=P2_AT[i].head * N_ratio ** 2,
                        b=b2,
                        D=D2,
                    )
                )

            else:

                P_ATconv.append(
                    ccp.Point(
                        suc=P_FD.suc,
                        eff=P_AT[i].eff,
                        speed=speed_FD,
                        flow_v=P_AT[i].flow_v * N_ratio,
                        head=P_AT[i].head * N_ratio ** 2,
                        b=b,
                        D=D,
                    )
                )

                if SS_config == "IN":
                    flow2_m_ATconv = P_ATconv[i].flow_m + flowSS_m_FD
                    RSS = flowSS_m_FD / flow2_m_ATconv
                    R1 = P_ATconv[i].flow_m / flow2_m_ATconv

                    fluid2_ATconv = {
                        GasesFD[i]: mol_fracSS_FD[i] * RSS + mol_fracFD[i] * R1
                        for i in range(len(GasesFD))
                    }
                    h2_ATconv = P_ATconv[i].disch.h() * R1 + SS_FD.h() * RSS

                    suc2ATconv = State.define(
                        fluid=fluid2_ATconv,
                        p=P_ATconv[i].disch.p() * 0.995,
                        h=h2_ATconv,
                    )

                else:
                    fluid2_ATconv = fluid_FD
                    flow2_m_ATconv = P_ATconv[i].flow_m - flowSS_m_FD

                    suc2ATconv = P_ATconv[i].disch

                P2_ATconv.append(
                    ccp.Point(
                        suc=suc2ATconv,
                        eff=P2_AT[i].eff,
                        speed=speed_FD,
                        flow_v=P2_AT[i].flow_v * N_ratio,
                        head=P2_AT[i].head * N_ratio ** 2,
                        b=b2,
                        D=D2,
                    )
                )

                Results_AT[i, 21].value = P_AT[i].eff
                Results2_AT[i, 21].value = P2_AT[i].eff

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
            AT_sheet["G32:AB32"].value = Results_AT[IdG[0], :].value
        elif len(IdG) > 1:
            IdG = [int(k) for k in np.argsort(Phi)[0:2]]
            IdG = sorted(IdG)
            aux1 = np.array(Results_AT[IdG[0], :].value)
            aux2 = np.array(Results_AT[IdG[1], :].value)
            f = (1 - aux1[7]) / (aux2[7] - aux1[7])

            aux = aux1 + f * (aux2 - aux1)
            AT_sheet["G32:AB32"].value = aux
        else:

            AT_sheet["G32:AB32"].value = [None] * len(Results_AT[0, :].value)

        if len(IdG2) == 1:
            AT_sheet["G47:AB47"].value = Results2_AT[IdG2[0], :].value
        elif len(IdG2) > 1:
            IdG2 = [int(k) for k in np.argsort(Phi2)[0:2]]
            IdG2 = sorted(IdG2)
            aux1 = np.array(Results2_AT[IdG2[0], :].value)
            aux2 = np.array(Results2_AT[IdG2[1], :].value)
            f = (1 - aux1[7]) / (aux2[7] - aux1[7])

            aux = aux1 + f * (aux2 - aux1)
            AT_sheet["G47:AB47"].value = aux
        else:

            AT_sheet["G47:AB47"].value = [None] * len(Results2_AT[0, :].value)

        AT_sheet["T11"].value = "READY!"

    ###########################################
    ### INÍCIO DA ROTINA DE TEST PROCEDURE
    ############################################

    if TP_sheet["R19"].value != None:
        TP_sheet["R19"].value = None
        TP_sheet["R23"].value = "Calculando..."

        if FD_sheet["AN5"].value == "Yes":

            FD_sheet = wb.sheets["DataSheet"]

            ### Reading and writing SECTION 1 from the FD sheet

            Ps_FD = Q_(FD_sheet.range("T23").value, "bar")
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
            )  ######used to be _head_pol()

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
            FD_sheet["AS27"].value = P_FD.volume_ratio.magnitude
            FD_sheet["AS28"].value = P_FD_eff.head.to("J/kg").magnitude
            FD_sheet["AS29"].value = P_FD_eff.disch.T().to("degC").magnitude
            FD_sheet["AS30"].value = P_FD_eff.power.to("kW").magnitude
            FD_sheet["AS31"].value = P_FD.head.to("J/kg").magnitude
            FD_sheet["AS32"].value = P_FD.eff.magnitude
            FD_sheet["AS33"].value = P_FD.power.to("kW").magnitude

            ### Reading and writing SECTION 2 from the FD sheet

            SS_config = FD_sheet.range("W18").value

            Ps2_FD = Pd_FD * 0.995
            if SS_config == "IN":
                TSS_FD = Q_(FD_sheet.range("W24").value, "degC")
            else:
                TSS_FD = Td_FD

            Pd2_FD = Q_(FD_sheet.range("Z31").value, "bar")
            Td2_FD = Q_(FD_sheet.range("Z32").value, "degC")

            eff2_FD = Q_(FD_sheet.range("Z41").value, "dimensionless")
            Pow2_FD = Q_(FD_sheet.range("Z35").value, "kW")
            H2_FD = Q_(FD_sheet.range("Z40").value, "J/kg")

            if FD_sheet.range("W21").value == None:
                V_test = True
                flowSS_v_FD = Q_(FD_sheet.range("W29").value, "m³/h")
            else:
                V_test = False
                flowSS_m_FD = Q_(FD_sheet.range("W21").value, "kg/h")

            D2 = Q_(FD_sheet.range("AB133").value, "mm")
            b2 = Q_(FD_sheet.range("AQ133").value, "mm")

            if SS_config == "IN":
                GasesFD = FD_sheet.range("B69:B85").value
                mol_fracSS_FD = FD_sheet.range("N69:N85").value

                fluidSS_FD = {GasesFD[i]: mol_fracSS_FD[i] for i in range(len(GasesFD))}
            else:
                fluidSS_FD = fluid_FD

            SS_FD = State.define(fluid=fluidSS_FD, p=Ps2_FD, T=TSS_FD)

            if V_test:
                flowSS_m_FD = flowSS_v_FD * SS_FD.rho()
                FD_sheet["AS36"].value = flowSS_m_FD.to("kg/h").magnitude
                FD_sheet["AQ36"].value = "SS Mass Flow"
                FD_sheet["AU36"].value = "kg/h"
            else:
                flowSS_v_FD = flowSS_m_FD / SS_FD.rho()
                FD_sheet["AS36"].value = flowSS_v_FD.to("m³/h").magnitude
                FD_sheet["AQ36"].value = "SS Volume Flow"
                FD_sheet["AU36"].value = "m³/h"

            if SS_config == "IN":
                flow2_m_FD = flow_m_FD + flowSS_m_FD
                RSS = flowSS_m_FD / flow2_m_FD
                R1 = flow_m_FD / flow2_m_FD

                fluid2_FD = {
                    GasesFD[i]: mol_fracSS_FD[i] * RSS + mol_fracFD[i] * R1
                    for i in range(len(GasesFD))
                }
                h2_FD = dischFD.h() * R1 + SS_FD.h() * RSS
                h2_FD_eff = P_FD_eff.disch.h() * R1 + SS_FD.h() * RSS

                suc2FD = State.define(fluid=fluid2_FD, p=Ps2_FD, h=h2_FD)
                suc2FD_eff = State.define(fluid=fluid2_FD, p=Ps2_FD, h=h2_FD_eff)
                disch2FD = State.define(fluid=fluid2_FD, p=Pd2_FD, T=Td2_FD)
                FD_sheet["AT35"].value = suc2FD.T().to("degC").magnitude
            else:
                fluid2_FD = fluid_FD
                flow2_m_FD = flow_m_FD - flowSS_m_FD

                suc2FD = State.define(fluid=fluid2_FD, p=Ps2_FD, T=Td_FD)
                suc2_eff = P_FD_eff.disch
                disch2FD = State.define(fluid=fluid2_FD, p=Pd2_FD, T=Td2_FD)
                FD_sheet["AT35"].value = suc2FD.T().to("degC").magnitude

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
                    b=b2,
                    D=D2,
                )

                P2 = P2_FD_eff.disch.p().to("Pa").magnitude

                return P2 - Pd2_FD.to("Pa").magnitude

            newton(
                update_head2,
                ccp.point.head_pol(suc=P2_FD.suc, disch=P2_FD.disch)
                .to("J/kg")
                .magnitude,
                tol=1,
            )  ######used to be _head_pol()

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

            if V_test:

                FD_sheet["AT34"].value = P2_FD.flow_m.to("kg/h").magnitude
            else:

                FD_sheet["AT34"].value = P2_FD.flow_v.to("m³/h").magnitude

            Q1d_FD = flow_m_FD / dischFD.rho()
            FD_sheet["AS37"].value = (
                flowSS_v_FD.to("m³/h").magnitude / Q1d_FD.to("m³/h").magnitude
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

        # P_TPconv = Imp_TP._calc_from_speed(point=P_TP,new_speed=P_FD.speed)

        N_ratio = speed_FD / speed_TP
        if TP_sheet["C23"].value == "Yes":
            rug = TP_sheet["D24"].value

            ReTP = P_TP.reynolds
            ReFD = P_FD.reynolds

            RCTP = 0.988 / ReTP ** 0.243
            RCFD = 0.988 / ReFD ** 0.243

            RBTP = np.log(0.000125 + 13.67 / ReTP) / np.log(rug + 13.67 / ReTP)
            RBFD = np.log(0.000125 + 13.67 / ReFD) / np.log(rug + 13.67 / ReFD)

            RATP = 0.066 + 0.934 * (4.8e6 * b.to("ft").magnitude / ReTP) ** RCTP
            RAFD = 0.066 + 0.934 * (4.8e6 * b.to("ft").magnitude / ReFD) ** RCFD

            corr = RAFD / RATP * RBFD / RBTP

            eff = 1 - (1 - P_TP.eff) * corr

            TP_sheet["H37"].value = eff.magnitude

            P_TPconv = ccp.Point(
                suc=P_FD.suc,
                eff=eff,
                speed=speed_FD,
                flow_v=P_TP.flow_v * N_ratio,
                head=P_TP.head * N_ratio ** 2,
                b=b,
                D=D,
            )

        else:

            P_TPconv = ccp.Point(
                suc=P_FD.suc,
                eff=P_TP.eff,
                speed=speed_FD,
                flow_v=P_TP.flow_v * N_ratio,
                head=P_TP.head * N_ratio ** 2,
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

        if TP_sheet["C25"].value == "Yes":

            HL_FD = Q_(
                ((sucFD.T() + dischFD.T()).to("degC").magnitude * 0.8 / 2 - 25)
                * 1.166
                * TP_sheet["D26"].value,
                "W",
            )
            HL_TP = Q_(
                ((sucTP.T() + dischTP.T()).to("degC").magnitude * 0.8 / 2 - 25)
                * 1.166
                * TP_sheet["D26"].value,
                "W",
            )

            TP_sheet["G34"].value = (P_TPconv.power - HL_TP + HL_FD).to("kW").magnitude
            TP_sheet["H35"].value = (P_TPconv.power - HL_TP + HL_FD).to(
                "kW"
            ).magnitude / min_Pow

        else:
            TP_sheet["G34"].value = P_TPconv.power.to("kW").magnitude
            TP_sheet["H35"].value = P_TPconv.power.to("kW").magnitude / min_Pow

        TP_sheet["G36"].value = P_TP.eff.magnitude

        ### Reading and writing SECTION 2 from the TP sheet

        Ps2_TP = Pd_TP * 0.995

        if SS_config == "IN":
            TSS_TP = Q_(TP_sheet.range("R9").value, TP_sheet.range("S9").value)
        else:
            TSS_TP = Td_TP

        Pd2_TP = Q_(TP_sheet.range("P14").value, TP_sheet.range("Q14").value)

        if TP_sheet.range("L9").value == None:
            V_test = True
            flowSS_v_TP = Q_(TP_sheet.range("N9").value, TP_sheet.range("O9").value)
        else:
            V_test = False
            flowSS_m_TP = Q_(TP_sheet.range("L9").value, TP_sheet.range("M9").value)

        speed2_TP = Q_(TP_sheet.range("J14").value, TP_sheet.range("K14").value)

        fluidSS_TP = fluid_TP

        SS_TP = State.define(fluid=fluidSS_TP, p=Ps2_TP, T=TSS_TP)

        if V_test:
            flowSS_m_TP = flowSS_v_TP * SS_TP.rho()
            TP_sheet["L9"].value = flowSS_m_TP.to(TP_sheet.range("M9").value).magnitude
        else:
            flowSS_v_TP = flowSS_m_TP / SS_TP.rho()
            TP_sheet["N9"].value = flowSS_v_TP.to(TP_sheet.range("O9").value).magnitude

        if SS_config == "IN":
            flow2_m_TP = flow_m_TP + flowSS_m_TP

            TP_sheet["F14"].value = flow2_m_TP.to(TP_sheet.range("G14").value).magnitude

            RSS = flowSS_m_TP / flow2_m_TP
            R1 = flow_m_TP / flow2_m_TP

            fluid2_TP = fluidSS_TP

            h2_TP = dischTP.h() * R1 + SS_TP.h() * RSS

            suc2TP = State.define(fluid=fluid2_TP, p=Ps2_TP, h=h2_TP)
            flow2_v_TP = flow2_m_TP * suc2TP.v()
            TP_sheet["H14"].value = flow2_v_TP.to(TP_sheet.range("I14").value).magnitude

            TP_sheet["N14"].value = suc2TP.T().to(TP_sheet.range("O14").value).magnitude

        else:
            fluid2_TP = fluid_TP
            flow2_m_TP = flow_m_TP - flowSS_m_TP
            TP_sheet["F14"].value = flow2_m_TP.to(TP_sheet.range("G14").value).magnitude

            suc2TP = State.define(fluid=fluid2_TP, p=Ps2_TP, T=Td_TP)

            flow2_v_TP = flow2_m_TP * suc2TP.v()
            TP_sheet["H14"].value = flow2_v_TP.to(TP_sheet.range("I14").value).magnitude

            TP_sheet["N14"].value = suc2FD.T().to(TP_sheet.range("O14").value).magnitude

        disch2TPk = State.define(fluid=fluid2_TP, p=Pd2_TP, s=suc2TP.s())

        hd2_TP = sucTP.h() + (disch2TPk.h() - suc2TP.h()) / ccp.point.eff_isentropic(
            suc=P2_FD.suc, disch=P2_FD.disch
        )
        disch2TP = State.define(fluid=fluid2_TP, p=Pd2_TP, h=hd2_TP)

        TP_sheet["R14"].value = disch2TP.T().to(TP_sheet.range("S14").value).magnitude

        P2_TP = ccp.Point(
            speed=speed2_TP, flow_m=flow2_m_TP, suc=suc2TP, disch=disch2TP, b=b2, D=D2
        )

        N2_ratio = speed_FD / speed2_TP
        if TP_sheet["C23"].value == "Yes":
            rug = TP_sheet["D24"].value

            Re2TP = P2_TP.reynolds
            Re2FD = P2_FD.reynolds

            RCTP = 0.988 / Re2TP ** 0.243
            RCFD = 0.988 / Re2FD ** 0.243

            RBTP = np.log(0.000125 + 13.67 / Re2TP) / np.log(rug + 13.67 / Re2TP)
            RBFD = np.log(0.000125 + 13.67 / Re2FD) / np.log(rug + 13.67 / Re2FD)

            RATP = 0.066 + 0.934 * (4.8e6 * b2.to("ft").magnitude / Re2TP) ** RCTP
            RAFD = 0.066 + 0.934 * (4.8e6 * b2.to("ft").magnitude / Re2FD) ** RCFD

            corr = RAFD / RATP * RBFD / RBTP

            eff = 1 - (1 - P2_TP.eff) * corr

            TP_sheet["M37"].value = eff.magnitude

            P2_TPconv = ccp.Point(
                suc=P2_FD.suc,
                eff=eff,
                speed=speed_FD,
                flow_v=P2_TP.flow_v * N2_ratio,
                head=P2_TP.head * N2_ratio ** 2,
                b=b2,
                D=D2,
            )

        else:

            P2_TPconv = ccp.Point(
                suc=P2_FD.suc,
                eff=P2_TP.eff,
                speed=speed_FD,
                flow_v=P2_TP.flow_v * N2_ratio,
                head=P2_TP.head * N2_ratio ** 2,
                b=b2,
                D=D2,
            )
            TP_sheet["M37"].value = ""

        Q1d_TP = flow_m_TP / dischTP.rho()
        TP_sheet["R28"].value = (
            flowSS_v_TP.to("m³/h").magnitude / Q1d_TP.to("m³/h").magnitude
        )
        TP_sheet["S28"].value = (
            flowSS_v_TP.to("m³/h").magnitude
            / Q1d_TP.to("m³/h").magnitude
            / (flowSS_v_FD.to("m³/h").magnitude / Q1d_FD.to("m³/h").magnitude)
        )

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

        if TP_sheet["C27"].value == "Yes":

            HL_FD = Q_(
                ((suc2FD.T() + disch2FD.T()).to("degC").magnitude * 0.8 / 2 - 25)
                * 1.166
                * TP_sheet["D28"].value,
                "W",
            )
            HL_TP = Q_(
                ((suc2TP.T() + disch2TP.T()).to("degC").magnitude * 0.8 / 2 - 25)
                * 1.166
                * TP_sheet["D28"].value,
                "W",
            )

            TP_sheet["L34"].value = (P2_TPconv.power - HL_TP + HL_FD).to("kW").magnitude
            TP_sheet["M35"].value = (P2_TPconv.power - HL_TP + HL_FD).to(
                "kW"
            ).magnitude / min_Pow2

        else:
            TP_sheet["L34"].value = P2_TPconv.power.to("kW").magnitude
            TP_sheet["M35"].value = P2_TPconv.power.to("kW").magnitude / min_Pow2

        TP_sheet["L36"].value = P2_TP.eff.magnitude

        TP_sheet["R23"].value = "READY!"

    if CF_sheet["K4"].value != None:
        global qm

        CF_sheet["A1"].value = "Calculando..."

        CF_sheet["K4"].value = None

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

            e = 1 - (0.351 + 0.256 * (beta ** 4) + 0.93 * (beta ** 8)) * (
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
                    + 0.0261 * beta ** 2
                    - 0.216 * beta ** 8
                    + 0.000521 * (1e6 * beta / Re) ** 0.7
                    + (0.0188 + 0.0063 * (19000 * beta / Re) ** 0.8)
                    * beta ** 3.5
                    * (1e6 / Re) ** 0.3
                    + (0.043 + 0.080 * np.e ** (-10 * L1) - 0.123 * np.e ** (-7 * L1))
                    * (1 - 0.11 * (19000 * beta / Re) ** 0.8)
                    * (beta ** 4 / (1 - beta ** 4))
                    - 0.031 * (M2 - 0.8 * M2 ** 1.1) * beta ** 1.3
                )

                if D < Q_(71.12, "mm"):
                    C += 0.011 * (0.75 - beta) * (2.8 - D / Q_(25.4, "mm"))

                qm = (
                    C
                    / (np.sqrt(1 - beta ** 4))
                    * e
                    * (np.pi / 4)
                    * d ** 2
                    * np.sqrt(2 * dP * rho)
                )

                Re_qm = (4 * qm / (mu * np.pi * D)).to("dimensionless").magnitude

                return abs(Re_qm - Re.magnitude)

            newton(update_Re, 1e8, tol=1e-5)

            Re = D / mu * qm / (np.pi * D ** 2 / 4)

            CF_sheet[i, 8].value = qm.to(Units[-1]).magnitude

            i += 1
            data = np.array(CF_sheet[i, 2:8].value)

        CF_sheet["A1"].value = "READY!"

    sleep(1)
    try:
        aux = open(FileName, "r+")
        Open = False
    except:
        Open = True
