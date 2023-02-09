#Rev. 27ago21 15hs23min
from pathlib import Path
import os
import time
from time import sleep
import multiprocessing
import ccp
from ccp import Q_
import numpy as np
import xlwings as xw
from xlwings import Book
from scipy.interpolate import UnivariateSpline
import plotly.graph_objects as go
import plotly.express as px
from itertools import cycle

FileName = os.path.basename(__file__)[:-3]

if __name__ == '__main__':

    xw.PRO = True

    wb = Book(FileName)

    o_sheet = wb.sheets['Performance - Original']
    a_sheet = wb.sheets['auxiliar']
    n_sheet = wb.sheets['Performance - Nova']
    v_sheet = wb.sheets['Performance - Validação']
    t_sheet = wb.sheets['Teste']
    CF_sheet = wb.sheets['Vazão - Cálculo']
    comp_sheet = wb.sheets['Curvas - Original x Nova']
    graf_ = wb.sheets['Curvas - Originais']
    graf_n_sheet = wb.sheets['Curvas - Novas']
    graf_n_ = wb.sheets['Curvas - Nova(Rotacao Original)']

    simp_question = o_sheet['M17'].value
    val_data = False
    Open_file = True
    case2 = False

    def gas_composition(p, T, column=3, sheet = o_sheet, o_sheet_template=True, output_sheet=True):
        #output_sheet - for original and new performance sheets whose gas properties are written on excel
        #column - gas composition column
        nn = 0
        if not o_sheet_template:
            nn = 1
        for i in range(25):
            if sheet.cells(12 + i - nn, column).value == None:
                N = i
                break
            elif i == 24:
                N = 25
        Gases = sheet.range(sheet.cells(12 - nn, column), sheet.cells(12 - nn + N - 1, column)).value
        mol_frac = sheet.range(sheet.cells(12 - nn, column + 2), sheet.cells(12 - nn + N - 1, column + 2)).value

        for i in range(len(Gases)):
            if mol_frac[i] == None:
                mol_frac[i] = 0
        if any(ele > 1 for ele in mol_frac):
            factor = 100
        else:
            factor = 1
        try:
            fluid = {Gases[i]: mol_frac[i] / factor for i in range(len(Gases))}
        except TypeError as e:
            if o_sheet_template:
                sheet['K15'].value = 'Erro! %molar!'
                sheet['K16'].value = 'Reinicie o Script!'
            elif not output_sheet:
                raise e
            else:
                n_sheet['I8'].value = 'Erro! %molar!'
                n_sheet['I9'].value = 'Reinicie o Script!'
        try:
            suc = ccp.State(p=p, T=T, fluid=fluid)
        except ValueError as e:
            if o_sheet_template:
                sheet['K15'].value = 'Composição do Gás!'
                sheet['K16'].value = 'Reinicie o Script!'
            elif not output_sheet:
                raise e
            else:
                n_sheet['I8'].value = 'Composição do Gás!'
                n_sheet['I9'].value = 'Reinicie o Script!'
        MW = suc.molar_mass().to('kg/kmol')
        ks = suc.kv()  #############################################
        km = (2 * ks - 0.01) / 2  # rough estimative##################################
        Zs = suc.z()
        Zm = (2 * Zs - 0.01) / 2  # rough estimative##################################
        gas_constant = suc.gas_constant()
        ###############################################################################################################
        if output_sheet:
            sheet.cells(37 - nn, column + 2).value = MW.magnitude
            sheet.cells(2, column + 3).value = MW.magnitude
            sheet.cells(2, column + 1 + 3).value = 'kg/kmol'
            sheet.cells(3, column + 3).value = ks.magnitude
            sheet.cells(4, column + 3).value = Zs.magnitude
        return suc, MW, km, Zm, gas_constant

    def load_from_excel(speed_unit,var1_unit,var2_unit,cell_speed_n='D40',column=3,sheet=o_sheet):

        N_speed = int(sheet[cell_speed_n].value)
        speed = Q_(np.zeros(N_speed), speed_unit)
        # Store each variable (flow, head and efficiency) in 2-D arrays - [variable,speed]
        f = 0
        for i in range(N_speed):
            Qs = list()
            H = list()
            eff = list()
            stop_loop = 0
            while (sheet.cells(42 + f, column).value) == None and stop_loop < 20:
                f += 1
                stop_loop += 1
            # stop loop whether there are no more curves to read from .xlsm file
            if stop_loop == 20:
                N_speed = i
                break
            speed[i] = Q_(sheet.cells(42 + f, column).value, speed_unit)
            f = f + 1
            # flow_unit = o_sheet.cells(42+f,3).value
            # if list(dict(Q_().dimensionality).keys())[0]flow_unit == []
            # var1_unit = o_sheet.cells(42+f,4).value
            f += 1
            while (sheet.cells(42 + f, column).value) != None:
                Qs.append(sheet.cells(42 + f, column).value)
                H.append(sheet.cells(42 + f, column+1).value)
                eff.append(sheet.cells(42 + f, column+2).value)
                f += 1
                # Sort each variable (Head and efficiency) in flow ascending order
            ind_Q = np.argsort(Qs)

            Qs = np.array(Qs)
            H = np.array(H)
            eff = np.array(eff)

            Qs = Qs[ind_Q]
            H = H[ind_Q]
            eff = eff[ind_Q]
            # set the first array as reference for the number of points in one speed
            # and resize other speeds "array"
            if i == 0:
                Flow = Q_(np.zeros((len(Qs), N_speed)), flow_unit)
                Head = Q_(np.zeros((len(Qs), N_speed)), var1_unit)
                Eff = Q_(np.zeros((len(Qs), N_speed)), var2_unit)
                Flow[:, i] = Q_(Qs, flow_unit)
                Head[:, i] = Q_(H, var1_unit)
                Eff[:, i] = Q_(eff, var2_unit)
            else:
                Flow[:, i] = Q_(np.linspace(Qs[0], Qs[-1], len(Flow[:, 0])), flow_unit)
                s = UnivariateSpline(Qs, H, s=1)
                Head[:, i] = Q_(s(Flow[:, i]), var1_unit)
                t = UnivariateSpline(np.array(Qs), eff, s=1)
                Eff[:, i] = Q_(t(Flow[:, i]), var2_unit)

        # Sort each parameter (Head and efficiency) in speed descending order
        if N_speed > 1:
            speed = speed.to('rpm')
            ind_Speed = np.argsort(speed.magnitude)[::-1]
            speed = speed[ind_Speed]
            Flow = Flow[:, ind_Speed]
            Head = Head[:, ind_Speed]
            Eff = Eff[:, ind_Speed]

            # Calculation of polytropic coefficient
        N_lines = len(Flow[:, 0])
        if stop_loop == 20:
            Flow = Q_(np.delete(Flow.magnitude, np.s_[N_speed:], 1), flow_unit)
            Head = Q_(np.delete(Head.magnitude, np.s_[N_speed:], 1), var1_unit)
            Eff = Q_(np.delete(Eff.magnitude, np.s_[N_speed:], 1), var2_unit)

        if np.any(Eff.magnitude > 1):
            Eff = Eff / 100

        return N_speed, N_lines, Flow, Head, Eff, speed

    def array_from_csv(suc, curve_cell, b, D, flow_unit, var1_unit, speed_unit, n_imp =[0]):#"L12"

        # store performance data from .csv file and sort to speed descending order
        # and flow ascending order
        n_imp[0]+=1
        data_dir = Path.cwd()
        curve_name = a_sheet[curve_cell].value
        try:
            curve_name = float(curve_name)
        except:
            pass
        if isinstance(curve_name, float):
            curve_name = int(curve_name)
        curve_name = str(curve_name)
        N_lines = int(a_sheet["C5"].value)
        print(f'Criando impelidor nº {n_imp[0]} com pontos...')
        t0 = time.time()
        try:
            imp = ccp.Impeller.load_from_engauge_csv(suc=suc, curve_name=curve_name, number_of_points=N_lines,
                                                     curve_path=data_dir, b=b, D=D, flow_units=flow_unit,
                                                     head_units=var1_unit, speed_units=speed_unit)
        except FileNotFoundError:
            data_dir = Path(a_sheet["B8"].value)
            imp = ccp.Impeller.load_from_engauge_csv(suc=suc, curve_name=curve_name, number_of_points=N_lines,
                                                     curve_path=data_dir, b=b, D=D, flow_units=flow_unit,
                                                     head_units=var1_unit, speed_units=speed_unit)
        except FileNotFoundError:
            o_sheet['K15'].value = "Curva não encontrada!"
            o_sheet['K16'].value = 'Reinicie o Script!'
        except KeyError:
            o_sheet['K15'].value = "Rotações inconsist.!"
            o_sheet['K16'].value = 'Reinicie o Script!'
        except:
            o_sheet['K15'].value = 'Corrigir unidades!'
            o_sheet['K16'].value = 'Reinicie o Script!'
        tf = time.time()
        dt = tf - t0
        print(f'Tempo criando impelidor {n_imp[0]}: ' + str(int(dt / 60)) + ' minutos e ' + str(int(dt % 60)) + ' segundos')
        # store impeller points in 2-D arrays for each variable (H,Q,eff)
        N_speed = len(imp.curves)
        Flow = Q_(np.zeros((N_lines, N_speed)), flow_unit)
        Head = Q_(np.zeros((N_lines, N_speed)), var1_unit)
        Eff = Q_(np.zeros((N_lines, N_speed)), var2_unit)
        speed = Q_(np.zeros(N_speed), speed_unit)

        for j in range(N_speed):
            if N_speed > 1:
                if imp.curves[0][0].speed > imp.curves[1][0].speed:
                    l = j
                else:
                    l = -1 - j
            else:
                l = j
            for i in range(N_lines):
                speed[j] = imp.curves[l][0].speed.to(speed_unit)
                Head[i, j] = imp.curves[l][i].head.to(var1_unit)
                Flow[i, j] = imp.curves[l][i].flow_v.to(flow_unit)
                Eff[i, j] = imp.curves[l][i].eff

        return imp, N_speed, N_lines, Flow, Head, Eff, speed


    def impeller_from_excel(N_speed, speed_array, Qs, H, Eff, n_imp=[0]):
        n_imp[0] += 1
        Point = []
        # create an impeller that will hold and convert curves.
        print(f'armazenando pontos do impelidor {n_imp[0]}...')
        t0 = time.time()

        for j in range(N_speed):
            suc = suc_o
            speed = speed_array[j]
            args_list = [
                (
                    suc,
                    speed,
                    flow,
                    head,
                    eff,
                    b,
                    D,
                )
                for flow, head, eff in zip(Qs[:, j], H[:, j], Eff[:, j])
            ]

            with multiprocessing.Pool() as pool:
                try:
                    Point += pool.map(ccp.impeller.create_points_flow_v, args_list)
                except ValueError:
                    o_sheet['K15'].value = 'Verificar unidades!'

        tf = time.time()
        dt = tf - t0
        print(f'Tempo armazenando pontos do impelidor {n_imp[0]}: {int(dt / 60)} minutos e {int(dt % 60)} segundos')
        print(f'Criando impelidor {n_imp[0]}')
        t0 = time.time()
        imp = ccp.Impeller(Point)
        tf = time.time()
        dt = tf - t0
        print(f'Tempo criando impelidor {n_imp[0]}: {int(dt / 60)} minutos e {int(dt % 60)} segundos')

        return imp

    def convert_and_store(imp, N_speed, N_lines, flow_unit_out, var1_unit_out, var2_unit_out, n_imp=[0], pr = False):
        n_imp[0]+=1
        # convert curves with ccp package method
        t0 = time.time()
        try:
            imp
        except NameError:
            n_sheet['I8'].value = 'Reinicie o Script!'

        try:
            imp_conv = ccp.Impeller.convert_from(imp, suc=suc_n)
        except ValueError as e:
            n_sheet['I8'].value = 'Erro! Convergência!'
            n_sheet['I9'].value = 'Reinicie o Script!'
            raise e
        except RuntimeError as f:
            n_sheet['I8'].value = 'Erro! Convergência!'
            n_sheet['I9'].value = 'Reinicie o Script!'
            raise f

        tf = time.time()
        dt = tf - t0
        print(f'Tempo convertendo pontos do impelidor {n_imp[0]}: {int(dt / 60)} minutos e {int(dt % 60)} segundos')

        Qs_n = Q_(np.zeros((N_lines, N_speed)), flow_unit_out)
        H_n = Q_(np.zeros((N_lines, N_speed)), var1_unit_out)
        eff_n = Q_(np.zeros((N_lines, N_speed)), var2_unit_out)
        speed_n = Q_(np.zeros(N_speed), speed_unit_out)

        for j in range(N_speed):
            if N_speed > 1:
                if speed_o[0] > speed_o[1]:
                    l = -1 - j
                else:
                    l = j
            else:
                l = j
            for i in range(N_lines):
                Qs_n[i, j] = imp_conv.curves[l][i].flow_v.to(flow_unit_out)
                if pr:
                    H_n[i, j] = imp_conv.curves[l][i].disch.p().m / imp_conv.curves[l][i].suc.p().m
                else:
                    H_n[i, j] = imp_conv.curves[l][i].head.to(var1_unit_out)
                eff_n[i, j] = imp_conv.curves[l][i].eff
                speed_n[j] = imp_conv.curves[l][0].speed.to(speed_unit_out)

        return H_n, Qs_n, eff_n, speed_n, imp_conv


    def convert_speeds(speed_n_n, flow_unit_out, var1_unit_out, var2_unit_out, *args):
        # args - Qs_n, H_n, Eff_n, speed_n  in this order
        i = 0
        for var in args:
            if i % 4 == 0:
                if i < 4:
                    Qs_n = var
                else:
                    Qs_n = np.concatenate((Qs_n, var), axis=1)
            elif i % 4 == 1:
                if i < 4:
                    H_n = var
                else:
                    H_n = np.concatenate((H_n, var), axis=1)
            elif i % 4 == 2:
                if i < 4:
                    Eff_n = var
                else:
                    Eff_n = np.concatenate((Eff_n, var), axis=1)
            elif i % 4 == 3:
                if i < 4:
                    speed_n = var
                else:
                    speed_n = np.concatenate((speed_n, var))
            i += 1

        N_speed_n_n = len(speed_n_n.m)
        N_lines_n_n = Qs_n.m.shape[0]

        Qs_n_n = np.zeros((N_lines_n_n, N_speed_n_n))
        H_n_n = np.zeros((N_lines_n_n, N_speed_n_n))
        Eff_n_n = np.zeros((N_lines_n_n, N_speed_n_n))

        desired_speeds = True

        if len(speed_n.m) > 1:
            for i in range(N_speed_n_n):

                closest_curves_idxs = ccp.impeller.find_closest_speeds(speed_n.m, speed_n_n[i].m)

                idx_l = closest_curves_idxs[0]
                idx_h = closest_curves_idxs[1]

                # calculate factor
                speed_range = speed_n[idx_h].m - speed_n[idx_l].m
                factor = (speed_n_n[i].m - speed_n[idx_l].m) / speed_range

                number_of_points = H_n.m.shape[0]
                for j in range(number_of_points):
                    flow_H, H_n_n[j, i] = ccp.impeller.get_interpolated_values(factor,
                                                         flow_0 = Qs_n[j, idx_l].m ,
                                                         val_0 = H_n[j, idx_l].m,
                                                         flow_1 = Qs_n[j, idx_h].m,
                                                         val_1 = H_n[j, idx_h].m
                                                         )
                    flow_Eff, Eff_n_n[j, i] = ccp.impeller.get_interpolated_values(factor,
                                                         flow_0 = Qs_n[j, idx_l].m,
                                                         val_0 = Eff_n[j, idx_l].m,
                                                         flow_1 = Qs_n[j, idx_h].m,
                                                         val_1 = Eff_n[j, idx_h].m
                                                         )

                    Qs_n_n[j, i] = (flow_H + flow_Eff) / 2

            Qs_n_n = Q_(Qs_n_n, flow_unit_out)
            H_n_n = Q_(H_n_n, var1_unit_out)
            Eff_n_n = Q_(Eff_n_n, var2_unit_out)

        else:

            Qs_n_n = Qs_n
            H_n_n = H_n
            Eff_n_n = Eff_n
            speed_n_n = speed_n
            N_speed_n_n = 1
            desired_speeds = False

            n_sheet['O6'].value = "on"
            n_sheet['I8'].value = "Atenção: Vel. Diferente."
            sleep(2)

        return Qs_n_n, H_n_n, Eff_n_n, N_speed_n_n, N_lines_n_n, speed_n_n, desired_speeds

    def convert_speeds_ccp(speed_n_n, flow_unit_out, var1_unit_out, var2_unit_out, imp_n, pr = False):

        # create an impeller that will hold and convert curves.
        print(f'Convertendo para velocidades desejadas...')
        t0 = time.time()
        N_speed_n_n = len(speed_n_n.m)
        curves = []
        N_lines_n_n = []
        desired_speeds = True

        if len(imp_n.curves) > 1:
            for i in range(N_speed_n_n):
                # print(f"\n i: {i} - speed_n_n = {speed_n_n[i].m} {speed_n_n[i].u}")
                curves.append(imp_n.curve(speed_n_n[i]))
                N_lines_n_n.append(len(curves[-1]))
        else:
            curves = imp_n.curves
            speed_n_n = curves[0].speed.to(speed_unit_out)
            N_lines_n_n = [len(curves[0])]
            N_speed_n_n = 1
            desired_speeds = False
            n_sheet['O6'].value = "on"
            n_sheet['I8'].value = "Atenção: Vel. Diferente."
            sleep(2)

        max_lines = max(N_lines_n_n)

        Qs_n_n = Q_(np.zeros((max_lines, N_speed_n_n)), flow_unit_out)
        H_n_n = Q_(np.zeros((max_lines, N_speed_n_n)), var1_unit_out)
        Eff_n_n = Q_(np.zeros((max_lines, N_speed_n_n)), var2_unit_out)

        for j in range(N_speed_n_n):
            curve = curves[j]

            Qs_list = [point.flow_v.to(flow_unit_out).m for point in curve]
            Qs_n_n[:, j] = Q_(np.array(Qs_list), flow_unit_out)

            if pr:
                pr_list = [point.disch.p().m / point.suc.p().m for point in curve]
                H_n_n[:, j] = Q_(np.array(pr_list), var1_unit_out)
            else:
                H_list = [point.head.to(var1_unit_out).m for point in curve]
                H_n_n[:, j] = Q_(np.array(H_list), var1_unit_out)

            Eff_list = [point.eff for point in curve]
            Eff_n_n[:, j] = Q_(np.array(Eff_list), var2_unit_out)

        # for j in range(N_speed_n_n):
        #     for i in range(max_lines):
        #         if i >= N_lines_n_n[j]:
        #             Qs_n_n[i, j] = curves[j][-1].flow_v
        #             H_n_n[i, j] = curves[j][-1].head
        #             Eff_n_n[i, j] = curves[j][-1].eff
        #         else:
        #             Qs_n_n[i, j] = curves[j][i].flow_v.to(flow_unit_out)
        #             if pr:
        #                 curve = curves[j]
        #                 pr_list = [point.disch.p().m/point.suc.p().m for point in curve]
        #                 H_n_n[:, j] = Q_(np.array(pr_list),'dimensionless')
        #             else:
        #                 H_n_n[i, j] = curves[j][i].head.to(var1_unit_out)
        #             Eff_n_n[i, j] = curves[j][i].eff

        tf = time.time()
        dt = tf - t0
        print(f'Tempo convertendo curvas para velocidades desejadas: \n {int(dt / 60)} minutos e {int(dt % 60)} segundos')

        return Qs_n_n, H_n_n, Eff_n_n, N_speed_n_n, max_lines, speed_n_n, desired_speeds


    def extract_pr(imp,var1_unit_out):

        curves = imp.curves
        N_speeds = len(curves)
        H = Q_(np.zeros((N_lines, N_speeds)), var1_unit_out)

        for j in range(N_speeds):
            curve = curves[j]
            pr_list = [point.disch.p().m / point.suc.p().m for point in curve]
            H[:,N_speeds-j-1] = Q_(np.array(pr_list), var1_unit_out)

        return H


    ########################################################################################################################
    ########################################################################################################################
    while Open_file:

        if o_sheet['I6'].value == "OFF":
            Open_file = False

        o_sheet['K16'].value = None
        v_sheet['K16'].value = None
        n_sheet['I9'].value = None
        t_sheet['B32'].value = None
        CF_sheet['O9'].value = None

        if o_sheet['K12'].value == 'on':
            o_sheet.api.Unprotect()
            print('Armazenando dados das curvas de projeto')
            o_sheet['K15'].value = 'Carregando Dados...'

            # suction data - Original
            ############################################# para nao simp - precisa Ps_o2
            #############################################
            try:
                Ps_o = Q_(o_sheet['F5'].value, o_sheet['G5'].value).to('Pa')
                Ts_o = Q_(o_sheet['F6'].value, o_sheet['G6'].value).to('kelvin')
            except TypeError as e:
                o_sheet['K15'].value = 'Erro! P e T de sucção!'
                o_sheet['K16'].value = 'Reinicie o Script!'
                raise e

            MW_question = o_sheet['E8'].value
            simp_question = o_sheet['M17'].value
            excel_question = o_sheet['K13'].value
            excel_questionv = v_sheet['K13'].value
            case2_question = o_sheet['Y8'].value

            if case2_question == "SIM":
                try:
                    Ps2_o = Q_(o_sheet['Z5'].value, o_sheet['AA5'].value).to('Pa')
                    Ts2_o = Q_(o_sheet['Z6'].value, o_sheet['AA6'].value).to('kelvin')
                except TypeError as e:
                    o_sheet['K15'].value = 'Erro! P e T caso 2!'
                    o_sheet['K16'].value = 'Reinicie o Script!'
                    raise e

            if v_sheet['K12'].value == 'on':
                v_sheet.api.Unprotect()
                v_sheet['K15'].value = 'Carregando Dados...'
                try:
                    Ps_v = Q_(v_sheet['F5'].value, v_sheet['G5'].value).to('Pa')
                    Ts_v = Q_(v_sheet['F6'].value, v_sheet['G6'].value).to('kelvin')
                except TypeError as e:
                    v_sheet['K15'].value = 'Erro! P e T de sucção!'
                    v_sheet['K16'].value = 'Reinicie o Script!'
                    raise e

            if MW_question == 'NÃO':
                try:
                    MW_o = Q_(o_sheet['F2'].value, o_sheet['G2'].value).to('kg/mol')
                    ks_o = Q_(o_sheet['F3'].value, 'dimensionless')
                    Zs_o = Q_(o_sheet['F4'].value, 'dimensionless')
                except TypeError as e:
                    o_sheet['K15'].value = 'Erro! Prop. do Gás!'
                    o_sheet['K16'].value = 'Reinicie o Script!'
                    raise e
                km_o = (2 * ks_o - 0.01) / 2  # rough estimative##################################
                Zm_o = (2 * Zs_o - 0.01) / 2  # rough estimative##################################
                gas_constant = Q_(8.314506886527345, 'joule/(kelvin*mol)')
            else:
                suc_o, MW_o, km_o, Zm_o, gas_constant = gas_composition(p=Ps_o, T=Ts_o)

                if case2_question == "SIM":
                    suc2_o, MW2_o, km2_o, Zm2_o, gas_constant = gas_composition(p=Ps2_o, T=Ts2_o, column=23)

                if v_sheet['K12'].value == 'on':
                    suc_v, MW_v, km_v, Zm_v, gas_constant = gas_composition(p=Ps_v, T=Ts_o, sheet = v_sheet)

                try:
                    b = Q_(o_sheet.range('O3').value, o_sheet.range('P3').value)
                    D = Q_(o_sheet.range('O2').value, o_sheet.range('P2').value)
                except TypeError as e:
                    o_sheet['K15'].value = 'Erro! Geometria imp!'
                    o_sheet['K16'].value = 'Reinicie o Script!'
                    raise e



            try:
                speed_rated = Q_(o_sheet['M5'].value, o_sheet['M6'].value).to('rpm')
            except TypeError as e:
                o_sheet['K15'].value = 'Erro! Velocidade nom!'
                o_sheet['K16'].value = 'Reinicie o Script!'
                raise e

            flow_unit = o_sheet.cells(13, 17).value
            flow_type = '[volumetric]'
            if list(Q_(1, flow_unit).dimensionality.keys())[0] == '[mass]':
                flow_type = '[mass]'

            var1_unit = o_sheet.cells(14, 17).value
            if var1_unit == '-':
                var_type = '[pressure ratio]'
                var1_unit = 'dimensionless'
            elif len(list(Q_(1, var1_unit).dimensionality.keys())):
                var1_type = '[head]'
            elif o_sheet.cells(14, 15).value == 'Pressão_descarga_abs':
                var1_type = '[pressure abs]'
            elif o_sheet.cells(14, 15).value == 'Pressão_descarga_man':
                var1_type = '[pressure man]'
            else:
                n_sheet['N8'].value = "Incoerência Unidades!"
                n_sheet['N9'].value = 'Reinicie o Script!'

            var2_unit = o_sheet.cells(15, 17).value
            if var2_unit == '-' or var2_unit == '%':
                var2_type = '[efficiency]'
                var2_unit = 'dimensionless'
            elif o_sheet.cells(15, 15).value == 'Potência_gás':
                var2_type = '[power_gas]'
            elif o_sheet.cells(15, 15).value == 'Potência_eixo':
                var2_type = '[power_shaft]'
            else:
                o_sheet['K15'].value = "Incoerência Unidades!"
                o_sheet['K16'].value = 'Reinicie o Script!'

            speed_unit = o_sheet.cells(16, 17).value

            if excel_question == "excel":
