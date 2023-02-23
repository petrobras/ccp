import os

filename = os.path.basename(__file__)[:-3]
DEBUG_MODE = False

if filename == "test_1sec":  # if the script is run from the test file
    filename = "Beta_1section.xlsm"
if DEBUG_MODE:
    filename = "Beta_1section.xlsm"

import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
log_file = Path(__file__).parent / "log.txt"
handler = logging.FileHandler(log_file, mode="w")
logger.addHandler(handler)


def handle_exception(exc_type, exc_value, exc_traceback):
    AT_sheet["F36"].value = "ERRO!"
    TP_sheet["J23"].value = "ERRO!"
    CF_sheet["M8"].value = "ERRO!"
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        logger.critical(
            "Exception occured:", exc_info=(exc_type, exc_value, exc_traceback)
        )


sys.excepthook = handle_exception

from xlwings import Book

wb = Book(filename)  # connect to an existing file in the current working directory
AT_sheet = wb.sheets["Actual Test Data"]
TG_sheet = wb.sheets["Test Gas"]
TP_sheet = wb.sheets["Test Procedure Data"]
FD_sheet = wb.sheets["DataSheet"]
CF_sheet = wb.sheets["CalcFlow"]

if AT_sheet["H35"].value != None:
    AT_sheet["F36"].value = "Carregando bibliotecas..."
elif TP_sheet["K19"].value != None:
    TP_sheet["J23"].value = "Carregando bibliotecas..."
elif CF_sheet["M4"].value != None:
    CF_sheet["M8"].value = "Carregando bibliotecas..."

from scipy.optimize import newton


try:
    aux = os.environ["RPprefix"]
except:
    os.environ["RPprefix"] = "C:\\Users\\Public\\REFPROP"
import ccp
from ccp import State, Q_
from ccp import compressor
import numpy as np


logger.critical("System Information:")
logger.critical(f"python: {sys.version}")
logger.critical(f"ccp: {ccp.__version__full}")
logger.critical(
    f"REFPROP path: {ccp._CP.get_config_string(ccp._CP.ALTERNATIVE_REFPROP_PATH)}"
)

