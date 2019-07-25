



import os
FileName=os.path.basename(__file__)[:-3]


from xlwings import Book

wb = Book(FileName)  # connect to an existing file in the current working directory
AT_sheet=wb.sheets['Actual Test Data']
TP_sheet=wb.sheets['Test Procedure Data']
FD_sheet=wb.sheets['DataSheet']

AT_sheet['F36'].value='Carregando bibliotecas...'
TP_sheet['J23'].value='Carregando bibliotecas...'

import xlwings as xw
import os
from time import sleep
try:
    aux=os.environ['RPprefix']
except:
    os.environ['RPprefix']='C:\\Users\\Public\\REFPROP'
import ccp
from ccp import State, Q_
import numpy as np


AT_sheet['H35'].value=None
TP_sheet['K19'].value=None
FD_sheet['A1'].value=None


AT_sheet['F36'].value='READY!'
TP_sheet['J23'].value='READY!'

Open_file=True

while Open_file:
    
    

    wb = xw.Book(FileName)  # connect to an existing file in the current working directory

    
    AT_sheet=wb.sheets['Actual Test Data']
    TP_sheet=wb.sheets['Test Procedure Data']
    FD_sheet=wb.sheets['DataSheet']
    
    if FD_sheet['A1'].value!=None:
        FD_sheet['A1'].value=None
        Open_file=False
    
    if AT_sheet['H35'].value!=None:
        
        AT_sheet['H35'].value=None
        AT_sheet['F36'].value="Calculando..."
        
        
        ### Reading and writing in the FD sheet

        Ps_FD = Q_(FD_sheet.range('T23').value,'bar')
        Ts_FD = Q_(FD_sheet.range('T24').value,'degC')

        Pd_FD = Q_(FD_sheet.range('T31').value,'bar')
        Td_FD = Q_(FD_sheet.range('T32').value,'degC')


        if FD_sheet.range('T21').value==None: 
            V_test=True
            flow_v_FD = Q_(FD_sheet.range('T29').value,'m³/h')
        else:
            V_test=False
            flow_m_FD = Q_(FD_sheet.range('T21').value,'kg/h')

        #flow_m_FD = Q_(FD_sheet.range('T21').value,'kg/h')
        #flow_v_FD = Q_(FD_sheet.range('T29').value,'m**3/h')

        speed_FD = Q_(FD_sheet.range('T38').value,'rpm')

        brake_pow_FD = Q_(FD_sheet.range('T36').value,'kW')
        Pol_head_FD = Q_(FD_sheet.range('T40').value,'J/kg')
        Pol_eff_FD = Q_(FD_sheet.range('T41').value,'dimensionless')

        D = Q_(FD_sheet.range('AB132').value,'mm')
        b = Q_(FD_sheet.range('AQ132').value,'mm')

        GasesFD = FD_sheet.range('B69:B85').value
        mol_fracFD = FD_sheet.range('K69:K85').value

        fluid_FD={GasesFD[i] : mol_fracFD[i] for i in range(len(GasesFD))}


        sucFD=State.define(fluid=fluid_FD , p=Ps_FD , T=Ts_FD)

        if V_test:
            flow_m_FD=flow_v_FD*sucFD.rho()
            FD_sheet['AS34'].value=flow_m_FD.to('kg/h').magnitude
            FD_sheet['AQ34'].value='Mass Flow'
            FD_sheet['AT34'].value='kg/h'
        else:
            flow_v_FD=flow_m_FD/sucFD.rho()
            FD_sheet['AS34'].value=flow_v_FD.to('m³/h').magnitude
            FD_sheet['AQ34'].value='Inlet Volume Flow'
            FD_sheet['AT34'].value='m³/h'

        dischFD=State.define(fluid=fluid_FD , p=Pd_FD , T=Td_FD)

        P_FD=ccp.Point(speed=speed_FD,flow_m=flow_m_FD,suc=sucFD,disch=dischFD)
        P_FD_=ccp.Point(speed=speed_FD,flow_m=flow_m_FD*0.001,suc=sucFD,disch=dischFD)

        Imp_FD = ccp.Impeller([P_FD,P_FD_],b=b,D=D)

        FD_sheet['AS25'].value=Imp_FD._mach(P_FD).magnitude
        FD_sheet['AS26'].value=Imp_FD._reynolds(P_FD).magnitude
        FD_sheet['AS27'].value=1/P_FD._volume_ratio().magnitude
        FD_sheet['AS28'].value=Imp_FD._phi(P_FD).magnitude
        FD_sheet['AS29'].value=Imp_FD._psi(P_FD).magnitude
        FD_sheet['AS30'].value=Imp_FD._work_input_factor(P_FD).magnitude
        FD_sheet['AS32'].value=P_FD._eff_pol_schultz().magnitude
        FD_sheet['AS33'].value=P_FD._power_calc().to('kW').magnitude
        FD_sheet['K90'].value=sucFD.molar_mass().to('g/mol').magnitude


        Curva=FD_sheet['AP39:AS46']

        for i in range(10):
            if Curva[i,0].value==None:
                Nc=i
                break

        Curva=Curva[0:Nc+1,:]

        QFD=np.array(Curva[0:Nc,0].value)

        if (Nc>0 and min(abs(QFD-flow_v_FD.to('m³/h').magnitude))==0):
            Gar=[None,None,None,None]
            Curva[Nc,:].value=Gar

        else:
            Gar=[flow_v_FD.to('m³/h').magnitude,P_FD._head_pol_schultz().to('kJ/kg').magnitude,
              None,P_FD._eff_pol_schultz().magnitude]
            Curva[Nc,:].value=Gar
            Nc=Nc+1


        QFD=np.array(Curva[0:Nc,0].value)

        Id=list(np.argsort(QFD))

        if len(Id)>1:
            Caux=Curva.value

            for i in range(Nc):
                Curva[i,:].value=Caux[Id[i]][:]

        ### Reading and writing in the Test Procedure Sheet

        Dados_AT=AT_sheet['G7:L16']

        for i in range(10):
            if Dados_AT[i,5].value==None:
                N=i
                break

        Dados_AT=Dados_AT[0:N,:]


        speed_AT = Q_(AT_sheet.range('H4').value,AT_sheet.range('I4').value)
        N_ratio=speed_FD/speed_AT

        GasesT = AT_sheet.range('B4:B20').value
        mol_fracT = AT_sheet.range('D4:D20').value

        P_AT=[]

        fluid_AT={}
        for i in range(len(GasesT)):
            if mol_fracT[i]>0:
                fluid_AT.update({GasesT[i]:mol_fracT[i]})

        for i in range(N):

            Ps_AT = Q_(Dados_AT[i,2].value,AT_sheet.range('I6').value)
            Ts_AT = Q_(Dados_AT[i,3].value,AT_sheet.range('J6').value)

            Pd_AT = Q_(Dados_AT[i,4].value,AT_sheet.range('K6').value)
            Td_AT = Q_(Dados_AT[i,5].value,AT_sheet.range('L6').value)


            if Dados_AT[i,1].value!=None: 
                V_test=True
                flow_v_AT = Q_(Dados_AT[i,1].value,AT_sheet.range('H6').value)
            else:
                V_test=False
                flow_m_AT = Q_(Dados_AT[i,0].value,AT_sheet.range('G6').value)

            sucAT=State.define(fluid=fluid_AT , p=Ps_AT , T=Ts_AT)
            dischAT=State.define(fluid=fluid_AT , p=Pd_AT , T=Td_AT)

            if V_test:
                flow_m_AT=flow_v_AT*sucAT.rho()
                Dados_AT[i,0].value=flow_m_AT.to(AT_sheet['G6'].value).magnitude
            else:
                flow_v_AT=flow_m_AT/sucAT.rho()
                Dados_AT[i,1].value=flow_v_AT.to(AT_sheet['H6'].value).magnitude

            P_AT.append(ccp.Point(speed=speed_AT,flow_m=flow_m_AT,suc=sucAT,disch=dischAT))
            if N==1:
                P_AT.append(ccp.Point(speed=speed_AT,flow_m=flow_m_AT*0.001,suc=sucAT,disch=dischAT))



        Imp_AT = ccp.Impeller([P_AT[i] for i in range(len(P_AT))],b=b,D=D)
        # Imp_AT.new_suc = P_FD.suc

        QQ=np.array(Dados_AT[:,1].value)
        Id=list(np.argsort(QQ))
        Daux=Dados_AT.value
        Paux=[P for P in P_AT]

        for i in range(N):
            Dados_AT[i,:].value=Daux[Id[i]][:]
            P_AT[i]=Paux[Id[i]]


        P_ATconv=[]

        Results_AT=AT_sheet['G22:AB32']
        Results_AT.value=[[None]*len(Results_AT[0,:].value)]*11
        Results_AT=Results_AT[0:N,:]

        for i in range(N):

            if AT_sheet['C23'].value=='Yes':
                rug=AT_sheet['D24'].value

                ReAT=Imp_AT._reynolds(P_AT[i])
                ReFD=Imp_FD._reynolds(P_FD)

                RCAT=0.988/ReAT**0.243
                RCFD=0.988/ReFD**0.243

                RBAT=np.log(0.000125+13.67/ReAT)/np.log(rug+13.67/ReAT)
                RBFD=np.log(0.000125+13.67/ReFD)/np.log(rug+13.67/ReFD)

                RAAT=0.066+0.934*(4.8e6*b.to('ft').magnitude/ReAT)**RCAT
                RAFD=0.066+0.934*(4.8e6*b.to('ft').magnitude/ReFD)**RCFD

                corr=RAFD/RAAT*RBFD/RBAT

                eff=1-(1-P_AT[i]._eff_pol_schultz())*corr

                Results_AT[i,21].value=eff.magnitude

                P_ATconv.append(ccp.Point(suc=P_FD.suc, eff=eff,
                                          speed=speed_FD,flow_v=P_AT[i].flow_v*N_ratio,
                                         head=P_AT[i]._head_pol_schultz()*N_ratio**2))

            else:

                P_ATconv.append(ccp.Point(suc=P_FD.suc, eff=P_AT[i]._eff_pol_schultz(),
                                          speed=speed_FD,flow_v=P_AT[i].flow_v*N_ratio,
                                         head=P_AT[i]._head_pol_schultz()*N_ratio**2))
                Results_AT[i,21].value=''


            Results_AT[i,0].value=1/P_AT[i]._volume_ratio().magnitude
            Results_AT[i,1].value=1/(P_AT[i]._volume_ratio().magnitude/P_FD._volume_ratio().magnitude)
            Results_AT[i,2].value=Imp_AT._mach(P_AT[i]).magnitude
            Results_AT[i,3].value=Imp_AT._mach(P_AT[i]).magnitude-Imp_FD._mach(P_FD).magnitude
            Results_AT[i,4].value=Imp_AT._reynolds(P_AT[i]).magnitude
            Results_AT[i,5].value=Imp_AT._reynolds(P_AT[i]).magnitude/Imp_FD._reynolds(P_FD).magnitude
            Results_AT[i,6].value=Imp_AT._phi(P_AT[i]).magnitude
            Results_AT[i,7].value=Imp_AT._phi(P_AT[i]).magnitude/Imp_FD._phi(P_FD).magnitude
            Results_AT[i,8].value=Imp_AT._psi(P_AT[i]).magnitude
            Results_AT[i,9].value=Imp_AT._psi(P_AT[i]).magnitude/Imp_FD._psi(P_FD).magnitude
            Results_AT[i,10].value=P_AT[i]._head_pol_schultz().to('kJ/kg').magnitude
            Results_AT[i,11].value=P_AT[i]._head_pol_schultz().to('kJ/kg').magnitude/P_FD._head_pol_schultz().to('kJ/kg').magnitude
            Results_AT[i,12].value=P_ATconv[i]._head_pol_schultz().to('kJ/kg').magnitude
            Results_AT[i,13].value=P_ATconv[i]._head_pol_schultz().to('kJ/kg').magnitude/P_FD._head_pol_schultz().to('kJ/kg').magnitude
            Results_AT[i,14].value=P_ATconv[i].flow_v.to('m³/h').magnitude
            Results_AT[i,15].value=P_ATconv[i].flow_v.to('m³/h').magnitude/P_FD.flow_v.to('m³/h').magnitude
            Results_AT[i,16].value=P_AT[i]._power_calc().to('kW').magnitude
            Results_AT[i,17].value=P_AT[i]._power_calc().to('kW').magnitude/P_FD._power_calc().to('kW').magnitude

            if AT_sheet['C25'].value=='Yes':

                HL_FD=Q_(((sucFD.T()+dischFD.T()).to('degC').magnitude*0.8/2-25)*1.166*AT_sheet['D26'].value,'W')
                HL_AT=Q_(((P_AT[i].suc.T()+P_AT[i].disch.T()).to('degC').magnitude*0.8/2-25)*1.166*AT_sheet['D26'].value,'W')

                Results_AT[i,18].value=(P_ATconv[i]._power_calc()-HL_AT+HL_FD).to('kW').magnitude
                Results_AT[i,19].value=(P_ATconv[i]._power_calc()-HL_AT+HL_FD).to('kW').magnitude/(P_FD._power_calc()).to('kW').magnitude

            else:
                Results_AT[i,18].value=P_ATconv[i]._power_calc().to('kW').magnitude
                Results_AT[i,19].value=P_ATconv[i]._power_calc().to('kW').magnitude/P_FD._power_calc().to('kW').magnitude


            Results_AT[i,20].value=P_AT[i]._eff_pol_schultz().magnitude

        Phi=np.abs(1-np.array(Results_AT[0:N,7].value))

        IdG=[]

        for i in range(N):
            if Phi[i]<0.04:
                IdG.append(i)


        if len(IdG)==1:
            AT_sheet['G32:AB32'].value=Results_AT[IdG[0],:].value
        elif len(IdG)>1:
            IdG=[int(k) for k in np.argsort(Phi)[0:2]]
            IdG=sorted(IdG)
            aux1=np.array(Results_AT[IdG[0],:].value)
            aux2=np.array(Results_AT[IdG[1],:].value)
            f=(1-aux1[7])/(aux2[7]-aux1[7])

            aux=aux1+f*(aux2-aux1)
            AT_sheet['G32:AB32'].value=aux
        else:

            AT_sheet['G32:AB32'].value=[None]*len(Results_AT[0,:].value)
        
        AT_sheet['F36'].value='READY!'
    
    
    ###########################################
    ### INÍCIO DA ROTINA DE TEST PROCEDURE
    ############################################
    
    
    if TP_sheet["K19"].value!=None:
        TP_sheet["K19"].value=None
        TP_sheet["J23"].value="Calculando..."
        
        FD_sheet=wb.sheets['DataSheet']
        
        ### Reading and writing in the FD sheet

        Ps_FD = Q_(FD_sheet.range('T23').value,'bar')
        Ts_FD = Q_(FD_sheet.range('T24').value,'degC')

        Pd_FD = Q_(FD_sheet.range('T31').value,'bar')
        Td_FD = Q_(FD_sheet.range('T32').value,'degC')


        if FD_sheet.range('T21').value==None: 
            V_test=True
            flow_v_FD = Q_(FD_sheet.range('T29').value,'m³/h')
        else:
            V_test=False
            flow_m_FD = Q_(FD_sheet.range('T21').value,'kg/h')

        #flow_m_FD = Q_(FD_sheet.range('T21').value,'kg/h')
        #flow_v_FD = Q_(FD_sheet.range('T29').value,'m**3/h')

        speed_FD = Q_(FD_sheet.range('T38').value,'rpm')

        brake_pow_FD = Q_(FD_sheet.range('T36').value,'kW')
        Pol_head_FD = Q_(FD_sheet.range('T40').value,'J/kg')
        Pol_eff_FD = Q_(FD_sheet.range('T41').value,'dimensionless')

        D = Q_(FD_sheet.range('AB132').value,'mm')
        b = Q_(FD_sheet.range('AQ132').value,'mm')

        GasesFD = FD_sheet.range('B69:B85').value
        mol_fracFD = FD_sheet.range('K69:K85').value

        fluid_FD={GasesFD[i] : mol_fracFD[i] for i in range(len(GasesFD))}


        sucFD=State.define(fluid=fluid_FD , p=Ps_FD , T=Ts_FD)

        if V_test:
            flow_m_FD=flow_v_FD*sucFD.rho()
            FD_sheet['AS34'].value=flow_m_FD.to('kg/h').magnitude
            FD_sheet['AQ34'].value='Mass Flow'
            FD_sheet['AT34'].value='kg/h'
        else:
            flow_v_FD=flow_m_FD/sucFD.rho()
            FD_sheet['AS34'].value=flow_v_FD.to('m³/h').magnitude
            FD_sheet['AQ34'].value='Inlet Volume Flow'
            FD_sheet['AT34'].value='m³/h'

        dischFD=State.define(fluid=fluid_FD , p=Pd_FD , T=Td_FD)

        P_FD=ccp.Point(speed=speed_FD,flow_m=flow_m_FD,suc=sucFD,disch=dischFD)
        P_FD_=ccp.Point(speed=speed_FD,flow_m=flow_m_FD*0.001,suc=sucFD,disch=dischFD)

        Imp_FD = ccp.Impeller([P_FD,P_FD_],b=b,D=D)

        FD_sheet['AS25'].value=Imp_FD._mach(P_FD).magnitude
        FD_sheet['AS26'].value=Imp_FD._reynolds(P_FD).magnitude
        FD_sheet['AS27'].value=1/P_FD._volume_ratio().magnitude
        FD_sheet['AS28'].value=Imp_FD._phi(P_FD).magnitude
        FD_sheet['AS29'].value=Imp_FD._psi(P_FD).magnitude
        FD_sheet['AS30'].value=Imp_FD._work_input_factor(P_FD).magnitude
        FD_sheet['AS32'].value=P_FD._eff_pol_schultz().magnitude
        FD_sheet['AS33'].value=P_FD._power_calc().to('kW').magnitude
        FD_sheet['K90'].value=sucFD.molar_mass().to('g/mol').magnitude

        ### Reading and writing in the Test Procedure Sheet

        Ps_TP = Q_(TP_sheet.range('L6').value,TP_sheet.range('M6').value)
        Ts_TP = Q_(TP_sheet.range('N6').value,TP_sheet.range('O6').value)

        Pd_TP = Q_(TP_sheet.range('P6').value,TP_sheet.range('Q6').value)


        if TP_sheet.range('F6').value==None: 
            V_test=True
            flow_v_TP = Q_(TP_sheet.range('H6').value,TP_sheet.range('I6').value)
        else:
            V_test=False
            flow_m_TP = Q_(TP_sheet.range('F6').value,TP_sheet.range('G6').value)

        speed_TP = Q_(TP_sheet.range('J6').value,TP_sheet.range('K6').value)

        GasesT = TP_sheet.range('B4:B20').value
        mol_fracT = TP_sheet.range('D4:D20').value


        fluid_TP={}
        for i in range(len(GasesT)):
            if mol_fracT[i]>0:
                fluid_TP.update({GasesT[i]:mol_fracT[i]})

        sucTP=State.define(fluid=fluid_TP , p=Ps_TP , T=Ts_TP)
        dischTPk=State.define(fluid=fluid_TP , p=Pd_TP , s=sucTP.s())

        hd_TP=sucTP.h()+(dischTPk.h()-sucTP.h())/P_FD._eff_isen()
        dischTP=State.define(fluid=fluid_TP , p=Pd_TP , h=hd_TP)

        if V_test:
            flow_m_TP=flow_v_TP*sucTP.rho()
            TP_sheet['F6'].value=flow_m_TP.to(TP_sheet['G6'].value).magnitude
        else:
            flow_v_TP=flow_m_TP/sucTP.rho()
            TP_sheet['H6'].value=flow_v_TP.to(TP_sheet['I6'].value).magnitude

        P_TP=ccp.Point(speed=speed_TP,flow_m=flow_m_TP,suc=sucTP,disch=dischTP)
        P_TP_=ccp.Point(speed=speed_TP,flow_m=flow_m_TP*0.001,suc=sucTP,disch=dischTP)

        Imp_TP = ccp.Impeller([P_TP,P_TP_],b=b,D=D)
        # Imp_TP.new_suc = P_FD.suc

        N_ratio=speed_FD/speed_TP
        if TP_sheet['C23'].value=='Yes':
            rug=TP_sheet['D24'].value

            ReTP=Imp_TP._reynolds(P_TP)
            ReFD=Imp_FD._reynolds(P_FD)

            RCTP=0.988/ReTP**0.243
            RCFD=0.988/ReFD**0.243

            RBTP=np.log(0.000125+13.67/ReTP)/np.log(rug+13.67/ReTP)
            RBFD=np.log(0.000125+13.67/ReFD)/np.log(rug+13.67/ReFD)

            RATP=0.066+0.934*(4.8e6*b.to('ft').magnitude/ReTP)**RCTP
            RAFD=0.066+0.934*(4.8e6*b.to('ft').magnitude/ReFD)**RCFD

            corr=RAFD/RATP*RBFD/RBTP

            eff=1-(1-P_TP._eff_pol_schultz())*corr

            TP_sheet['H29'].value=eff.magnitude

            P_TPconv = ccp.Point(suc=P_FD.suc, eff=eff,
                                      speed=speed_FD,flow_v=P_TP.flow_v*N_ratio,
                                     head=P_TP._head_pol_schultz()*N_ratio**2)

        else:

            P_TPconv = ccp.Point(suc=P_FD.suc, eff=P_TP._eff_pol_schultz(),
                                      speed=speed_FD,flow_v=P_TP.flow_v*N_ratio,
                                     head=P_TP._head_pol_schultz()*N_ratio**2)
            TP_sheet['H29'].value=''

        TP_sheet['R6'].value=dischTP.T().to(TP_sheet['S6'].value).magnitude
        TP_sheet['G11'].value=1/P_TP._volume_ratio().magnitude
        TP_sheet['H11'].value=1/(P_TP._volume_ratio().magnitude/P_FD._volume_ratio().magnitude)
        TP_sheet['G12'].value=Imp_TP._mach(P_TP).magnitude
        TP_sheet['H13'].value=Imp_TP._mach(P_TP).magnitude-Imp_FD._mach(P_FD).magnitude
        TP_sheet['G14'].value=Imp_TP._reynolds(P_TP).magnitude
        TP_sheet['H15'].value=Imp_TP._reynolds(P_TP).magnitude/Imp_FD._reynolds(P_FD).magnitude
        TP_sheet['G16'].value=Imp_TP._phi(P_TP).magnitude
        TP_sheet['H17'].value=Imp_TP._phi(P_TP).magnitude/Imp_FD._phi(P_FD).magnitude
        TP_sheet['G18'].value=Imp_TP._psi(P_TP).magnitude
        TP_sheet['H19'].value=Imp_TP._psi(P_TP).magnitude/Imp_FD._psi(P_FD).magnitude
        TP_sheet['G20'].value=P_TP._head_pol_schultz().to('kJ/kg').magnitude
        TP_sheet['H21'].value=P_TP._head_pol_schultz().to('kJ/kg').magnitude/P_FD._head_pol_schultz().to('kJ/kg').magnitude
        TP_sheet['G22'].value=P_TPconv._head_pol_schultz().to('kJ/kg').magnitude
        TP_sheet['H23'].value=P_TPconv._head_pol_schultz().to('kJ/kg').magnitude/P_FD._head_pol_schultz().to('kJ/kg').magnitude
        TP_sheet['G24'].value=P_TP._power_calc().to('kW').magnitude
        TP_sheet['H25'].value=P_TP._power_calc().to('kW').magnitude/P_FD._power_calc().to('kW').magnitude

        if TP_sheet['C25'].value=='Yes':

            HL_FD=Q_(((sucFD.T()+dischFD.T()).to('degC').magnitude*0.8/2-25)*1.166*TP_sheet['D26'].value,'W')
            HL_TP=Q_(((sucTP.T()+dischTP.T()).to('degC').magnitude*0.8/2-25)*1.166*TP_sheet['D26'].value,'W')

            TP_sheet['G26'].value=(P_TPconv._power_calc()-HL_TP+HL_FD).to('kW').magnitude
            TP_sheet['H27'].value=(P_TPconv._power_calc()-HL_TP+HL_FD).to('kW').magnitude/(P_FD._power_calc()).to('kW').magnitude

        else:
            TP_sheet['G26'].value=P_TPconv._power_calc().to('kW').magnitude
            TP_sheet['H27'].value=P_TPconv._power_calc().to('kW').magnitude/P_FD._power_calc().to('kW').magnitude


        TP_sheet['G28'].value=P_TP._eff_pol_schultz().magnitude
        
        TP_sheet["J23"].value="READY!"
        
        
    
    sleep(1)
    try:
        aux=open(FileName,'r+')
        Open=False
    except:
        Open=True