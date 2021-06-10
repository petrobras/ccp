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
print("Hello World!")
FileName=os.path.basename(__file__)[:-3]

if __name__== '__main__':

    xw.PRO = True
    
    wb = Book(FileName)
    
    o_sheet = wb.sheets['Performance - Original']
    a_sheet = wb.sheets['auxiliar']
    n_sheet = wb.sheets['Performance - Nova']
    t_sheet = wb.sheets['Teste']
    CF_sheet=wb.sheets['Vazão - Cálculo']
    comp_sheet = wb.sheets['Curvas - Original x Nova']
    graf_ = wb.sheets['Curvas - Originais']
    graf_n_sheet = wb.sheets['Curvas - Novas']
    graf_n_ = wb.sheets['Curvas - Nova(Rotacao Original)']
    
    
    
    simp_question = o_sheet['M17'].value
    Open_file = True
    
    while Open_file:
        
        if o_sheet['I6'].value == "OFF":
            Open_file = False 
        
        o_sheet['K16'].value = None
        
    
        if o_sheet['K12'].value == 'on':
            o_sheet.api.Unprotect()
            print('Armazenando dados das curvas de projeto')
            o_sheet['K15'].value = 'Carregando Dados...'
        
            #suction data - Original
            Ps_o = Q_(o_sheet['F5'].value,o_sheet['G5'].value).to('Pa')
            Ts_o = Q_(o_sheet['F6'].value, o_sheet['G6'].value).to('kelvin')
            
            MW_question = o_sheet['E8'].value
            simp_question = o_sheet['M17'].value
            excel_question = o_sheet['K13'].value
            
            if MW_question == 'NÃO':
                MW_o = Q_(o_sheet['F2'].value,o_sheet['G2'].value).to('kg/mol')
                ks_o= Q_(o_sheet['F3'].value,'dimensionless')
                Zs_o = Q_(o_sheet['F4'].value,'dimensionless')
                Zm_o = Q_((Zs_o+0.01)/2,'dimensionless')
                gas_constant = Q_(8.314506886527345,'joule/(kelvin*mol)')
            else:
                for i in range(25):
                    if o_sheet.cells(12+i,3).value == None: 
                        N=i
                        break
                    elif i==24:
                        N=25
                Gases_o = o_sheet.range(o_sheet.cells(12,3),o_sheet.cells(12+N-1,3)).value
                mol_frac_o = o_sheet.range(o_sheet.cells(12,5),o_sheet.cells(12+N-1,5)).value
                try:
                    fluid_o = {Gases_o[i]: mol_frac_o[i]/100 for i in range(len(Gases_o))}
                except TypeError:
                    o_sheet['K15'].value = 'Erro! %molar!'
                    o_sheet['K16'].value = 'Reinicie o Script!'
                try:
                    suc_o = ccp.State.define(p = Ps_o, T = Ts_o,fluid = fluid_o)
                except ValueError:
                    o_sheet['K15'].value = 'Composição do Gás!'
                    o_sheet['K16'].value = 'Reinicie o Script!'
                MW_o = suc_o.molar_mass().to('kg/kmol')
                o_sheet.range('E37').value = MW_o.magnitude
                ks_o = suc_o.cp()/suc_o.cv()#############################################
                Zs_o = suc_o.z()#########################################################
                Zm_o = Q_((Zs_o.magnitude+0.01)/2,'dimensionless')#######################
                b = Q_(o_sheet.range('O3').value,o_sheet.range('P3').value)
                D = Q_(o_sheet.range('O2').value,o_sheet.range('P2').value)
                o_sheet.range('F2').value = MW_o.magnitude
                o_sheet.range('G2').value = 'kg/kmol'
                o_sheet.range('F3').value = ks_o.magnitude
                o_sheet.range('F4').value = Zs_o.magnitude
                gas_constant = suc_o.gas_constant()
                   
         
            speed_rated = Q_(o_sheet['M5'].value,o_sheet['M6'].value).to('rpm')
            
            
            if excel_question == "excel":
                N_speed = int(o_sheet['D40'].value)
                speed_o = Q_(np.zeros(N_speed),'rpm')
                #Store each variable (flow, head and efficiency) in 2-D arrays - [variable,speed]
                f = 0
                for i in range(N_speed):
                    Qs = list()
                    H = list()
                    eff = list()
                    stop_loop = 0
                    while (o_sheet.cells(42+f,3).value) == None and stop_loop<20:
                        f += 1 
                        stop_loop +=1
                    #stop loop whether there are no more curves to read from .xlsm file
                    if stop_loop ==20:
                        N_speed = i
                        break
                    speed_o[i] = Q_(o_sheet.cells(42+f,3).value,o_sheet.cells(42+f,4).value)
                    f = f+2
                    flow_unit = o_sheet.cells(42+f,3).value
                    head_unit = o_sheet.cells(42+f,4).value
                    f+=1
                    while (o_sheet.cells(42+f,3).value) != None:
                        Qs.append(o_sheet.cells(42+f,3).value) 
                        H.append(o_sheet.cells(42+f,4).value) 
                        eff.append(o_sheet.cells(42+f,5).value/100) #dimensionless
                        f +=1 
                    #Sort each variable (Head and efficiency) in flow ascending order
                    ind_Q = np.argsort(Qs)
                
                    Qs = np.array(Qs)
                    H = np.array(H)
                    eff = np.array(eff)
                    
                    Qs = Qs[ind_Q]
                    H = H[ind_Q]            
                    eff= eff[ind_Q]
                    #set the first array as reference for the number of points in one speed
                    #and resize other speeds "array"
                    if i == 0:
                        Qs_o = Q_(np.zeros((len(Qs),N_speed)),flow_unit)
                        H_o = Q_(np.zeros((len(Qs),N_speed)),head_unit)
                        eff_o = Q_(np.zeros((len(Qs),N_speed)),'dimensionless')
                        Qs_o[:,i] = Q_(Qs,flow_unit)
                        H_o[:,i]  =  Q_(H,head_unit)                 
                        eff_o[:,i] =  Q_(eff,'dimensionless') 
                    elif (i!=0) & (len(Qs)!= len(Qs_o[:,0])):        
                        Qs_o[:,i] = Q_(np.linspace(Qs[0],Qs[-1],len(Qs_o[:,0])),flow_unit)
                        s = UnivariateSpline(Qs,H)
                        H_o[:,i] = Q_(s(Qs_o[:,i]),head_unit)
                        t = UnivariateSpline(np.array(Qs),eff)
                        eff_o[:,i] = Q_(t(Qs_o[:,i]),'dimensionless')
                    else:
                        Qs_o[:,i] = Q_(Qs,flow_unit)
                        H_o[:,i]  =  Q_(H,head_unit)            
                        eff_o[:,i] =  Q_(eff,'dimensionless')  
                        
                #Sort each parameter (Head and efficiency) in speed descending order
                if N_speed > 1:
                    speed_o = speed_o.to('rpm')
                    ind_Speed = np.argsort(speed_o.magnitude)[::-1]
                    speed_o = speed_o[ind_Speed]
                    Qs_o = Qs_o[:,ind_Speed]
                    H_o  = H_o[:,ind_Speed]            
                        
                #Calculation of polytropic coefficient
                N_lines = len(Qs_o[:,0]) 
                if stop_loop ==20:
                    Qs_o = Q_(np.delete(Qs_o.magnitude,np.s_[N_speed:],1),flow_unit)
                    H_o  = Q_(np.delete(H_o.magnitude,np.s_[N_speed:],1),head_unit)            
                    eff_o= Q_(np.delete(eff_o.magnitude,np.s_[N_speed:],1),'dimensionless') 
                
            else:
                #store performance data from .csv file and sort to speed descending order
                #and flow ascending order
                try:
                    data_dir = Path(a_sheet["B8"].value)
                except:
                    data_dir=Path.cwd()
                curve_name = str(o_sheet["L12"].value)
                flow_unit =  str(a_sheet["C2"].value)
                head_unit =  str(a_sheet["C3"].value)
                speed_unit=  a_sheet["C4"].value
                N_lines =  int(a_sheet["C5"].value)
                print('Criando impelidor com pontos')
                try:
                    imp = ccp.Impeller.load_from_engauge_csv(suc = suc_o, curve_name=curve_name, number_of_points=N_lines, curve_path = data_dir, b=b, D=D, flow_units=flow_unit,head_units=head_unit,speed_units = speed_unit)
                except FileNotFoundError:
                    o_sheet['K15'].value = "Curva não encontrada!"
                    o_sheet['K16'].value = 'Reinicie o Script!'
                except:
                    o_sheet['K15'].value = 'Corrigir unidades!'
                    o_sheet['K16'].value = 'Reinicie o Script!'
                #except
                #store impeller points in 2-D arrays for each variable (H,Q,eff)
                N_speed = len(imp.curves)
                speed_o = Q_(np.zeros(N_speed),'rpm') 
                H_o = Q_(np.zeros((N_lines,N_speed)),'kJ/kg')
                Qs_o = Q_(np.zeros((N_lines,N_speed)),'m**3/h')
                eff_o = Q_(np.zeros((N_lines,N_speed)),'dimensionless')
            
                
                for j in range(N_speed):
                    if N_speed > 1:
                        if imp.curves[0][0].speed > imp.curves[1][0].speed:
                            l = -1-j
                        else:
                            l = j
                    else:
                        l = j
                    for i in range(N_lines):
                        speed_o[j] = imp.curves[l][0].speed.to('rpm')
                        H_o [i,j] = imp.curves[l][i].head.to('kJ/kg')
                        Qs_o [i,j]= imp.curves[l][i].flow_v.to('m**3/h')
                        eff_o [i,j] = imp.curves[l][i].eff
                    
            
            if simp_question == 'SIM':
                np_o = Q_(eff_o.magnitude*ks_o.magnitude/(ks_o.magnitude*eff_o.magnitude+ np.ones([N_lines,N_speed])*(1-ks_o.magnitude)),'dimensionless')
                vr_o = (H_o*(np_o-1)/np_o*MW_o/(Zm_o*gas_constant*Ts_o)+1)**(1/(np_o-1))
                vr_o = vr_o.to('dimensionless')
            elif excel_question == "excel":
                Point_o = []
                # create an impeller that will hold and convert curves.
                print('armazenando pontos')
                t0=time.time()

                for j in range(N_speed):
                    suc = suc_o
                    speed = speed_o[j]                    
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
                        for flow, head, eff in zip(Qs_o[:,j], H_o[:,j], eff_o[:,j])
                    ]
    
                    with multiprocessing.Pool() as pool:
                        Point_o += pool.map(ccp.impeller.create_points_flow_v, args_list)
                tf=time.time()
                dt = tf-t0
                print('Tempo armazenando pontos: '+str(int(dt/60))+' minutos e '+ str(int(dt%60))+ ' segundos')
                print('Criando impelidor')
                t0=time.time()
                imp = ccp.Impeller(Point_o)
                tf=time.time()
                dt = tf-t0
                print('Tempo criando impelidor: '+str(int(dt/60))+' minutos e '+ str(int(dt%60))+ ' segundos')
                
            print('Dados carregados')
            o_sheet['K15'].value = 'Dados Carregados'
            o_sheet['K12'].value = 'off'
            o_sheet.api.Protect()
            
        
        #New condition
        if n_sheet['I5'].value == 'on' and o_sheet['K15'].value=='Dados Carregados':
            n_sheet.api.Unprotect()
            speed_unit_out = n_sheet['S6'].value
            flow_unit_out = n_sheet['S4'].value
            head_unit_out = n_sheet['S5'].value
            
            speed_o = speed_o.to(speed_unit_out)
            H_o = H_o.to(head_unit_out)
            Qs_o = Qs_o.to(flow_unit_out)
    
            print('Armazenando dados da nova condição operacional')
            n_sheet['I8'].value = 'Carregando Dados...'
            simp_question = o_sheet['M17'].value
            
            # 1 section suction data - New Condition
            Ps_n = Q_(n_sheet['F5'].value,n_sheet['G5'].value).to('Pa')+Q_(1,'atm').to('Pa')
            Ts_n = Q_(n_sheet['F6'].value, n_sheet['G6'].value).to('kelvin')
            
            MW_question = n_sheet['E8'].value
            
            if MW_question == 'NÃO':
                MW_n = Q_(n_sheet['F2'].value,n_sheet['G2'].value)
                ks_n= Q_(n_sheet['F3'].value,'dimensionless')
                Zs_n = Q_(n_sheet['F4'].value,'dimensionless')
                Zm_n = Q_((Zs_n+0.01)/2,'dimensionless')
                gas_constant = Q_(8.314506886527345,'joule/(kelvin*mol)')
            else:
                for i in range(25):
                    if n_sheet.cells(11+i,3).value == None: 
                        N=i
                        break
                    elif i==24:
                        N=25
                Gases_n = n_sheet.range(n_sheet.cells(11,3),n_sheet.cells(11+N-1,3)).value
                mol_frac_n = n_sheet.range(n_sheet.cells(11,5),n_sheet.cells(11+N-1,5)).value
                try:
                    fluid_n = {Gases_n[i]: mol_frac_n[i]/100 for i in range(len(Gases_n))}
                except TypeError:
                    n_sheet['I8'].value = 'Erro! %molar!'
                    n_sheet['I9'].value = 'Reinicie o Script!'
                try:
                    suc_n = ccp.State.define(p = Ps_n, T = Ts_n,fluid = fluid_n)
                except ValueError:
                    n_sheet['I8'].value = 'Composição do Gás!'
                    n_sheet['I9'].value = 'Reinicie o Script!'
                MW_n = suc_n.molar_mass().to('kg/kmol')
                n_sheet.range('E36').value = MW_n.magnitude
                ks_n= suc_n.cp()/suc_n.cv()##############################################
                Zs_n = suc_n.z()#########################################################
                Zm_n = Q_((Zs_n.magnitude+0.01)/2,'dimensionless')#######################
                n_sheet.range('F2').value = MW_n.magnitude
                n_sheet.range('G2').value = 'kg/kmol'
                n_sheet.range('F3').value = ks_n.magnitude
                n_sheet.range('F4').value = Zs_n.magnitude
                gas_constant = suc_n.gas_constant()
                
              
                
        
            print('Convertendo as curvas de performance.')
            n_sheet['I8'].value = 'Convertendo Curvas...'
            #Convert the curves
            if simp_question == 'SIM' :
                try:
                    vr_o
                except NameError:
                    np_o = Q_(eff_o.magnitude*ks_o.magnitude/(ks_o.magnitude*eff_o.magnitude+ np.ones([N_lines,N_speed])*(1-ks_o.magnitude)),'dimensionless')
                    vr_o = (H_o*(np_o-1)/np_o*MW_o/(Zm_o*gas_constant*Ts_o)+1)**(1/(np_o-1))
                    vr_o = vr_o.to('dimensionless')
                
                #Similarity condition
                eff_n = eff_o
                vr_n = vr_o
            
                np_n = Q_(np.zeros((N_lines,N_speed)),'dimensionless') ##################
                H_n = Q_(np.zeros((N_lines,N_speed)),head_unit_out)######################
                speed_n_matrix = Q_(np.zeros((N_lines,N_speed)),speed_unit_out)##########
                Qs_n = Q_(np.zeros((N_lines,N_speed)),flow_unit_out)#####################
            
                np_n = eff_n*ks_n/(ks_n*eff_n+ np.ones([N_lines,N_speed])*(1-ks_n))
                H_n = np_n/(np_n-1)*Zm_n*gas_constant/MW_n*Ts_n*((vr_n)**(np_n-1)-1)
            
                for i in range(N_speed):
                    speed_n_matrix[:,i] = speed_o[i]*(H_n[:,i]/H_o[:,i])**(1/2)
                    Qs_n[:,i] = Qs_o[:,i]*(speed_n_matrix[:,i]/speed_o[i])
            
                #New speed values
                speed_n = Q_(np.mean(speed_n_matrix.magnitude,axis=0),speed_n_matrix.units)
            
            else:
                # convert curves with ccp package method
                t0=time.time()
                try:
                    imp
                except NameError:
                    n_sheet['I8'].value='Reinicie o Script!'
                
                imp_conv = ccp.Impeller.convert_from(imp, suc=suc_n)
                tf=time.time()
                dt = tf-t0
                print('Tempo convertendo pontos: '+str(int(dt/60))+' minutos e '+ str(int(dt%60))+ ' segundos')
                
                speed_n = Q_(np.zeros(N_speed),speed_unit_out) 
                H_n = Q_(np.zeros((N_lines,N_speed)),head_unit_out)
                Qs_n = Q_(np.zeros((N_lines,N_speed)),flow_unit_out)
                eff_n = Q_(np.zeros((N_lines,N_speed)),'dimensionless')
            
                
                for j in range(N_speed):
                    if N_speed > 1:
                        if speed_o[0]>speed_o[1]:
                            l = -1-j
                        else:
                            l = j
                    else:
                        l = j
                    for i in range(N_lines):
                        speed_n[j] = imp_conv.curves[l][0].speed.to(speed_unit_out)
                        H_n [i,j] = imp_conv.curves[l][i].head.to(head_unit_out)
                        Qs_n [i,j]= imp_conv.curves[l][i].flow_v.to(flow_unit_out)
                        eff_n [i,j] = imp_conv.curves[l][i].eff
            
            
            
            
            #Calculations for the new gas condition - original speed (design/shop test)
            
            H_n_o = Q_(np.zeros((N_lines,N_speed)),head_unit_out)
            Qs_n_o = Q_(np.zeros((N_lines,N_speed)),flow_unit_out)
            eff_n_o = Q_(np.zeros((N_lines,N_speed)),'dimensionless')
            error = np.ones((N_speed))*100
            vr_n_o = Q_(np.zeros((N_lines,N_speed)),'dimensionless')
            
            #find the nearest speed to each original one
            for i in range(N_speed):
                counter = -1
                for k in range(N_speed):
                    ref = abs(speed_n[k].magnitude-speed_o[i].magnitude)/speed_o[i].magnitude
                    if ref < error[i]:
                        error[i] = ref
                        counter += 1
                H_n_o[:,i] = H_n[:,counter]*(speed_o[i]/speed_n[counter])**2
                Qs_n_o[:,i] = Qs_n[:,counter]*(speed_o[i]/speed_n[counter])
                eff_n_o[:,i] = eff_n[:,counter]
            
                if simp_question == 'SIM' :
                    #considers that efficiency are the same for those "similar" points and recalculate
                    #volume ratio to evaluate, i.e, considers deviation only due to volume ratio
                    vr_n_o[:,i] = vr_n[:,counter]
                    vr_n_o_ref = (H_n_o*(np_n-1)/np_n*MW_n/(Zm_n*gas_constant*Ts_n)+1)**(1/(np_n-1))
                    vr_n_o_ref = vr_n_o_ref.to('dimensionless')
            
                    erro_vr = abs((vr_n_o_ref-vr_n_o)/vr_n_o_ref)
                    erro_vr_mean = np.mean(erro_vr,axis = 0)    
            
            n_sheet['C41:E1416'].value=[[None]*(3)]*(1415-41+1)
            n_sheet['D39'].value= None
            print('Curvas convertidas')
            n_sheet['I8'].value = 'Curvas Convertidas'
            n_sheet['I5'].value = 'off'
            n_sheet.api.Protect()
        
        
        
        ###################################
        ##calculate flow
        CalcFlow_tag = CF_sheet['N3'].value
        
        if CF_sheet['N3'].value == 'on' and n_sheet['E8'].value!='NÃO':
            
            CF_sheet.api.Unprotect()
            print('Calculando vazao massica - ISO 5167.')  
            CF_sheet['N7'].value = 'Calculando Vazão...'
            
            for i in range(25):
                if n_sheet.cells(11+i,3).value == None: 
                    N=i
                    break
                elif i==24:
                    N=25
            Gases_n = n_sheet.range(n_sheet.cells(11,3),n_sheet.cells(11+N-1,3)).value
            mol_frac_n = n_sheet.range(n_sheet.cells(11,5),n_sheet.cells(11+N-1,5)).value
            try:
                fluid_n = {Gases_n[i]: mol_frac_n[i]/100 for i in range(len(Gases_n))}
            except TypeError:
                CF_sheet['N7'].value = 'Erro! %molar!'
                CF_sheet['N8'].value = 'Reinicie o Script!'

            global qm
                
            from scipy.optimize import newton
            
            Units=CF_sheet['C4:K4'].value
                
            i=4
            data=np.array(CF_sheet[i,2:8].value)

            while len(data[data==None])==0:
                                
                    
                D=Q_(float(data[0]),Units[0])
                d=Q_(float(data[1]),Units[1])
                P1=Q_(float(data[2]),Units[2])+Q_(1,'atm').to(Units[2])
                T1=Q_(float(data[3]),Units[3])
                dP=Q_(float(data[4]),Units[4])
                tappings=data[5]
                    
                    
                                    
                P2=P1-dP
                try:
                    State_FO=ccp.State.define(fluid=fluid_n , p=P1 , T=T1)
                except ValueError:
                    CF_sheet['N7'].value = 'Composição do Gás!'   
                    CF_sheet['N8'].value = 'Reinicie o Script!'
                    
                beta=d/D
                mu=State_FO.viscosity()
                rho=State_FO.rho()
                k=State_FO.kv()
                    
                e=1-(0.351+0.256*(beta**4)+0.93*(beta**8))*(1-(P2/P1)**(1/k))
                    
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
                        
                    Re=Q_(Re,'dimensionless')
                    # calc C
                    C = (
                        0.5961 + 0.0261 * beta ** 2 - 0.216 * beta ** 8
                        + 0.000521 * (1e6 * beta / Re) ** 0.7
                        + (0.0188 + 0.0063
                        * (19000 * beta / Re)**0.8) * beta**3.5 * (1e6 / Re)**0.3
                        + (0.043 + 0.080 * np.e**(-10 * L1) - 0.123 * np.e**(-7 * L1))
                        * (1 - 0.11 * (19000 * beta / Re)**0.8) * (beta**4 / (1 - beta**4))
                        - 0.031 * (M2 - 0.8 * M2 ** 1.1) * beta**1.3
                    )
                    
                    if D < Q_(71.12, 'mm'):
                        C += 0.011 * (0.75 - beta) * (2.8 - D / Q_(25.4,'mm'))
                            
                    qm = C / (np.sqrt(1 - beta**4)) * e * (np.pi / 4) * d**2 * np.sqrt(2 * dP * rho) 
                                
                    Re_qm=(4*qm/(mu*np.pi*D)).to('dimensionless').magnitude
                        
                    return abs(Re_qm-Re.magnitude)
                    
                    
                newton(update_Re,1e8,tol=1e-5)
                    
                Re=D/mu*qm/(np.pi*D**2/4)
                   
                    
                CF_sheet[i,8].value=qm.to(Units[6]).magnitude
                
                disch_n = ccp.State.define(p = Q_(1,'atm'), T = Q_(0,'degC'),fluid = fluid_n)
                flow_normal = disch_n.z()*disch_n.gas_constant()*Q_(0,'degC').to('kelvin')*qm/(disch_n.molar_mass()*Q_(1,'atm'))
                CF_sheet[i,9].value = flow_normal.to(Units[7]).magnitude
                
                flow_rate = qm/ccp.State.define(p=P1,T=T1,fluid=fluid_n).rho()
                CF_sheet[i,10].value = flow_rate.to(Units[8]).magnitude
                i += 1
                data=np.array(CF_sheet[i,2:8].value)
                    
                        
            print('Vazão calculada')
            
            CF_sheet['N7'].value = 'Vazão Calculada'
            CF_sheet['N3'].value = 'off'
            CF_sheet.api.Protect()
                
        
        
        
        ##############
        #Tested points 
        
        if t_sheet['B27'].value == 'on' and n_sheet['E8'].value!='NÃO':
            
            t_sheet.api.Unprotect()
            print('Calculando Performance...')  
            t_sheet['B31'].value = 'Calculando Performance...'
        
            
            for i in range(25):
                if n_sheet.cells(11+i,3).value == None:
                    Ng=i
                    break
                elif i==24:
                    Ng=25
            Gases_n = n_sheet.range(n_sheet.cells(11,3),n_sheet.cells(11+Ng-1,3)).value
            mol_frac_n = n_sheet.range(n_sheet.cells(11,5),n_sheet.cells(11+Ng-1,5)).value
            try:
                fluid_n = {Gases_n[i]: mol_frac_n[i]/100 for i in range(len(Gases_n))}
            except TypeError:
                t_sheet['B31'].value = 'Erro! %molar!'
                t_sheet['B32'].value = 'Reinicie o Script!'
            b = Q_(o_sheet.range('O3').value,o_sheet.range('P3').value)
            D = Q_(o_sheet.range('O2').value,o_sheet.range('P2').value)
            
            for i in range(40):
                if t_sheet.cells(5,5+i).value == None:
                    NT=i
                    break
            
            if NT !=0:
                t_sheet['E20:Q20'].value=[None]*14
                t_sheet['E21:Q21'].value=[None]*14
                t_sheet['E22:Q22'].value=[None]*14
                P_test = []
            
                for i in range(NT):
                    if CF_sheet['N7'].value == 'Vazão Calculada':
                        t_sheet.cells(20,5+i).value=Q_(CF_sheet.cells(5+i,9).value,CF_sheet.cells(4,9).value).to(t_sheet.cells(20,4).value).magnitude
                    Ps_T = Q_(t_sheet.cells(5,5+i).value,t_sheet.cells(5,4).value)+Q_(1,'atm').to('Pa')
                    Ts_T = Q_(t_sheet.cells(6,5+i).value,t_sheet.cells(6,4).value)
                    Pd_T = Q_(t_sheet.cells(7,5+i).value,t_sheet.cells(7,4).value)+Q_(1,'atm').to('Pa')
                    Td_T = Q_(t_sheet.cells(8,5+i).value,t_sheet.cells(8,4).value)
                    try:
                        disch_n = ccp.State.define(p = Q_(1,'atm'), T = Q_(0,'degC'),fluid = fluid_n)
                    except ValueError:
                        t_sheet['B31'].value = 'Composição do Gás!'
                        t_sheet['B32'].value = 'Reinicie o Script!'
                    if t_sheet.cells(20,5+i).value != None:
                        flow_m = Q_(t_sheet.cells(20,5+i).value,t_sheet.cells(20,4).value)
                        flow_normal = disch_n.z()*disch_n.gas_constant()*Q_(0,'degC').to('kelvin')*flow_m/(disch_n.molar_mass()*Q_(1,'atm'))
                        t_sheet.cells(22,5+i).value = flow_normal.to(t_sheet.cells(22,4).value).magnitude
                    elif t_sheet.cells(9,5+i).value == None:
                        raise ValueError('Mass flow or Normal flow rate must be provided!')
                    else:
                        flow_m = Q_(1,'atm')*Q_(t_sheet.cells(9,5+i).value,t_sheet.cells(9,4).value)*disch_n.molar_mass()/(disch_n.z()*disch_n.gas_constant()*Q_(0,'degC').to('kelvin'))
                        t_sheet.cells(20,5+i).value = flow_m.to(t_sheet.cells(20,4).value).magnitude      
                                   
                    speed_T = Q_(t_sheet.cells(12,5+i).value,t_sheet.cells(12,4).value)
                    suc_T = ccp.State.define(p = Ps_T, T = Ts_T,fluid = fluid_n)
                    disch_T = ccp.State.define(p = Pd_T, T = Td_T,fluid = fluid_n)
                    
                    P_test.append(ccp.Point(speed=speed_T,flow_m=flow_m,suc=suc_T,disch=disch_T,b =b, D=D))
            
                for i in range(NT):
                    t_sheet.cells(14,5+i).value = P_test[i].head.to(t_sheet.cells(14,4).value).magnitude
                    t_sheet.cells(15,5+i).value = P_test[i].eff.magnitude*100
                    t_sheet.cells(16,5+i).value = P_test[i].power.to(t_sheet.cells(16,4).value).magnitude
                    t_sheet.cells(21,5+i).value = P_test[i].flow_v.to(t_sheet.cells(21,4).value).magnitude
                
            
            print('Performance calculada')
            
            t_sheet['B31'].value = 'Performance Calculada'
            t_sheet['B27'].value = 'off'
            t_sheet.api.Protect()
        
         
        #############################################################
        #Export converted curves data (flow,head,efficiency) to excel
        
        if n_sheet['N5'].value =='on' and o_sheet['K15'].value == 'Dados Carregados' and n_sheet['I8'].value == 'Curvas Convertidas': 
            
            n_sheet.api.Unprotect()
            
            flow_unit_out = n_sheet['S4'].value
            head_unit_out = n_sheet['S5'].value
            speed_unit_out = n_sheet['S6'].value
            
            #store variables (Head,speed,flow,eff,power) in numpy arrays
            if t_sheet.range('C18').value == 'SIM' and t_sheet['B31'].value =='Performance Calculada':
                n_sheet['N8'].value = 'Carregando dados do teste...'
                flow_v_T = Q_(np.zeros(NT),flow_unit_out)
                Head_T = Q_(np.zeros(NT),head_unit_out)
                eff_T = np.zeros(NT)
                speed_T = Q_(np.zeros(NT),speed_unit_out)
                for i in range(NT):
                    Head_T[i] = P_test[i].head
                    speed_T[i] = P_test[i].speed
                    flow_v_T[i] = P_test[i].flow_v
                    eff_T[i] = P_test[i].eff.magnitude
            
            print('Plotando os gráficos.')  
            n_sheet['N8'].value = 'Plotando Gráficos...'
            count = 41
            n_sheet['D39'].value = N_speed 
            
            
            for j in range(N_speed):
                #if j == 0:
                    #count +=1
                count +=1
                n_sheet.cells(count,3).value = round(speed_o[j].to(speed_unit_out).magnitude,1)
                n_sheet.cells(count,4).value = speed_unit_out
                count += 1
                n_sheet.cells(count,3).value = 'Vazão'
                n_sheet.cells(count,4).value = 'Head'
                n_sheet.cells(count,5).value = 'Eficiência'
                count += 1
                n_sheet.cells(count,3).value = flow_unit_out
                n_sheet.cells(count,4).value = head_unit_out
                n_sheet.cells(count,5).value = '%'    
                for i in range(N_lines):
                    if i == 0:
                        count +=1
                    n_sheet.cells(count,3).value = round(Qs_n_o[i,j].to(flow_unit_out).magnitude,1) 
                    n_sheet.cells(count,4).value = round(H_n_o[i,j].to(head_unit_out).magnitude,1) 
                    n_sheet.cells(count,5).value = round(eff_n_o[i,j].magnitude*100,1)
                    count += 1
                    if i == (N_lines-1):
                        count +=1
                    
                            
                
            ################################
            ################################    
            #Plot curves and export to excel
            
            figs_o = []
            figs_n = []
            figs_n_o = []
            figs_comp = []
            
            speed_o = speed_o.to(speed_unit_out)
            Qs_n_o = Qs_n_o.to(flow_unit_out)
            H_n_o = H_n_o.to(head_unit_out)
            
            speed_n = speed_n.to(speed_unit_out)
            Qs_n = Qs_n.to(flow_unit_out)
            H_n = H_n.to(head_unit_out)
            
            Qs_o = Qs_o.to(flow_unit_out)
            H_o = H_o.to(head_unit_out)
            
            #################################################################
            #Original curves (design/shop test) x New conditions (field test)
           
            speed_fraction_o = speed_o/speed_rated
            speed_fraction_o = speed_fraction_o.to('dimensionless')
            
            Data_compH =   list()
            Data_compEff =   list()
            
            
            # colors
            palette = cycle(px.colors.qualitative.Bold)
            palette = cycle(['darkslateblue', 'mediumblue', 'dodgerblue', 'orangered'])
            color = list()
            for i in range(N_speed):
                color.append(next(palette))
            
            
            for i in range(N_speed):
                Data_compH.append(go.Scatter(x = Qs_n_o[:,i] , y = H_n_o[:,i], 
                                                 line = dict(color = color[i], 
                                                               width = 1, dash ='dash'), marker = dict(size=4),
                                            name = str(int(speed_o[i].magnitude))+' '+speed_unit_out+' - '+ str(int(round(100*speed_fraction_o[i].magnitude,0)))+ '% N<sub>rated</sub>' +'- new'))
                Data_compH.append(go.Scatter(x = Qs_o[:,i] , y = H_o[:,i], 
                                            marker = dict (color = color[i],
                                            size = 1.5,
                                            line = dict(
                                            color = color[i],
                                            width = 2)),
                                            name = str(int(speed_o[i].magnitude))+' '+speed_unit_out+' - design'))
                Data_compEff.append(go.Scatter(x = Qs_n_o[:,i] , y = 100*eff_n_o[:,i], 
                                                 line = dict(color = color[i], 
                                                               width = 1, dash ='dash'), marker = dict(size=4),
                                            name = str(int(speed_o[i].magnitude))+' '+speed_unit_out+' - '+ str(int(round(100*speed_fraction_o[i].magnitude,0)))+ '% N<sub>rated</sub>' +'- new'))
                Data_compEff.append(go.Scatter(x = Qs_o[:,i] , y = 100*eff_o[:,i], 
                                            marker = dict (color = color[i],
                                            size = 1.5,
                                            line = dict(
                                            color = color[i],
                                            width = 2)),
                                            name = str(int(speed_o[i].magnitude))+' '+speed_unit_out+' - design'))
                
            
            if t_sheet.range('C18').value == 'SIM' and t_sheet['B31'].value =='Performance Calculada':
                Data_compH.append(go.Scatter(x = flow_v_T , y = Head_T, opacity=0.55,
                                                marker = dict(color ='gold', size = 9, line = dict(width =1.5,color ='black')),
                                                           mode='markers', name = 'Test'))
                Data_compEff.append(go.Scatter(x = flow_v_T , y = 100*eff_T, opacity =0.55,
                                                marker = dict(color ='gold', size = 9, line = dict(width =1.5,color ='black')),
                                                           mode='markers', name = 'Test'))
                
                
            Data_compH = tuple(Data_compH)
            Data_compEff = tuple(Data_compEff)
            
            fig = go.Figure(
                Data_compH,
                layout_title_text="Head Politrópico x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> ('+flow_unit_out+')',yaxis_title='H<sub>p</sub> ('+ head_unit_out+')',showlegend = True)
            figs_comp.append(fig)
            
            fig = go.Figure(
                Data_compEff,
                layout_title_text="Eficiência Politrópica x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title= 'Q<sub>s</sub> ('+flow_unit_out+')',yaxis_title='\u03b7<sub>p</sub> (%)',showlegend = True)
            figs_comp.append(fig)
            
            
            for i, fig in enumerate(figs_comp):
                w=1000
                h=500
                fig.update_layout(width=w,height=h)
                try:
                    comp_sheet.pictures.add(fig,top=i*(h-100))
                except:
                    pass
            
            ###################################
            #Original curves (design/shop test)
            
            Data_H =   list()
            Data_eff = list()
            
            for i in range(N_speed):
                Data_H.append(go.Scatter(x = Qs_o[:,i] , y = H_o[:,i], 
                                            marker = dict (color = color[i],
                                            size = 1.5,
                                            line = dict(
                                            color = color[i],
                                            width = 2)),
                                         name = str(int(speed_o[i].magnitude))+' '+speed_unit_out+' - '+ str(int(round(100*speed_fraction_o[i].magnitude,0)))+ '% N<sub>rated</sub>'))
                Data_eff.append(go.Scatter(x = Qs_o[:,i] , y = eff_o[:,i]*100, 
                                            marker = dict (color = color[i],
                                            size = 1.5,
                                            line = dict(
                                            color = color[i],
                                            width = 2)),
                                           name = str(int(speed_o[i].magnitude))+' '+speed_unit_out+' - '+ str(int(round(100*speed_fraction_o[i].magnitude,0)))+ '% N<sub>rated</sub>'))
                
            Data_H = tuple(Data_H)
            Data_eff = tuple(Data_eff)
            
            fig = go.Figure(
                Data_H,
                layout_title_text= "Head Politrópico x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> ('+flow_unit_out+')',yaxis_title='H<sub>p</sub> ('+ head_unit_out+')',showlegend = True)
            figs_o.append(fig)
            
            
            fig = go.Figure(
                Data_eff,
                layout_title_text="Eficiência Politrópica x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> ('+flow_unit_out+')',yaxis_title='\u03b7<sub>p</sub> (%)',showlegend = True)
            figs_o.append(fig)
            
            for i, fig in enumerate(figs_o):
                w=1000
                h=500
                fig.update_layout(width=w,height=h)
                try:
                    graf_.pictures.add(fig,top=i*(h-100))
                except:
                    pass
                
                
                
            ####################################################################  
            #New curves - performance curves before converted to original speeds
            speed_fraction_n = speed_n/speed_rated
            speed_fraction_n = speed_fraction_n.to('dimensionless')
            
            Data_H_n =   list()
            Data_eff_n = list()
            
            for i in range(N_speed):
                Data_H_n.append(go.Scatter(x = Qs_n[:,i] , y = H_n[:,i], 
                                           line = dict(color = color[i], 
                                           width = 1, dash ='dash'), marker = dict(size=4), 
                                           name = str(int(speed_n[i].magnitude))+' '+speed_unit_out+' - '+ str(int(round(100*speed_fraction_n[i].magnitude,0)))+ '% N<sub>rated</sub>'))
                Data_eff_n.append(go.Scatter(x = Qs_n[:,i] , y = eff_n[:,i]*100, 
                                             line = dict(color = color[i], 
                                             width = 1, dash ='dash'), marker = dict(size=4),                                            
                                             name = str(int(speed_n[i].magnitude))+' '+speed_unit_out+' - '+ str(int(round(100*speed_fraction_n[i].magnitude,0)))+ '% N<sub>rated</sub>'))
            
            if t_sheet.range('C18').value == 'SIM' and t_sheet['B31'].value =='Performance Calculada':
                Data_H_n.append(go.Scatter(x = flow_v_T , y = Head_T, opacity=0.55,
                                                marker = dict(color ='gold', size = 9, line = dict(width =1.5,color ='black')),
                                                           mode='markers', name = 'Test'))
                Data_eff_n.append(go.Scatter(x = flow_v_T , y = 100*eff_T, opacity=0.55,
                                                marker = dict(color ='gold', size = 9, line = dict(width =1.5,color ='black')),
                                                           mode='markers', name = 'Test'))
                
            Data_H_n = tuple(Data_H_n)
            Data_eff_n = tuple(Data_eff_n)
            
            fig = go.Figure(
                Data_H_n,
                layout_title_text="Head Politrópico x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> ('+flow_unit_out+')',yaxis_title='H<sub>p</sub> ('+ head_unit_out+')',showlegend = True)
            figs_n.append(fig)
            
            
            fig = go.Figure(
                Data_eff_n,
                layout_title_text="Eficiência Politrópica x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> ('+flow_unit_out+')',yaxis_title='\u03b7<sub>p</sub> (%)',showlegend = True)
            figs_n.append(fig)
            
            for i, fig in enumerate(figs_n):
                w=1000
                h=500
                fig.update_layout(width=w,height=h)
                try:
                    graf_n_sheet.pictures.add(fig,top=i*(h-100))
                except:
                    pass
                
            ##########################################  
            #New curves - converted to original speeds
            
            Data_H_n_o =   list()
            Data_eff_n_o = list()
            Data_err = list()
            
            for i in range(N_speed):
                Data_H_n_o.append(go.Scatter(x = Qs_n_o[:,i] , y = H_n_o[:,i], 
                                             line = dict(color = color[i], 
                                             width = 1, dash ='dash'), marker = dict(size=4), 
                                             name = str(int(speed_o[i].magnitude))+' '+speed_unit_out+' - '+ str(int(round(100*speed_fraction_o[i].magnitude,0)))+ '% N<sub>rated</sub>'))
                Data_eff_n_o.append(go.Scatter(x = Qs_n_o[:,i] , y = eff_n_o[:,i]*100, 
                                               line = dict(color = color[i], 
                                               width = 1, dash ='dash'), marker = dict(size=4),                                                
                                               name = str(int(speed_o[i].magnitude))+' '+speed_unit_out+' - '+ str(int(round(100*speed_fraction_o[i].magnitude,0)))+ '% N<sub>rated</sub>'))
                if simp_question == 'SIM':
                    Data_err.append(go.Scatter(x = Qs_o[:,i] , y = erro_vr[:,i]*100, 
                                               marker = dict (color = color[i],
                                               size = 1.5,
                                               line = dict(
                                               color = color[i],
                                               width = 2)),                                               
                                               name = str(int(speed_o[i].magnitude))+' rpm - '+ str(int(round(100*speed_fraction_o[i].magnitude,0)))+ '% N<sub>rated</sub>'))
                
            if t_sheet.range('C18').value == 'SIM' and t_sheet['B31'].value =='Performance Calculada':
                Data_H_n_o.append(go.Scatter(x = flow_v_T , y = Head_T, opacity=0.55,
                                                    marker = dict(color ='gold', size = 9, line = dict(width =1.5,color ='black')),
                                                               mode='markers', name = 'Test'))
                Data_eff_n_o.append(go.Scatter(x = flow_v_T , y = 100*eff_T, opacity=0.55,
                                                    marker = dict(color ='gold', size = 9, line = dict(width =1.5,color ='black')),
                                                               mode='markers', name = 'Test'))
            
            
            Data_H_n_o = tuple(Data_H_n_o)
            Data_eff_n_o = tuple(Data_eff_n_o)
            Data_err = tuple(Data_err)
            
            fig = go.Figure(
                Data_H_n_o,
                layout_title_text="Head Politrópico x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> ('+flow_unit_out+')',yaxis_title='H<sub>p</sub> ('+ head_unit_out+')',showlegend = True)
            figs_n_o.append(fig)
            
            
            fig = go.Figure(
                Data_eff_n_o,
                layout_title_text="Eficiência Politrópica x Vazão Volumétrica de Sucção"
            )
            fig.update_layout(xaxis_title='Q<sub>s</sub> ('+flow_unit_out+')',yaxis_title='\u03b7<sub>p</sub> (%)',showlegend = True)
            figs_n_o.append(fig)
            
            if simp_question == 'SIM':
                fig = go.Figure(
                    Data_err,
                    layout_title_text="Erro da razão entre volume específico x Vazão Volumétrica de Sucção"
                )
                fig.update_layout(xaxis_title='Q<sub>s</sub> ('+flow_unit_out+')',yaxis_title='\u03B5<sub>\u03c5<sub>r</sub></sub> (%)',showlegend = True)
                figs_n_o.append(fig)
            
            for i, fig in enumerate(figs_n_o):
                w=1000
                h=500
                fig.update_layout(width=w,height=h)
                try:
                    graf_n_.pictures.add(fig,top=i*(h-100)).pictures.add(fig,top=i*(h-100))
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
            t_sheet.api.Unprotect()
            CF_sheet.api.Unprotect()
            
            o_sheet["I6"].value = '||'
            n_sheet["G8"].value = '||'
            t_sheet["D31"].value = '||'
            CF_sheet["N23"].value = '||'
            
            secs = o_sheet["L13"].value
            
            o_sheet.api.Protect()
            n_sheet.api.Protect()
            t_sheet.api.Protect()
            CF_sheet.api.Protect()
            
            try:
                sleep(secs)   
            except TypeError:
                print('integer or float must be provided!')
            o_sheet.api.Unprotect()
            n_sheet.api.Unprotect()
            t_sheet.api.Unprotect()
            CF_sheet.api.Unprotect()
            o_sheet["L13"].value = None
            o_sheet["I6"].value = 'ON'
            n_sheet["G8"].value = 'ON'
            t_sheet["D31"].value = 'ON'
            CF_sheet["N23"].value = 'ON'
            sleep(1)
            o_sheet.api.Protect()
            n_sheet.api.Protect()
            t_sheet.api.Protect()
            CF_sheet.api.Protect()
        else:
            sleep(1)
        try:
            aux=open(FileName,'r+')
            Open=False
        except:
            Open=True
    

    