if __name__ == "__main__" or __name__ == "test_script":

    if DEBUG_MODE or __name__ == "test_script":
        AT_sheet["H35"].value = "Calcular"

    global P_FD_eff

    if AT_sheet["H35"].value != None:
        AT_sheet["H35"].value = None
        AT_sheet["F36"].value = "Calculando..."

        ### Reading and writing in the FD sheet

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

        speed_FD = Q_(FD_sheet.range("T38").value, "rpm")

        brake_pow_FD = Q_(FD_sheet.range("T36").value, "kW")
        Pol_head_FD = Q_(FD_sheet.range("T40").value, "J/kg")
        Pol_eff_FD = Q_(FD_sheet.range("T41").value, "dimensionless")

        D = Q_(FD_sheet.range("AB132").value, "mm")
        b = Q_(FD_sheet.range("AQ132").value, "mm")
        GasesFD = FD_sheet.range("B69:B85").value
        mol_fracFD = FD_sheet.range("K69:K85").value
        fluid_FD = {
            GasesFD[i]: mol_fracFD[i]
            for i in range(len(GasesFD))
            if mol_fracFD[i] is not None
        }
        sucFD = State(fluid=fluid_FD, p=Ps_FD, T=Ts_FD)

        if V_test:
            flow_m_FD = flow_v_FD * sucFD.rho()
            FD_sheet["AS34"].value = flow_m_FD.to("kg/h").magnitude
            FD_sheet["AQ34"].value = "Mass Flow"
            FD_sheet["AT34"].value = "kg/h"
        else:
            flow_v_FD = flow_m_FD / sucFD.rho()
            FD_sheet["AS34"].value = flow_v_FD.to("m³/h").magnitude
            FD_sheet["AQ34"].value = "Inlet Volume Flow"
            FD_sheet["AT34"].value = "m³/h"

        dischFD = State(fluid=fluid_FD, p=Pd_FD, T=Td_FD)

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

        newton(update_head, P_FD.head.to("J/kg").magnitude, tol=1)

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

        FD_sheet["K90"].value = sucFD.molar_mass().to("g/mol").magnitude

        ### End of Reading and writing in the FD sheet
        Curva = FD_sheet["AP39:AS46"]

        for i in range(8):
            if Curva[i, 0].value == None or i == 7:
                Nc = i
                break

        Curva = Curva[0 : Nc + 1, :]
        QFD = Q_(np.array(Curva[0:Nc, 0].value), FD_sheet["AP38"].value)
        logger.critical(f"Nc {Nc}, QFD {QFD}, flow_v_FD {flow_v_FD}")
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

        curve_shape = AT_sheet["C33"].value
        BL_leak = AT_sheet["C35"].value
        BF_leak = AT_sheet["C37"].value

        if curve_shape == "Yes":
            args_list = []
            P_exp = []
            for i in range(Nc):
                arg_dict = {
                    "eff": Curva[i, 3].value,
                    "flow_v": Q_(Curva[i, 0].value, FD_sheet["AP38"].value),
                    "suc": sucFD,
                    "speed": speed_FD,
                    "head": Q_(Curva[i, 1].value, FD_sheet["AQ38"].value),
                    "b": b,
                    "D": D,
                }
                args_list.append(arg_dict)

            with multiprocessing.Pool() as pool:
                P_exp += pool.map(ccp.impeller.create_points_parallel, args_list)

            imp_exp = P_exp

        ### Reading and writing in the Actual Test Data Sheet

        Dados_AT = AT_sheet["G7:R16"]

        for i in range(10):
            if Dados_AT[i, 5].value == None:
                N = i
                break

        Dados_AT = Dados_AT[0:N, :]

        P_AT = []
        P_AT_Bal = []
        P_AT_Buf = []

        for i in range(N):

            speed_AT = Q_(Dados_AT[i, 11].value, AT_sheet.range("R6").value)
            N_ratio = speed_FD / speed_AT

            gas = int(Dados_AT[i, 7].value)

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

            sucAT = State(fluid=fluid_AT, p=Ps_AT, T=Ts_AT)
            dischAT = State(fluid=fluid_AT, p=Pd_AT, T=Td_AT)

            if V_test:
                flow_m_AT = flow_v_AT * sucAT.rho()
                Dados_AT[i, 0].value = flow_m_AT.to(AT_sheet["G6"].value).magnitude
            else:
                flow_v_AT = flow_m_AT / sucAT.rho()
                Dados_AT[i, 1].value = flow_v_AT.to(AT_sheet["H6"].value).magnitude

            # Heat loss consideration - power and efficiency  correction
            if AT_sheet["C25"].value == "Yes":
                Cas_Area = Q_(AT_sheet["D26"].value, "m**2")
                T_amb = Q_(0, AT_sheet["M6"].value)
                Cas_Temperature = Q_(Dados_AT[i, 6].value, AT_sheet["M6"].value)
                heat_constant = Q_(AT_sheet["D32"].value, "W/m**2/kelvin")

            else:
                Cas_Area = None
                Cas_Temperature = None
                T_amb = None
                heat_constant = None

            balance_line_flow = None
            seal_gas_flow = None
            seal_gas_temperature = None

            if AT_sheet["D24"].value == None:
                surface_roughness = Q_(3.175e-6, "m")
            else:
                surface_roughness = Q_(AT_sheet["D24"].value, "inches")

            if BL_leak == "Yes":
                if Dados_AT[i, 8].value == None:
                    Dados_AT[i, 8].value = 0
                balance_line_flow = Q_(Dados_AT[i, 8].value, AT_sheet.range("O6").value)
            else:
                balance_line_flow = Q_(0, "kg/s")

            if BF_leak == "Yes":
                if Dados_AT[i, 9].value == None:
                    Dados_AT[i, 9].value = 0
                if Dados_AT[i, 10].value == None:
                    Dados_AT[i, 10].value = 0
                seal_gas_flow = Q_(Dados_AT[i, 9].value, AT_sheet.range("P6").value)
                seal_gas_temperature = Q_(
                    Dados_AT[i, 10].value, AT_sheet.range("Q6").value
                ).to("kelvin")
            else:
                seal_gas_flow = Q_(0, "kg/s")
                seal_gas_temperature = Q_(0, "kelvin")

            P_AT.append(
                compressor.Point1Sec(
                    speed=speed_AT,
                    flow_m=flow_m_AT,
                    suc=sucAT,
                    disch=dischAT,
                    casing_area=Cas_Area,
                    casing_temperature=Cas_Temperature,
                    ambient_temperature=T_amb,
                    convection_constant=heat_constant,
                    b=b,
                    D=D,
                    balance_line_flow_m=balance_line_flow,
                    seal_gas_flow_m=seal_gas_flow,
                    seal_gas_temperature=seal_gas_temperature,
                    surface_roughness=surface_roughness,
                )
            )

        reynolds_correction = False
        if AT_sheet["C23"].value == "Yes":
            reynolds_correction = True
        imp_conv = compressor.StraightThrough(
            guarantee_point=P_FD,
            test_points=P_AT,
            speed=speed_FD,
            reynolds_correction=reynolds_correction,
        )

        # calculate speed to match pressure
        if AT_sheet["H36"].value is not None:
            AT_sheet["H36"].value = None
            imp_conv = imp_conv.calculate_speed_to_match_discharge_pressure()
            FD_sheet["T38"].value = imp_conv.speed.to("RPM").m
            speed_FD = Q_(FD_sheet.range("T38").value, "rpm")

        QQ = np.array(Dados_AT[:, 1].value)
        Id = list(np.argsort(QQ))
        Daux = Dados_AT.value
        Paux = [P for P in P_AT]

        if N > 1:
            for i in range(N):
                Dados_AT[i, :].value = Daux[Id[i]][:]
                P_AT[i] = Paux[Id[i]]

        P_ATconv = []

        Results_AT = AT_sheet["G22:AB32"]
        Results_AT.value = [[None] * len(Results_AT[0, :].value)] * 11
        Results_AT = Results_AT[0:N, :]

        curve_shape = AT_sheet["C33"].value
        points_converted_reyn = []

        for i in range(N):

            if curve_shape == "Yes":
                P_exp_flow = imp_exp.point(
                    flow_v=P_AT[i].flow_v * N_ratio, speed=speed_FD
                )
            else:
                P_exp_flow = P_FD

            Results_AT[i, 0].value = P_AT[i].volume_ratio.magnitude
            Results_AT[i, 1].value = (
                P_AT[i].volume_ratio.magnitude / P_exp_flow.volume_ratio.magnitude
            )
            Results_AT[i, 2].value = P_AT[i].mach.magnitude
            Results_AT[i, 3].value = P_AT[i].mach.magnitude - P_exp_flow.mach.magnitude
            Results_AT[i, 4].value = P_AT[i].reynolds.magnitude
            Results_AT[i, 5].value = (
                P_AT[i].reynolds.magnitude / P_exp_flow.reynolds.magnitude
            )
            Results_AT[i, 6].value = P_AT[i].phi.magnitude
            Results_AT[i, 7].value = P_AT[i].phi.magnitude / P_exp_flow.phi.magnitude
            Results_AT[i, 10].value = P_AT[i].head.to("kJ/kg").magnitude
            Results_AT[i, 11].value = P_AT[i].head.to("kJ/kg").magnitude / max_H
            Results_AT[i, 16].value = P_AT[i].power.to("kW").magnitude
            Results_AT[i, 17].value = P_AT[i].power.to("kW").magnitude / min_Pow
            Results_AT[i, 20].value = P_AT[i].eff.magnitude

            Results_AT[i, 8].value = (
                imp_conv.points_flange_sp[i].disch.p().to("bar").magnitude
            )
            Results_AT[i, 9].value = (
                imp_conv.points_flange_sp[i].disch.p().to("bar").m
                / P_exp_flow.disch.p().to("bar").m
            )

            Results_AT[i, 12].value = (
                imp_conv.points_flange_sp[i].head.to("kJ/kg").magnitude
            )
            Results_AT[i, 13].value = (
                imp_conv.points_flange_sp[i].head.to("kJ/kg").magnitude / max_H
            )
            Results_AT[i, 14].value = (
                imp_conv.points_flange_sp[i].flow_v.to("m³/h").magnitude
            )
            Results_AT[i, 15].value = (
                imp_conv.points_flange_sp[i].flow_v.to("m³/h").magnitude
                / P_exp_flow.flow_v.to("m³/h").magnitude
            )
            Results_AT[i, 18].value = (
                imp_conv.points_flange_sp[i].power.to("kW").magnitude
            )
            Results_AT[i, 19].value = (
                imp_conv.points_flange_sp[i].power.to("kW").magnitude / min_Pow
            )  #########
            if reynolds_correction:
                Results_AT[i, 21].value = imp_conv.points_flange_sp[i].eff.magnitude

        Q_ratio = np.abs(1 - np.array(Results_AT[0:N, 15].value))

        if N == 1:
            Q_ratio = [Q_ratio]

        # Add guarantee point
        point_converted_sp = imp_conv.point(flow_m=P_FD.flow_m, speed=speed_FD)
        guarantee_results = AT_sheet["G32:AB32"]
        guarantee_results[0].value = point_converted_sp.volume_ratio.m
        guarantee_results[1].value = (
            point_converted_sp.volume_ratio.m / P_FD.volume_ratio.m
        )
        guarantee_results[2].value = point_converted_sp.mach.m
        guarantee_results[3].value = point_converted_sp.mach.m - P_FD.mach.m
        guarantee_results[4].value = point_converted_sp.reynolds.m
        guarantee_results[5].value = point_converted_sp.reynolds.m / P_FD.reynolds.m
        guarantee_results[6].value = point_converted_sp.phi.m
        guarantee_results[7].value = point_converted_sp.phi.m / P_FD.phi.m
        guarantee_results[8].value = point_converted_sp.disch.p("bar").m
        guarantee_results[9].value = (
            point_converted_sp.disch.p("bar").m / P_FD.disch.p("bar").m
        )
        guarantee_results[10].value = " - "
        guarantee_results[11].value = " - "
        guarantee_results[12].value = point_converted_sp.head.to("kJ/kg").m
        guarantee_results[13].value = (
            point_converted_sp.head.to("kJ/kg").m / P_FD.head.to("kJ/kg").m
        )
        guarantee_results[14].value = point_converted_sp.flow_v.to("m³/h").m
        guarantee_results[15].value = (
            point_converted_sp.flow_v.to("m³/h").m / P_FD.flow_v.to("m³/h").m
        )
        guarantee_results[16].value = " - "
        guarantee_results[17].value = " - "
        guarantee_results[18].value = point_converted_sp.power.to("kW").m
        guarantee_results[19].value = (
            point_converted_sp.power.to("kW").m / P_FD.power.to("kW").m
        )
        if AT_sheet["C23"].value == "Yes":
            guarantee_results[20].value = None
            guarantee_results[21].value = point_converted_sp.eff.m
        else:
            guarantee_results[20].value = point_converted_sp.eff.m
            guarantee_results[21].value = None

        AT_sheet["F36"].value = "Calculado"

    ###########################################
    ### INÍCIO DA ROTINA DE TEST PROCEDURE
    ############################################

    if TP_sheet["K19"].value != None:
        TP_sheet["K19"].value = None
        TP_sheet["J23"].value = "Calculando..."

        FD_sheet = wb.sheets["DataSheet"]

        ### Reading and writing in the FD sheet

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

        brake_pow_FD = Q_(FD_sheet.range("T36").value, "kW")
        Pol_head_FD = Q_(FD_sheet.range("T40").value, "J/kg")
        Pol_eff_FD = Q_(FD_sheet.range("T41").value, "dimensionless")

        D = Q_(FD_sheet.range("AB132").value, "mm")
        b = Q_(FD_sheet.range("AQ132").value, "mm")
        GasesFD = FD_sheet.range("B69:B85").value
        mol_fracFD = FD_sheet.range("K69:K85").value

        fluid_FD = {
            GasesFD[i]: mol_fracFD[i]
            for i in range(len(GasesFD))
            if mol_fracFD[i] is not None
        }

        sucFD = State(fluid=fluid_FD, p=Ps_FD, T=Ts_FD)

        if V_test:
            flow_m_FD = flow_v_FD * sucFD.rho()
            FD_sheet["AS34"].value = flow_m_FD.to("kg/h").magnitude
            FD_sheet["AQ34"].value = "Mass Flow"
            FD_sheet["AT34"].value = "kg/h"
        else:
            flow_v_FD = flow_m_FD / sucFD.rho()
            FD_sheet["AS34"].value = flow_v_FD.to("m³/h").magnitude
            FD_sheet["AQ34"].value = "Inlet Volume Flow"
            FD_sheet["AT34"].value = "m³/h"

        dischFD = State(fluid=fluid_FD, p=Pd_FD, T=Td_FD)

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

        newton(update_head, P_FD.head.to("J/kg").magnitude, tol=1)

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

        FD_sheet["K90"].value = sucFD.molar_mass().to("g/mol").magnitude

        ### Reading and writing in the FD sheet

        ### Reading and writing in the Test Procedure Sheet

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

        sucTP = State(fluid=fluid_TP, p=Ps_TP, T=Ts_TP)
        dischTPk = State(fluid=fluid_TP, p=Pd_TP, s=sucTP.s())

        hd_TP = sucTP.h() + (dischTPk.h() - sucTP.h()) / ccp.point.eff_isentropic(
            suc=P_FD.suc, disch=P_FD.disch
        )
        dischTP = State(fluid=fluid_TP, p=Pd_TP, h=hd_TP)

        if V_test:
            flow_m_TP = flow_v_TP * sucTP.rho()
            TP_sheet["F6"].value = flow_m_TP.to(TP_sheet["G6"].value).magnitude
        else:
            flow_v_TP = flow_m_TP / sucTP.rho()
            TP_sheet["H6"].value = flow_v_TP.to(TP_sheet["I6"].value).magnitude

        # Heat loss consideration - power and efficiency  correction
        if TP_sheet["C25"].value == "Yes":
            Cas_Area = Q_(TP_sheet["D26"].value, "m**2")
            if TP_sheet["D28"].value == None:
                Cas_Temperature = (sucTP.T() + dischTP.T()).to("kelvin") / 2
            else:
                Cas_Temperature = Cas_Temperature = Q_(
                    TP_sheet["D28"].value, "degC"
                ).to("kelvin")
            T_amb = Q_(TP_sheet["D30"].value, "degC").to("kelvin")
            heat_constant = Q_(TP_sheet["D32"].value, "W/(m²*degK)")
            # HL_AT = (Cas_Area - t_amb) * heat_const * Area
            # eff_HL_corr = (P_ATconv[i].head / (P_ATconv[i].head / eff + HL_AT)).to("dimensionless").m
        else:
            Cas_Area = None
            Cas_Temperature = None
            T_amb = None
            heat_constant = None

        P_TP = ccp.Point(
            speed=speed_TP,
            flow_m=flow_m_TP,
            suc=sucTP,
            disch=dischTP,
            casing_area=Cas_Area,
            casing_temperature=Cas_Temperature,
            ambient_temperature=T_amb,
            convection_constant=heat_constant,
            b=b,
            D=D,
        )

        N_ratio = speed_FD / speed_TP
        if TP_sheet["C23"].value == "Yes":

            P_TPconv = reynolds_corr(
                P_AT=P_TP,
                P_FD=P_FD,
                rug=TP_sheet["D24"].value,
            )

            TP_sheet["H29"].value = P_TPconv.eff.m

        else:

            P_TPconv = ccp.Point(
                suc=P_FD.suc,
                eff=P_TP.eff,
                speed=speed_FD,
                flow_v=P_TP.flow_v * N_ratio,
                head=P_TP.head * N_ratio**2,
                b=b,
                D=D,
            )
            TP_sheet["H29"].value = ""

        TP_sheet["R6"].value = dischTP.T().to(TP_sheet["S6"].value).magnitude
        TP_sheet["G11"].value = P_TP.volume_ratio.magnitude
        TP_sheet["H11"].value = 1 / (
            P_TP.volume_ratio.magnitude / P_FD.volume_ratio.magnitude
        )
        TP_sheet["G12"].value = P_TP.mach.magnitude
        TP_sheet["H13"].value = P_TP.mach.magnitude - P_FD.mach.magnitude
        TP_sheet["G14"].value = P_TP.reynolds.magnitude
        TP_sheet["H15"].value = P_TP.reynolds.magnitude / P_FD.reynolds.magnitude
        TP_sheet["G16"].value = P_TP.phi.magnitude
        TP_sheet["H17"].value = P_TP.phi.magnitude / P_FD.phi.magnitude
        TP_sheet["G18"].value = P_TP.psi.magnitude
        TP_sheet["H19"].value = P_TP.psi.magnitude / P_FD.psi.magnitude
        TP_sheet["G20"].value = P_TP.head.to("kJ/kg").magnitude
        TP_sheet["H21"].value = P_TP.head.to("kJ/kg").magnitude / max_H
        TP_sheet["G22"].value = P_TPconv.head.to("kJ/kg").magnitude
        TP_sheet["H23"].value = P_TPconv.head.to("kJ/kg").magnitude / max_H
        TP_sheet["G24"].value = P_TP.power.to("kW").magnitude
        TP_sheet["H25"].value = P_TP.power.to("kW").magnitude / min_Pow

        TP_sheet["G26"].value = P_TPconv.power.to("kW").magnitude
        TP_sheet["H27"].value = P_TPconv.power.to("kW").magnitude / min_Pow

        TP_sheet["G28"].value = P_TP.eff.magnitude

        TP_sheet["J23"].value = "Calculado"

    if CF_sheet["M4"].value != None:
        global qm

        CF_sheet["M8"].value = "Calculando..."

        CF_sheet["M4"].value = None

        i = 4
        data = np.array(CF_sheet[i, 2:9].value)

        while len(data[data == None]) == 0:

            Units = CF_sheet["C4:J4"].value

            gas = int(float(data[6]))

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

            # if len(data[data==None])==0:

            D = Q_(float(data[0]), Units[0])
            d = Q_(float(data[1]), Units[1])
            P1 = Q_(float(data[2]), Units[2])
            T1 = Q_(float(data[3]), Units[3])
            dP = Q_(float(data[4]), Units[4])
            tappings = data[5]

            P2 = P1 - dP

            State_FO = State(fluid=fluid_AT, p=P1, T=T1)

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

            CF_sheet[i, 9].value = qm.to(Units[-1]).magnitude

            i += 1
            data = np.array(CF_sheet[i, 2:9].value)

        CF_sheet["M8"].value = "Calculado"