#######################################################################################################################
                N_speed, N_lines, Qs_o, H_o, Eff_o, speed_o = load_from_excel(speed_unit, var1_unit, var2_unit,
                                                              cell_speed_n='D40', column=3)
                if case2_question == "SIM":
                    N2_speed, N2_lines, Qs2_o, H2_o, Eff2_o, speed2_o = load_from_excel(speed_unit, var1_unit, var2_unit,
                                                                                        cell_speed_n='X40', column=23)
                    case2 = True

#######################################################################################################################
            else:
                imp, N_speed, N_lines, Qs_o, H_o, Eff_o, speed_o = array_from_csv(suc_o, "E2", b, D, flow_unit,
                                                                                   var1_unit, speed_unit)
                if case2_question == "SIM":
                    imp2, N2_speed, N2_lines, Qs2_o, H2_o, Eff2_o, speed2_o = array_from_csv(suc2_o, "E3", b, D,
                                                                                           flow_unit,
                                                                                           var1_unit,speed_unit)
                    case2 = True

            if v_sheet['K12'].value == 'on':
                if excel_questionv == "excel":
                    N_speedv, N_linesv, Qs_v, H_v, Eff_v, speed_v = load_from_excel(speed_unit, var1_unit,
                                                                                    var2_unit,
                                                                                    cell_speed_n='D40', column=3,
                                                                                    sheet=v_sheet)
                else:
                    impv, N_speedv, N_linesv, Qs_v, H_v, Eff_v, speed_v = array_from_csv(suc_v, "I2", b, D, flow_unit,
                                                                                      var1_unit, speed_unit)
                val_data = True



            if simp_question == 'SIM' or MW_question == 'NÃO':
                o_sheet['M17'].value = 'SIM'
                np_o = Q_(Eff_o.magnitude * km_o.magnitude / (
                        km_o.magnitude * Eff_o.magnitude + np.ones([N_lines, N_speed]) * (1 - km_o.magnitude)),
                          'dimensionless')
                vr_o = (H_o * (np_o - 1) / np_o * MW_o / (Zm_o * gas_constant * Ts_o) + 1) ** (1 / (np_o - 1))
                vr_o = vr_o.to('dimensionless')
                case2 = False
            elif excel_question == "excel":
                imp = impeller_from_excel(N_speed, speed_array=speed_o,Qs=Qs_o, H=H_o, Eff=Eff_o)

                if case2_question == "SIM":
                    imp2 = impeller_from_excel(N_speed=N2_speed, speed_array=speed2_o, Qs=Qs2_o, H=H2_o, Eff=Eff2_o)
                    case2 = True

                ######################################################

            print('Dados carregados')
            o_sheet['K15'].value = 'Dados Carregados'
            if v_sheet['K12'].value == 'on':
                v_sheet['K15'].value = 'Dados Carregados'
            v_sheet['K12'].value = 'off'
            o_sheet['K12'].value = 'off'
            o_sheet.api.Protect()
            v_sheet.api.Protect()

        # New condition
#####################################################################################################################
#####################################################################################################################
        if n_sheet['I5'].value == 'on' and o_sheet['K15'].value == 'Dados Carregados':
            n_sheet.api.Unprotect()

            print('Armazenando dados da nova condição operacional')
            n_sheet['I8'].value = 'Carregando Dados...'
            simp_question = o_sheet['M17'].value
            #speed_question = n_sheet["l12"].value

            # 1 section suction data - New Condition
            try:
                Ps_n = Q_(n_sheet['F5'].value, n_sheet['G5'].value).to('Pa') + Q_(1, 'atm').to('Pa')
                Ts_n = Q_(n_sheet['F6'].value, n_sheet['G6'].value).to('kelvin')
            except TypeError as e:
                n_sheet['I8'].value = 'Erro! P e T de sucção!'
                n_sheet['I9'].value = 'Reinicie o Script!'
                raise e

            MW_question = n_sheet['E8'].value

            if MW_question == 'NÃO':
                try:
                    MW_n = Q_(n_sheet['F2'].value, n_sheet['G2'].value)
                    ks_n = Q_(n_sheet['F3'].value, 'dimensionless')
                    Zs_n = Q_(n_sheet['F4'].value, 'dimensionless')
                except TypeError as e:
                    n_sheet['I8'].value = 'Erro! Prop. do Gás!'
                    n_sheet['I9'].value = 'Reinicie o Script!'
                    raise e
                km_n = (2 * ks_n - 0.01) / 2  # rough estimative##################################
                Zm_n = (2 * Zs_n - 0.01) / 2  # rough estimative##################################
                gas_constant = Q_(8.314506886527345, 'joule/(kelvin*mol)')
            else:
                suc_n, MW_n, km_n, Zm_n, gas_constant = gas_composition(p=Ps_n, T=Ts_n,sheet = n_sheet,o_sheet_template=False)

            flow_unit_out = n_sheet['S4'].value
            flow_type_out = '[volumetric]'
            if list(Q_(1, flow_unit_out).dimensionality.keys())[0] == '[mass]':
                flow_type_out = '[mass]'

            pr = False
            var1_unit_out = n_sheet['S5'].value
            if var1_unit_out == '-':
                var1_type_out = '[pressure ratio]'
                var1_unit_out = 'dimensionless'
                pr = True
            elif len(list(Q_(1, var1_unit_out).dimensionality.keys())):
                var1_type_out = '[head]'
            elif n_sheet['Q5'].value == 'Pressão_descarga_abs':
                var1_type_out = '[pressure abs]'
            elif n_sheet['Q5'].value == 'Pressão_descarga_man':
                var1_type_out = '[pressure man]'
            else:
                n_sheet['I8'].value = "Incoerência Unidades!"
                n_sheet['I9'].value = 'Reinicie o Script!'

            var2_unit_out = n_sheet['S6'].value
            if var2_unit_out == '-' or var2_unit_out == '%':
                var2_type_out = '[efficiency]'
                var2_unit_out = 'dimensionless'
            elif n_sheet['Q6'].value == 'Potência_gás':
                var2_type_out = '[power_gas]'
            elif n_sheet['Q6'].value == 'Potência_eixo':
                var2_type_out = '[power_shaft]'
            else:
                n_sheet['I8'].value = "Incoerência Unidades!"
                n_sheet['I9'].value = 'Reinicie o Script!'

            speed_unit_out = n_sheet['S7'].value

            speed_o = speed_o.to(speed_unit_out)
            if pr:
                H_o = extract_pr(imp,var1_unit_out)
            else:
                H_o = H_o.to(var1_unit_out)
            Qs_o = Qs_o.to(flow_unit_out)

            speed_n_n = speed_o
            if n_sheet["J17"].value != None:
                for i in range(9):
                    if n_sheet.cells(17 + i, 10).value == None:
                        NT = i
                        break
                speeds_array = np.array(n_sheet.range((17, 10), (17 + NT - 1, 10)).value)
                if NT > 1:
                    index = np.argsort(speeds_array)[::-1]
                    speed_n_n = Q_(speeds_array[index], speed_unit_out)
                else:
                    speed_n_n = Q_(np.array([speeds_array]), speed_unit_out)
            print('Convertendo as curvas de performance.')
            n_sheet['I8'].value = 'Convertendo Curvas...'
            # Convert the curves
            if simp_question == 'SIM' or MW_question == 'NÃO':
                try:
                    vr_o
                except NameError:
                    np_o = Q_(Eff_o.magnitude * km_o.magnitude / (
                            km_o.magnitude * Eff_o.magnitude + np.ones([N_lines, N_speed]) * (1 - km_o.magnitude)),
                              'dimensionless')
                    vr_o = (H_o * (np_o - 1) / np_o * MW_o / (Zm_o * gas_constant * Ts_o) + 1) ** (1 / (np_o - 1))
                    vr_o = vr_o.to('dimensionless')

                o_sheet['M17'].value = 'SIM'

                # Similarity condition
                Eff_n = Eff_o
                vr_n = vr_o

                np_n = Q_(np.zeros((N_lines, N_speed)), 'dimensionless')
                H_n = Q_(np.zeros((N_lines, N_speed)), var1_unit_out)
                speed_n_matrix = Q_(np.zeros((N_lines, N_speed)), speed_unit_out)
                Qs_n = Q_(np.zeros((N_lines, N_speed)), flow_unit_out)

                np_n = Eff_n * km_n / (km_n * Eff_n + np.ones([N_lines, N_speed]) * (1 - km_n))
                H_n = np_n / (np_n - 1) * Zm_n * gas_constant / MW_n * Ts_n * ((vr_n) ** (np_n - 1) - 1)

                for i in range(N_speed):
                    speed_n_matrix[:, i] = speed_o[i] * (H_n[:, i] / H_o[:, i]) ** (1 / 2)
                    Qs_n[:, i] = Qs_o[:, i] * (speed_n_matrix[:, i] / speed_o[i])

                # New speed values
                speed_n = Q_(np.mean(speed_n_matrix.magnitude, axis=0), speed_n_matrix.units)

            else:
                H_n, Qs_n, Eff_n, speed_n, imp_n = convert_and_store(imp, N_speed, N_lines, flow_unit_out, var1_unit_out,
                                                              var2_unit_out, pr = pr)

                if case2_question == "SIM" and case2:
                    H2_n, Qs2_n, Eff2_n, speed2_n, imp2_n = convert_and_store(imp2, N2_speed, N2_lines, flow_unit_out, var1_unit_out,
                                                                      var2_unit_out, pr = pr)



            # calculate curves to desired speeds
            if simp_question == 'SIM' or MW_question == 'NÃO':

                Qs_n_n, H_n_n, Eff_n_n, N_speed_n_n, N_lines_n_n, speed_n_n, desired_speeds = convert_speeds(speed_n_n,
                                                                                            flow_unit_out,
                                                                                            var1_unit_out,
                                                                                            var2_unit_out,
                                                                                            Qs_n, H_n, Eff_n,
                                                                                            speed_n)
            else:

                # if speed_question == "Interpolação entre 2 Rotações":
                if case2_question == "SIM" and case2:
                    print(f'Consolidando curvas em único impelidor...')
                    t0 = time.time()
                    # for i in range(len(imp2_n.points)):
                    #     imp.points.append(imp2.points[i])
                    #     imp_n.points.append(imp2_n.points[i])
                    tf = time.time()
                    dt = tf -  t0
                    print(f'Tempo consolidando curvas: {int(dt/60)} minutos e {int(dt%60)} segundos.')

                Qs_n_n, H_n_n, Eff_n_n, N_speed_n_n, N_lines_n_n, speed_n_n, desired_speeds = convert_speeds_ccp(speed_n_n, flow_unit_out,
                                                                                      var1_unit_out, var2_unit_out,
                                                                                      imp_n, pr = pr )




            n_sheet['C41:E1416'].value = [[None] * (3)] * (1414 - 41 + 1)
            n_sheet['D39'].value = None
            print('Curvas convertidas')
            n_sheet['I8'].value = 'Curvas Convertidas'
            n_sheet['I5'].value = 'off'
            n_sheet.api.Protect()

        ###################################
        ##calculate flow
        CalcFlow_tag = CF_sheet['O3'].value

        if CF_sheet['O3'].value == 'on' and n_sheet['E8'].value != 'NÃO':

            CF_sheet.api.Unprotect()
            print('Calculando vazao massica - ISO 5167.')
            CF_sheet['O7'].value = 'Calculando Vazão...'
            P_normal = Q_(1, 'atm')
            T_normal = Q_(0, 'degC')
            try:
                disch_normal_n, _, _, _, gas_constant = gas_composition(p=P_normal, T=T_normal,
                                                                                              sheet = n_sheet,
                                                                                              o_sheet_template=False,
                                                                                              output_sheet=False)
                disch_normal_o, _, _, _, _ = gas_composition(p=P_normal, T=T_normal, output_sheet=False)

            except TypeError:
                CF_sheet['O7'].value = 'Erro! %molar!'
                CF_sheet['O8'].value = 'Reinicie o Script!'
            fluid_n = disch_normal_n.fluid

            global qm

            from scipy.optimize import newton

            Units = CF_sheet['C4:L4'].value

            i = 4
            data = np.array(CF_sheet[i, 2:9].value)

            while len(data[data == None]) == 0:

                D = Q_(float(data[0]), Units[0])
                d = Q_(float(data[1]), Units[1])
                P1 = Q_(float(data[2]), Units[2]) + Q_(1, 'atm').to(Units[2])
                T1 = Q_(float(data[3]), Units[3])
                dP = Q_(float(data[4]), Units[4])
                gas = data[5]
                tappings = data[6]

                P2 = P1 - dP
                fluid = fluid_n
                if gas == 'Original':
                    fluid = disch_normal_o.fluid
                try:
                    State_FO = ccp.State(fluid=fluid, p=P1, T=T1)
                except ValueError:
                    CF_sheet['O7'].value = 'Composição do Gás!'
                    CF_sheet['O8'].value = 'Reinicie o Script!'

                beta = d / D
                mu = State_FO.viscosity()
                rho = State_FO.rho()
                k = State_FO.kv()

                e = 1 - (0.351 + 0.256 * (beta ** 4) + 0.93 * (beta ** 8)) * (1 - (P2 / P1) ** (1 / k))

                if tappings == 'corner':
                    L1 = L2 = 0
                elif tappings == 'D D/2':
                    L1 = 1
                    L2 = 0.47
                elif tappings == 'flange':
                    L1 = L2 = Q_(0.0254, 'm') / D

                M2 = 2 * L2 / (1 - beta)


                def update_Re(Re):
                    global qm

                    Re = Q_(Re, 'dimensionless')
                    # calc C
                    C = (
                            0.5961 + 0.0261 * beta ** 2 - 0.216 * beta ** 8
                            + 0.000521 * (1e6 * beta / Re) ** 0.7
                            + (0.0188 + 0.0063
                               * (19000 * beta / Re) ** 0.8) * beta ** 3.5 * (1e6 / Re) ** 0.3
                            + (0.043 + 0.080 * np.e ** (-10 * L1) - 0.123 * np.e ** (-7 * L1))
                            * (1 - 0.11 * (19000 * beta / Re) ** 0.8) * (beta ** 4 / (1 - beta ** 4))
                            - 0.031 * (M2 - 0.8 * M2 ** 1.1) * beta ** 1.3
                    )

                    if D < Q_(71.12, 'mm'):
                        C += 0.011 * (0.75 - beta) * (2.8 - D / Q_(25.4, 'mm'))

                    qm = C / (np.sqrt(1 - beta ** 4)) * e * (np.pi / 4) * d ** 2 * np.sqrt(2 * dP * rho)

                    Re_qm = (4 * qm / (mu * np.pi * D)).to('dimensionless').magnitude

                    return abs(Re_qm - Re.magnitude)


                newton(update_Re, 1e8, tol=1e-5)

                Re = D / mu * qm / (np.pi * D ** 2 / 4)
                disch_normal = disch_normal_n
                if gas == 'Original':
                    disch_normal = disch_normal_o
                CF_sheet[i, 9].value = qm.to(Units[7]).magnitude
                flow_normal = disch_normal.z() * gas_constant * T_normal.to('kelvin') * qm / (
                        disch_normal.molar_mass() * P_normal)
                CF_sheet[i, 10].value = flow_normal.to(Units[8]).magnitude

                flow_rate = qm / ccp.State(p=P1, T=T1, fluid=fluid).rho()
                CF_sheet[i, 11].value = flow_rate.to(Units[9]).magnitude
                i += 1
                data = np.array(CF_sheet[i, 2:9].value)

            print('Vazão calculada')

            CF_sheet['O7'].value = 'Vazão Calculada'
            CF_sheet['O3'].value = 'off'
            CF_sheet.api.Protect()

        ##############
        # Tested points

        if t_sheet['B27'].value == 'on' and n_sheet['E8'].value != 'NÃO':

            t_sheet.api.Unprotect()
            print('Calculando Performance...')
            t_sheet['B31'].value = 'Calculando Performance...'

            P_normal=Q_(1, 'atm')
            T_normal=Q_(0, 'degC')
            try:
                disch_normal_n, MW_normal, km_normal, Zm_normal, gas_constant = gas_composition(p=P_normal, T=T_normal,
                                                                                              sheet=n_sheet,
                                                                                              o_sheet_template=False,
                                                                                          output_sheet=False)
                disch_normal_o, _, _, _, _ = gas_composition(p=P_normal, T=T_normal, output_sheet=False)
            except TypeError:
                t_sheet['B31'].value = 'Erro! %molar!'
                t_sheet['B32'].value = 'Reinicie o Script!'
            fluid_n = disch_normal_n.fluid

            try:
                b = Q_(o_sheet.range('O3').value, o_sheet.range('P3').value)
                D = Q_(o_sheet.range('O2').value, o_sheet.range('P2').value)
            except TypeError as e:
                o_sheet['K15'].value = 'Erro! Geometria imp!'
                o_sheet['K16'].value = 'Reinicie o Script!'
                raise e

            for i in range(40):
                if t_sheet.cells(5, 5 + i).value == None:
                    NT = i
                    break

            if NT != 0:
                # t_sheet['E20:Q20'].value=[None]*14
                t_sheet['E21:Q21'].value = [None] * 14
                t_sheet['E22:Q22'].value = [None] * 14
                P_test = []
                index_o = []
                index = []

                for i in range(NT):
                    if CF_sheet['O7'].value == 'Vazão Calculada':
                        t_sheet.cells(20, 5 + i).value = Q_(CF_sheet.cells(5 + i, 10).value,
                                                            CF_sheet.cells(4, 10).value).to(
                            t_sheet.cells(20, 4).value).magnitude
                    Ps_T = Q_(t_sheet.cells(5, 5 + i).value, t_sheet.cells(5, 4).value) + Q_(1, 'atm').to('Pa')
                    Ts_T = Q_(t_sheet.cells(6, 5 + i).value, t_sheet.cells(6, 4).value)
                    Pd_T = Q_(t_sheet.cells(7, 5 + i).value, t_sheet.cells(7, 4).value) + Q_(1, 'atm').to('Pa')
                    Td_T = Q_(t_sheet.cells(8, 5 + i).value, t_sheet.cells(8, 4).value)
                    gas = t_sheet.cells(13, 5 + i).value
                    fluid = fluid_n
                    disch_normal = disch_normal_n
                    if gas == 'Original':
                        fluid = disch_normal_o.fluid
                        disch_normal = disch_normal_o
                    try:
                        disch_normal = ccp.State(p=Q_(1, 'atm'), T=Q_(0, 'degC'), fluid=fluid)
                    except ValueError:
                        t_sheet['B31'].value = 'Composição do Gás!'
                        t_sheet['B32'].value = 'Reinicie o Script!'
                    if t_sheet.cells(20, 5 + i).value != None:
                        flow_m = Q_(t_sheet.cells(20, 5 + i).value, t_sheet.cells(20, 4).value)
                        flow_normal = disch_normal.z() * disch_normal.gas_constant() * Q_(0, 'degC').to('kelvin') * flow_m / (
                                disch_normal.molar_mass() * Q_(1, 'atm'))
                        t_sheet.cells(22, 5 + i).value = flow_normal.to(t_sheet.cells(22, 4).value).magnitude
                    elif t_sheet.cells(9, 5 + i).value == None:
                        t_sheet['B31'].value = 'Vazão do Gás!'
                        t_sheet['B32'].value = 'Reinicie o Script!'
                        raise ValueError('Mass flow or Normal flow rate must be provided!')
                    else:
                        flow_m = Q_(1, 'atm') * Q_(t_sheet.cells(9, 5 + i).value,
                                                   t_sheet.cells(9, 4).value) * disch_normal.molar_mass() / (
                                         disch_normal.z() * disch_normal.gas_constant() * Q_(0, 'degC').to('kelvin'))
                        t_sheet.cells(20, 5 + i).value = flow_m.to(t_sheet.cells(20, 4).value).magnitude

                    speed_T = Q_(t_sheet.cells(12, 5 + i).value, t_sheet.cells(12, 4).value)
                    suc_T = ccp.State(p=Ps_T, T=Ts_T, fluid=fluid)
                    disch_T = ccp.State(p=Pd_T, T=Td_T, fluid=fluid)

                    P_test.append(ccp.Point(speed=speed_T, flow_m=flow_m, suc=suc_T, disch=disch_T, b=b, D=D))

                    if gas == 'Original':
                        index_o.append(i)
                    else:
                        index.append(i)

                for i in range(NT):
                    t_sheet.cells(14, 5 + i).value = P_test[i].head.to(t_sheet.cells(14, 4).value).magnitude
                    t_sheet.cells(15, 5 + i).value = P_test[i].eff.magnitude * 100
                    t_sheet.cells(16, 5 + i).value = P_test[i].power.to(t_sheet.cells(16, 4).value).magnitude
                    t_sheet.cells(21, 5 + i).value = P_test[i].flow_v.to(t_sheet.cells(21, 4).value).magnitude

            print('Performance calculada')

            t_sheet['B31'].value = 'Performance Calculada'
            t_sheet['B27'].value = 'off'
            t_sheet.api.Protect()

        #############################################################
        # Export converted curves data (flow,head,efficiency) to excel

        if n_sheet['N5'].value == 'on' and o_sheet['K15'].value == 'Dados Carregados' and n_sheet[
            'I8'].value == 'Curvas Convertidas':

            n_sheet.api.Unprotect()

            # flow_unit_out = n_sheet['S4'].value
            # var1_unit_out = n_sheet['S5'].value
            # speed_unit_out = n_sheet['S7'].value

            # store variables (Head,speed,flow,eff,power) in numpy arrays
            if t_sheet.range('C18').value == 'SIM' and t_sheet['B31'].value == 'Performance Calculada':
                n_sheet['N8'].value = 'Carregando dados do teste...'
                flow_v_T = Q_(np.zeros(NT), flow_unit_out)
                Head_T = Q_(np.zeros(NT), var1_unit_out)
                eff_T = np.zeros(NT)
                speed_T = Q_(np.zeros(NT), speed_unit_out)
                for i in range(NT):
                    if pr:
                        Head_T[i] = P_test[i].disch.p()/P_test[i].suc.p()
                    else:
                        Head_T[i] = P_test[i].head
                    speed_T[i] = P_test[i].speed
                    flow_v_T[i] = P_test[i].flow_v
                    eff_T[i] = P_test[i].eff.magnitude

            print('Plotando os gráficos.')
            n_sheet['N8'].value = 'Plotando Gráficos...'
            count = 41
            n_sheet['D39'].value = N_speed_n_n

            #
            speed_symbol_out = a_sheet['L24'].value
            ##################################################################
            if flow_type_out == '[volumetric]':
                flow_symbol_out = a_sheet['M24'].value
            else:
                flow_symbol_out = a_sheet['N24'].value

            if var1_type_out == '[head]':
                var1_symbol_out = a_sheet['O24'].value
            elif var1_type_out == '[pressure abs]':
                var1_symbol_out = a_sheet['P24'].value
            elif var1_type_out == '[pressure man]':
                var1_symbol_out = a_sheet['Q24'].value
            else:
                var1_symbol_out = a_sheet['R24'].value

            if var2_type_out == '[efficiency]':
                var2_symbol_out = a_sheet['S24'].value
            elif var2_type_out == '[power_gas]':
                var2_symbol_out = a_sheet['T24'].value
            else:
                var2_symbol_out = a_sheet['U24'].value
            ##################################################################

            for j in range(N_speed_n_n):
                # if j == 0:
                # count +=1
                count += 1
                n_sheet.cells(count, 3).value = round(speed_n_n[j].to(speed_unit_out).magnitude, 0)
                n_sheet.cells(count, 4).value = speed_symbol_out
                count += 1
                n_sheet.cells(count, 3).value = flow_symbol_out
                n_sheet.cells(count, 4).value = var1_symbol_out
                n_sheet.cells(count, 5).value = var2_symbol_out
                for i in range(N_lines_n_n):
                    if i == 0:
                        count += 1
                    n_sheet.cells(count, 3).value = round(Qs_n_n[i, j].to(flow_unit_out).magnitude, 1)
                    n_sheet.cells(count, 4).value = round(H_n_n[i, j].to(var1_unit_out).magnitude, 1)
                    if var2_type_out == '[efficiency]':
                        if var2_symbol_out == '%':
                            n_sheet.cells(count, 5).value = int(round(Eff_n_n[i, j].magnitude * 100, 0))
                        else:
                            n_sheet.cells(count, 5).value = round(Eff_n_n[i, j].magnitude * 100, 1)
                    count += 1
                    if i == (N_lines - 1):
                        count += 1

            ################################
            ################################
            # Plot curves and export to excel

            figs_o = []
            figs_n = []
            figs_n_n = []
            figs_comp = []

            speed_n_n = speed_n_n.to(speed_unit_out)
            Qs_n_n = Qs_n_n.to(flow_unit_out)
            H_n_n = H_n_n.to(var1_unit_out)
            speed_fraction_n_n = speed_n_n / speed_rated
            speed_fraction_n_n = speed_fraction_n_n.to('dimensionless')

            speed_n = speed_n.to(speed_unit_out)
            Qs_n = Qs_n.to(flow_unit_out)
            if pr:
                H_n = extract_pr(imp_n,var1_unit_out)
            else:
                H_n = H_n.to(var1_unit_out)
            speed_fraction_n = speed_n / speed_rated
            speed_fraction_n = speed_fraction_n.to('dimensionless')

            speed_o = speed_o.to(speed_unit_out)
            Qs_o = Qs_o.to(flow_unit_out)
            # if pr:
            #     H_o = extract_pr(imp,var1_unit_out)
            # else:
            H_o = H_o.to(var1_unit_out)
            speed_fraction_o = speed_o / speed_rated
            speed_fraction_o = speed_fraction_o.to('dimensionless')

            if case2_question == 'SIM' and o_sheet['AC4'].value == 'SIM' and case2:
                speed2_n = speed2_n.to(speed_unit_out)
                Qs2_n = Qs2_n.to(flow_unit_out)
                if pr:
                    H2_n = extract_pr(imp2_n, var1_unit_out)
                else:
                    H2_n = H2_n.to(var1_unit_out)
                speed2_fraction_n = speed2_n / speed_rated
                speed2_fraction_n = speed2_fraction_n.to('dimensionless')

                speed2_o = speed2_o.to(speed_unit_out)
                Qs2_o = Qs2_o.to(flow_unit_out)
                if pr:
                    H2_o = extract_pr(imp2, var1_unit_out)
                else:
                    H2_o = H2_o.to(var1_unit_out)
                speed2_fraction_o = speed2_o / speed_rated
                speed2_fraction_o = speed2_fraction_o.to('dimensionless')

            if v_sheet.range('E8').value == 'SIM' and val_data:
                speed_v = speed_v.to(speed_unit_out)
                Qs_v = Qs_v.to(flow_unit_out)
                H_v = H_v.to(var1_unit_out)
                speed_fraction_v = speed_v / speed_rated
                speed_fraction_v = speed_fraction_v.to('dimensionless')

            #################################################################
            # Original curves (design/shop test) x New conditions (field test)

            Data_compH = list()
            Data_compEff = list()

            # colors
            palette = cycle(px.colors.qualitative.Bold)
            palette = cycle(['darkslateblue', 'mediumblue', 'dodgerblue', 'orangered','red'])
            color = list()
            soma = N_speed


            if case2_question == 'SIM' and o_sheet['AC4'].value == 'SIM' and case2:
                soma = N_speed + N2_speed

            for i in range(max(soma, N_speed_n_n)):
                color.append(next(palette))

            for i in range(N_speed_n_n):

                i_color = i
                if MW_n > MW_o:
                    i = N_speed_n_n - i - 1

                Data_compH.append(go.Scatter(x=Qs_n_n[:, i], y=H_n_n[:, i],
                                             line=dict(color=color[i_color],
                                                       width=1, dash='dash'), mode='lines',#marker=dict(size=4),
                                             name=str(int(speed_n_n[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                 int(round(100 * speed_fraction_n_n[i].magnitude,
                                                           0))) + '% N<sub>rated</sub>' + '- converted'))
                Data_compEff.append(go.Scatter(x=Qs_n_n[:, i], y=100 * Eff_n_n[:, i],
                                               line=dict(color=color[i_color],
                                                         width=1, dash='dash'), mode='lines',#marker=dict(size=4),
                                               name=str(int(speed_n_n[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                   int(round(100 * speed_fraction_n_n[i].magnitude,
                                                             0))) + '% N<sub>rated</sub>' + '- converted'))
            for i in range(N_speed):

                i_color = i
                if MW_n > MW_o:
                    i = N_speed - i - 1

                Data_compH.append(go.Scatter(x=Qs_o[:, i], y=H_o[:, i],
                                             marker=dict(color=color[i_color],
                                                         size=1.5,
                                                         line=dict(
                                                             color=color[i_color],
                                                             width=2)),
                                             name=str(int(speed_o[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                 int(round(100 * speed_fraction_o[i].magnitude,
                                                           0))) + '% N<sub>rated</sub>' + '- design'))
                                             #name=str(int(speed_o[i].magnitude)) + ' ' + speed_unit_out + ' - design'))
                Data_compEff.append(go.Scatter(x=Qs_o[:, i], y=100 * Eff_o[:, i],
                                               marker=dict(color=color[i_color],
                                                           size=1.5,
                                                           line=dict(
                                                               color=color[i_color],
                                                               width=2)),
                                               name=str(int(speed_o[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                   int(round(100 * speed_fraction_o[i].magnitude,
                                                             0))) + '% N<sub>rated</sub>' + '- design'))
                                               # name=str(
                                               #     int(speed_o[i].magnitude)) + ' ' + speed_unit_out + ' - design'))
            if case2_question == 'SIM' and o_sheet['AC4'].value == 'SIM' and case2:
                for i in range(N2_speed):

                    i_color = i
                    if MW_n > MW_o:
                        i = N2_speed - i - 1

                    Data_compH.append(go.Scatter(x=Qs2_o[:, i], y=H2_o[:, i],
                                                 line=dict(color=color[i+N_speed],
                                                           width=1, dash='dot'), marker=dict(size=4),
                                                 # marker=dict(color=color[i_color],
                                                 #             size=1.5,
                                                 #             line=dict(
                                                 #                 color=color[i_color],
                                                 #                 width=2)),
                                                 name=str(
                                                     int(speed2_o[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                     int(round(100 * speed2_fraction_o[i].magnitude,
                                                               0))) + '% N<sub>rated</sub>' + '- design 2'))
                                                 # name=str(int(speed2_o[i].magnitude)) + ' ' + speed_unit_out + ' - case 2'))
                    Data_compEff.append(go.Scatter(x=Qs2_o[:, i], y=100 * Eff2_o[:, i],
                                                   line=dict(color=color[i+N_speed],
                                                             width=1, dash='dot'), marker=dict(size=4),
                                                   # marker=dict(color=color[i_color],
                                                   #             size=1.5,
                                                   #             line=dict(
                                                   #                 color=color[i_color],
                                                   #                 width=2)),
                                                   name=str(
                                                       int(speed2_o[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                       int(round(100 * speed2_fraction_o[i].magnitude,
                                                                 0))) + '% N<sub>rated</sub>' + '- design 2'))
                                                   # name=str(
                                                   #     int(speed2_o[i].magnitude)) + ' ' + speed_unit_out + ' - case 2'))




            if t_sheet.range('C18').value == 'SIM' and t_sheet['B31'].value == 'Performance Calculada':
                Data_compH.append(go.Scatter(x=flow_v_T[index], y=Head_T[index], opacity=0.55,
                                             marker=dict(color='gold', size=9, line=dict(width=1.5, color='black')),
                                             mode='markers', name='Test'))

                Data_compEff.append(go.Scatter(x=flow_v_T[index], y=100 * eff_T[index], opacity=0.55,
                                               marker=dict(color='gold', size=9, line=dict(width=1.5, color='black')),
                                               mode='markers', name='Test'))

                if len(index_o) > 0:
                    Data_compH.append(go.Scatter(x=flow_v_T[index_o], y=Head_T[index_o], opacity=0.55,
                                                 marker=dict(color='red', size=9, line=dict(width=1.5, color='black')),
                                                 mode='markers', name='Test - design gas'))
                    Data_compEff.append(go.Scatter(x=flow_v_T[index_o], y=100 * eff_T[index_o], opacity=0.55,
                                                   marker=dict(color='red', size=9,
                                                               line=dict(width=1.5, color='black')),
                                                   mode='markers', name='Test - design gas'))

            Data_compH = tuple(Data_compH)
            Data_compEff = tuple(Data_compEff)

            if pr:
                fig = go.Figure(
                    Data_compH,
                    layout_title_text="Razão de Compressão x Vazão Volumétrica de Sucção"
                )
                fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')',
                                  yaxis_title='r<sub>c</sub> (' + var1_unit_out + ')', showlegend=True)
            else:
                fig = go.Figure(
                    Data_compH,
                    layout_title_text="Head Politrópico x Vazão Volumétrica de Sucção"
                )
                fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')',
                                  yaxis_title='H<sub>p</sub> (' + var1_unit_out + ')', showlegend=True)

            figs_comp.append(fig)

            fig = go.Figure(
                Data_compEff,
                layout_title_text="Eficiência Politrópica x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')', yaxis_title='\u03b7<sub>p</sub> (%)',
                              showlegend=True)
            figs_comp.append(fig)

            for i, fig in enumerate(figs_comp):
                w = 1000
                h = 500
                fig.update_layout(width=w, height=h)
                try:
                    comp_sheet.pictures.add(fig, top=i * (h - 100))
                except:
                    pass

            ###################################
            # Original curves (design/shop test)

            Data_H = list()
            Data_eff = list()

            for i in range(N_speed):

                i_color = i
                if MW_n > MW_o:
                    i = N_speed - i - 1

                Data_H.append(go.Scatter(x=Qs_o[:, i], y=H_o[:, i],
                                         marker=dict(color=color[i_color],
                                                     size=1.5,
                                                     line=dict(
                                                         color=color[i_color],
                                                         width=2)),
                                         name=str(int(speed_o[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                             int(round(100 * speed_fraction_o[i].magnitude,
                                                       0))) + '% N<sub>rated</sub> - design'))
                Data_eff.append(go.Scatter(x=Qs_o[:, i], y=Eff_o[:, i] * 100,
                                           marker=dict(color=color[i_color],
                                                       size=1.5,
                                                       line=dict(
                                                           color=color[i_color],
                                                           width=2)),
                                           name=str(int(speed_o[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                               int(round(100 * speed_fraction_o[i].magnitude,
                                                         0))) + '% N<sub>rated</sub> - design'))

            if case2_question == 'SIM' and o_sheet['AC4'].value == 'SIM' and case2:
                for i in range(N2_speed):

                    i_color = i
                    if MW_n > MW_o:
                        i = N2_speed - i - 1

                    Data_H.append(go.Scatter(x=Qs2_o[:, i], y=H2_o[:, i],
                                                line=dict(color=color[i + N_speed],
                                                width=1, dash='dot'), marker=dict(size=4),
                                                 # marker=dict(color=color[i_color],
                                                 #             size=1.5,
                                                 #             line=dict(
                                                 #                 color=color[i_color],
                                                 #                 width=2)),
                                                name=str(int(speed2_o[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                int(round(100 * speed2_fraction_o[i].magnitude,
                                                           0))) + '% N<sub>rated</sub> - design 2'))
                                                 # name=str(int(speed2_o[i].magnitude)) + ' ' + speed_unit_out + ' - case 2'))
                    Data_eff.append(go.Scatter(x=Qs2_o[:, i], y=100 * Eff2_o[:, i],
                                               line=dict(color=color[i + N_speed],
                                                         width=1, dash='dot'), marker=dict(size=4),
                                                   # marker=dict(color=color[i_color],
                                                   #             size=1.5,
                                                   #             line=dict(
                                                   #                 color=color[i_color],
                                                   #                 width=2)),
                                                   name=str(
                                                   int(speed2_o[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                   int(round(100 * speed2_fraction_o[i].magnitude,
                                                             0))) + '% N<sub>rated</sub> - design 2'))
                                                   # name=str(
                                                   #     int(speed2_o[i].magnitude)) + ' ' + speed_unit_out + ' - case 2'))

            Data_H = tuple(Data_H)
            Data_eff = tuple(Data_eff)

            if pr:
                fig = go.Figure(
                    Data_H,
                    layout_title_text="Razão de Compressão x Vazão Volumétrica de Sucção"
                )
                fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')',
                                  yaxis_title='r<sub>c</sub> (' + var1_unit_out + ')', showlegend=True)
            else:
                fig = go.Figure(
                    Data_H,
                    layout_title_text="Head Politrópico x Vazão Volumétrica de Sucção"
                )
                fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')',
                                  yaxis_title='H<sub>p</sub> (' + var1_unit_out + ')', showlegend=True)

            figs_o.append(fig)

            fig = go.Figure(
                Data_eff,
                layout_title_text="Eficiência Politrópica x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')', yaxis_title='\u03b7<sub>p</sub> (%)',
                              showlegend=True)
            figs_o.append(fig)

            for i, fig in enumerate(figs_o):
                w = 1000
                h = 500
                fig.update_layout(width=w, height=h)
                try:
                    graf_.pictures.add(fig, top=i * (h - 100))
                except:
                    pass

            ####################################################################
            # New curves - performance curves before converted to original speeds

            Data_H_n = list()
            Data_eff_n = list()

            for i in range(N_speed):

                i_color = i
                if MW_n > MW_o:
                    i = N_speed - i - 1

                Data_H_n.append(go.Scatter(x=Qs_n[:, i], y=H_n[:, i],
                                           line=dict(color=color[i_color],
                                                     width=1, dash='dash'),  mode='lines',#marker=dict(size=4),
                                           name=str(int(speed_n[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                               int(round(100 * speed_fraction_n[i].magnitude,
                                                         0))) + '% N<sub>rated</sub> - converted from design'))
                Data_eff_n.append(go.Scatter(x=Qs_n[:, i], y=Eff_n[:, i] * 100,
                                             line=dict(color=color[i_color],
                                                       width=1, dash='dash'),  mode='lines',#marker=dict(size=4),
                                             name=str(int(speed_n[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                 int(round(100 * speed_fraction_n[i].magnitude,
                                                           0))) + '% N<sub>rated</sub> - converted from design'))
            if case2_question == 'SIM' and o_sheet['AC4'].value == 'SIM' and case2:
                for i in range(N2_speed):

                    i_color = i
                    if MW_n > MW_o:
                        i = N2_speed - i - 1

                    Data_H_n.append(go.Scatter(x=Qs2_n[:, i], y=H2_n[:, i],
                                               line=dict(color=color[i + N_speed],
                                                         width=1, dash='longdashdot'),  mode='lines',#marker=dict(size=4),
                                               # line=dict(color=color[i_color],
                                               #           width=1, dash='dash'), marker=dict(size=4),
                                               name=str(int(speed2_n[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                   int(round(100 * speed2_fraction_n[i].magnitude,
                                                             0))) + '% N<sub>rated</sub> - converted from design 2'))
                    Data_eff_n.append(go.Scatter(x=Qs2_n[:, i], y=Eff2_n[:, i] * 100,
                                                 line=dict(color=color[i + N_speed],
                                                           width=1, dash='longdashdot'),  mode='lines',#marker=dict(size=4),
                                                 # line=dict(color=color[i_color],
                                                 #           width=1, dash='dash'), marker=dict(size=4),
                                                 name=str(int(speed2_n[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                     int(round(100 * speed2_fraction_n[i].magnitude,
                                                               0))) + '% N<sub>rated</sub> - converted from design 2'))

            if t_sheet.range('C18').value == 'SIM' and t_sheet['B31'].value == 'Performance Calculada':
                Data_H_n.append(go.Scatter(x=flow_v_T[index], y=Head_T[index], opacity=0.55,
                                           marker=dict(color='gold', size=9, line=dict(width=1.5, color='black')),
                                           mode='markers', name='Test'))
                Data_eff_n.append(go.Scatter(x=flow_v_T[index], y=100 * eff_T[index], opacity=0.55,
                                             marker=dict(color='gold', size=9, line=dict(width=1.5, color='black')),
                                             mode='markers', name='Test'))

                if len(index_o) > 0:
                    Data_H_n.append(go.Scatter(x=flow_v_T[index_o], y=Head_T[index_o], opacity=0.55,
                                                 marker=dict(color='red', size=9, line=dict(width=1.5, color='black')),
                                                 mode='markers', name='Test - design gas'))
                    Data_eff_n.append(go.Scatter(x=flow_v_T[index_o], y=100 * eff_T[index_o], opacity=0.55,
                                                 marker=dict(color='red', size=9, line=dict(width=1.5, color='black')),
                                                 mode='markers', name='Test - design gas'))

            Data_H_n = tuple(Data_H_n)
            Data_eff_n = tuple(Data_eff_n)

            if pr:
                fig = go.Figure(
                    Data_H_n,
                    layout_title_text="Razão de Compressão x Vazão Volumétrica de Sucção"
                )
                fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')',
                                  yaxis_title='r<sub>c</sub> (' + var1_unit_out + ')', showlegend=True)
            else:
                fig = go.Figure(
                    Data_H_n,
                    layout_title_text="Head Politrópico x Vazão Volumétrica de Sucção"
                )
                fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')',
                                  yaxis_title='H<sub>p</sub> (' + var1_unit_out + ')', showlegend=True)

            figs_n.append(fig)

            fig = go.Figure(
                Data_eff_n,
                layout_title_text="Eficiência Politrópica x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')', yaxis_title='\u03b7<sub>p</sub> (%)',
                              showlegend=True)
            figs_n.append(fig)

            for i, fig in enumerate(figs_n):
                w = 1000
                h = 500
                fig.update_layout(width=w, height=h)
                try:
                    graf_n_sheet.pictures.add(fig, top=i * (h - 100))
                except:
                    pass

            ##########################################
            # New curves - converted to desired speeds

            if desired_speeds:

                Data_H_n_n = list()
                Data_eff_n_n = list()

                for i in range(N_speed_n_n):

                    i_color = i
                    if MW_n > MW_o:
                        i = N_speed_n_n - i - 1

                    Data_H_n_n.append(go.Scatter(x=Qs_n_n[:, i], y=H_n_n[:, i],
                                                 line=dict(color=color[i_color],
                                                           width=1, dash='dash'),  mode='lines',#marker=dict(size=4),
                                                 name=str(int(speed_n_n[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                     int(round(100 * speed_fraction_n_n[i].magnitude,
                                                               0))) + '% N<sub>rated</sub>' + '- converted'))
                    Data_eff_n_n.append(go.Scatter(x=Qs_n_n[:, i], y=Eff_n_n[:, i] * 100,
                                                   line=dict(color=color[i_color],
                                                             width=1, dash='dash'),  mode='lines',#marker=dict(size=4),
                                                   name=str(int(speed_n_n[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                       int(round(100 * speed_fraction_n_n[i].magnitude,
                                                                 0))) + '% N<sub>rated</sub>' + '- converted'))


                if v_sheet.range('E8').value == 'SIM' and val_data:
                    for i in range(N_speedv):

                        i_color = i
                        if MW_n > MW_o:
                            i = N_speedv - i - 1

                        Data_H_n_n.append(go.Scatter(x=Qs_v[:, i], y=H_v[:, i],
                                                    marker=dict(color=color[i_color],
                                                                 size=1.5,
                                                                 line=dict(
                                                                     color=color[i_color],
                                                                     width=2)),
                                                    name=str(
                                                         int(speed_v[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                         int(round(100 * speed_fraction_v[i].magnitude,
                                                                   0))) + '% N<sub>rated</sub>'+ '- vendor curve'))
                        Data_eff_n_n.append(go.Scatter(x=Qs_v[:, i], y=Eff_v[:, i] * 100,
                                                       marker=dict(color=color[i_color],
                                                                   size=1.5,
                                                                   line=dict(
                                                                       color=color[i_color],
                                                                       width=2)),
                                                       # marker=dict(size=4),
                                                       name=str(int(
                                                           speed_v[i].magnitude)) + ' ' + speed_unit_out + ' - ' + str(
                                                           int(round(100 * speed_fraction_v[i].magnitude,
                                                                     0))) + '% N<sub>rated</sub>'+ '- vendor curve'))



                if t_sheet.range('C18').value == 'SIM' and t_sheet['B31'].value == 'Performance Calculada':
                    Data_H_n_n.append(go.Scatter(x=flow_v_T[index], y=Head_T[index], opacity=0.55,
                                                 marker=dict(color='gold', size=9, line=dict(width=1.5, color='black')),
                                                 mode='markers', name='Test'))
                    Data_eff_n_n.append(go.Scatter(x=flow_v_T[index], y=100 * eff_T[index], opacity=0.55,
                                                   marker=dict(color='gold', size=9, line=dict(width=1.5, color='black')),
                                                   mode='markers', name='Test'))

                    if len(index_o) > 0:
                        Data_H_n_n.append(go.Scatter(x=flow_v_T[index_o], y=Head_T[index_o], opacity=0.55,
                                                     marker=dict(color='red', size=9,
                                                                 line=dict(width=1.5, color='black')),
                                                     mode='markers', name='Test - design gas'))
                        Data_eff_n_n.append(go.Scatter(x=flow_v_T[index_o], y=100 * eff_T[index_o], opacity=0.55,
                                                       marker=dict(color='red', size=9,
                                                                   line=dict(width=1.5, color='black')),
                                                       mode='markers', name='Test - design gas'))

                Data_H_n_n = tuple(Data_H_n_n)
                Data_eff_n_n = tuple(Data_eff_n_n)

                if pr:
                    fig = go.Figure(
                        Data_H_n_n,
                        layout_title_text="Razão de Compressão x Vazão Volumétrica de Sucção"
                    )
                    fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')',
                                      yaxis_title='r<sub>c</sub> (' + var1_unit_out + ')', showlegend=True)
                else:
                    fig = go.Figure(
                        Data_H_n_n,
                        layout_title_text="Head Politrópico x Vazão Volumétrica de Sucção"
                    )
                    fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')',
                                      yaxis_title='H<sub>p</sub> (' + var1_unit_out + ')', showlegend=True)

                figs_n_n.append(fig)

                fig = go.Figure(
                    Data_eff_n_n,
                    layout_title_text="Eficiência Politrópica x Vazão Volumétrica de Sucção"
                )
                fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')', yaxis_title='\u03b7<sub>p</sub> (%)',
                                  showlegend=True)
                figs_n_n.append(fig)

                # if simp_question == 'SIM' or MW_question == 'NÃO':
                #     fig = go.Figure(
                #         Data_err,
                #         layout_title_text="Erro da razão entre volume específico x Vazão Volumétrica de Sucção"
                #     )
                #     fig.update_layout(xaxis_title='Q<sub>s</sub> (' + flow_unit_out + ')',
                #                       yaxis_title='\u03B5<sub>\u03c5<sub>r</sub></sub> (%)', showlegend=True)
                #     figs_n_n.append(fig)

                for i, fig in enumerate(figs_n_n):
                    w = 1000
                    h = 500
                    fig.update_layout(width=w, height=h)
                    try:
                        graf_n_.pictures.add(fig, top=i * (h - 100)).pictures.add(fig, top=i * (h - 100))
                    except:
                        pass

            print('Gráficos Plotados')
            n_sheet['N8'].value = 'Gráficos Plotados'
            n_sheet['N5'].value = 'off'
            wb.save()
            n_sheet.api.Protect()

        if o_sheet["L13"].value != None:
            o_sheet.api.Unprotect()
            n_sheet.api.Unprotect()
            v_sheet.api.Unprotect()
            t_sheet.api.Unprotect()
            CF_sheet.api.Unprotect()

            o_sheet["I6"].value = '||'
            n_sheet["G8"].value = '||'
            t_sheet["D31"].value = '||'
            CF_sheet["O23"].value = '||'

            secs = o_sheet["L13"].value

            o_sheet.api.Protect()
            n_sheet.api.Protect()
            v_sheet.api.Protect()
            t_sheet.api.Protect()
            CF_sheet.api.Protect()

            try:
                sleep(secs)
            except TypeError:
                print('integer or float must be provided!')
            o_sheet.api.Unprotect()
            n_sheet.api.Unprotect()
            v_sheet.api.Unprotect()
            t_sheet.api.Unprotect()
            CF_sheet.api.Unprotect()
            o_sheet["L13"].value = None
            o_sheet["I6"].value = 'ON'
            n_sheet["G8"].value = 'ON'
            t_sheet["D31"].value = 'ON'
            CF_sheet["O23"].value = 'ON'
            sleep(1)
            o_sheet.api.Protect()
            n_sheet.api.Protect()
            v_sheet.api.Protect()
            t_sheet.api.Protect()
            CF_sheet.api.Protect()
        else:
            sleep(1)
        try:
            aux = open(FileName, 'r+')
            Open = False
        except:
            Open = True
