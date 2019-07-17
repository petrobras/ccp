import xlwings as xw
import ccp
from ccp import State, Q_
import numpy as np

wb = xw.Book('Modelo_2sections.xlsx')  # connect to an existing file in the current working directory

FD_sheet=wb.sheets['DataSheet']
AT_sheet=wb.sheets['Actual Test Data']

### Reading and writing SECTION 1 from the FD sheet

Ps_FD = Q_(FD_sheet['T23'].value,'bar')
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

brake_pow1_FD = Q_(FD_sheet.range('T36').value,'kW')

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
    FD_sheet['AU34'].value='kg/h'
else:
    flow_v_FD=flow_m_FD/sucFD.rho()
    FD_sheet['AS34'].value=flow_v_FD.to('m³/h').magnitude
    FD_sheet['AQ34'].value='Inlet Volume Flow'
    FD_sheet['AU34'].value='m³/h'

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

#Processando dados de projeto do Side Stream

SS_config = FD_sheet.range('W18').value

Ps2_FD = Pd_FD*0.995
if SS_config=='IN':
    TSS_FD = Q_(FD_sheet.range('W24').value,'degC')
else:
    TSS_FD = Td_FD

Pd2_FD = Q_(FD_sheet.range('Z31').value,'bar')
Td2_FD = Q_(FD_sheet.range('Z32').value,'degC')


if FD_sheet.range('W21').value==None: 
    V_test=True
    flowSS_v_FD = Q_(FD_sheet.range('W29').value,'m³/h')
else:
    V_test=False
    flowSS_m_FD = Q_(FD_sheet.range('W21').value,'kg/h')

brake_pow2_FD = Q_(FD_sheet.range('Z36').value,'kW')

D2 = Q_(FD_sheet.range('AB133').value,'mm')
b2 = Q_(FD_sheet.range('AQ133').value,'mm')

if SS_config=='IN':
    GasesFD = FD_sheet.range('B69:B85').value
    mol_fracSS_FD = FD_sheet.range('N69:N85').value

    fluidSS_FD={GasesFD[i] : mol_fracSS_FD[i] for i in range(len(GasesFD))}
else:
    fluidSS_FD=fluid_FD

SS_FD = State.define(fluid=fluidSS_FD , p=Ps2_FD , T=TSS_FD)

if V_test:
    flowSS_m_FD=flowSS_v_FD*SS_FD.rho()
    FD_sheet['AS36'].value=flowSS_m_FD.to('kg/h').magnitude
    FD_sheet['AQ36'].value='SS Mass Flow'
    FD_sheet['AU36'].value='kg/h'
else:
    flowSS_v_FD=flowSS_m_FD/SS_FD.rho()
    FD_sheet['AS36'].value=flowSS_v_FD.to('m³/h').magnitude
    FD_sheet['AQ36'].value='SS Volume Flow'
    FD_sheet['AU36'].value='m³/h'


if SS_config=='IN':
    flow2_m_FD=flow_m_FD+flowSS_m_FD
    RSS=flowSS_m_FD/flow2_m_FD
    R1=flow_m_FD/flow2_m_FD
    
    fluid2_FD={GasesFD[i] : mol_fracSS_FD[i]*RSS+mol_fracFD[i]*R1 for i in range(len(GasesFD))}
    h2_FD=dischFD.h()*R1+SS_FD.h()*RSS

    suc2FD=State.define(fluid=fluid2_FD , p=Ps2_FD , h=h2_FD)
    disch2FD=State.define(fluid=fluid2_FD , p=Pd2_FD , T=Td2_FD)
    FD_sheet['AT35'].value=suc2FD.T().to('degC').magnitude
else:
    fluid2_FD=fluid_FD
    flow2_m_FD=flow_m_FD-flowSS_m_FD
    
    suc2FD=State.define(fluid=fluid2_FD , p=Ps2_FD , T=Td_FD)
    disch2FD=State.define(fluid=fluid2_FD , p=Pd2_FD , T=Td2_FD)
    FD_sheet['AT35'].value=suc2FD.T().to('degC').magnitude
    

P2_FD=ccp.Point(speed=speed_FD,flow_m=flow2_m_FD,suc=suc2FD,disch=disch2FD)
P2_FD_=ccp.Point(speed=speed_FD,flow_m=flow2_m_FD*0.001,suc=suc2FD,disch=disch2FD)

if V_test:
    
    FD_sheet['AT34'].value=P2_FD.flow_m.to('kg/h').magnitude
else:
    
    FD_sheet['AT34'].value=P2_FD.flow_v.to('m³/h').magnitude
    

Imp2_FD = ccp.Impeller([P2_FD,P2_FD_],b=b2,D=D2)

Q1d_FD=flow_m_FD/dischFD.rho()
FD_sheet['AS37'].value=flowSS_v_FD.to('m³/h').magnitude/Q1d_FD.to('m³/h').magnitude

FD_sheet['AT25'].value=Imp2_FD._mach(P2_FD).magnitude
FD_sheet['AT26'].value=Imp2_FD._reynolds(P2_FD).magnitude
FD_sheet['AT27'].value=1/P2_FD._volume_ratio().magnitude
FD_sheet['AT28'].value=Imp2_FD._phi(P2_FD).magnitude
FD_sheet['AT29'].value=Imp2_FD._psi(P2_FD).magnitude
FD_sheet['AT30'].value=Imp2_FD._work_input_factor(P2_FD).magnitude
FD_sheet['AT32'].value=P2_FD._eff_pol_schultz().magnitude
FD_sheet['AT33'].value=P2_FD._power_calc().to('kW').magnitude
FD_sheet['K90'].value=sucFD.molar_mass().to('g/mol').magnitude
FD_sheet['N90'].value=SS_FD.molar_mass().to('g/mol').magnitude


Curva=FD_sheet['AP42:AS49']
Curva2=FD_sheet['AP53:AS60']

for i in range(10):
    if Curva[i,0].value==None:
        Nc=i
        break

for i in range(10):
    if Curva2[i,0].value==None:
        Nc2=i
        break        

Curva=Curva[0:Nc+1,:]
Curva2=Curva2[0:Nc2+1,:]

## Organização dos pontos da curva da primeira seção

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
    
## Organização dos pontos da curva da segunda seção
    
QFD2=np.array(Curva2[0:Nc2,0].value)   
    
if (Nc2>0 and min(abs(QFD2-P2_FD.flow_v.to('m³/h').magnitude))==0):
    Gar=[None,None,None,None]
    Curva2[Nc2,:].value=Gar

else:
    Gar=[P2_FD.flow_v.to('m³/h').magnitude,P2_FD._head_pol_schultz().to('kJ/kg').magnitude,
      None,P2_FD._eff_pol_schultz().magnitude]
    Curva2[Nc2,:].value=Gar
    Nc2=Nc2+1


QFD2=np.array(Curva2[0:Nc2,0].value)

Id2=list(np.argsort(QFD2))

if len(Id2)>1:
    Caux2=Curva2.value

    for i in range(Nc2):
        Curva2[i,:].value=Caux2[Id2[i]][:]
    
    

### Reading and writing in the Actual Test Data Sheet

Dados_AT=AT_sheet['G7:S16']

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
P2_AT=[]

fluid_AT={}
for i in range(len(GasesT)):
    if mol_fracT[i]>0:
        fluid_AT.update({GasesT[i]:mol_fracT[i]})

for i in range(N):

    Ps_AT = Q_(Dados_AT[i,2].value,AT_sheet.range('I6').value)
    Ts_AT = Q_(Dados_AT[i,3].value,AT_sheet.range('J6').value)

    Pd_AT = Q_(Dados_AT[i,4].value,AT_sheet.range('K6').value)
    Td_AT = Q_(Dados_AT[i,5].value,AT_sheet.range('L6').value)


    if Dados_AT[i,0].value==None: 
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
        
    
    ## Carregando dados da segunda seção
    
    
    Ps2_AT = Pd_AT*0.995

    if SS_config=='IN':
        TSS_AT = Q_(Dados_AT[i,8].value,AT_sheet.range('O6').value)
    else:
        TSS_AT = Td_AT

    Pd2_AT = Q_(Dados_AT[i,9].value,AT_sheet.range('P6').value)
    Td2_AT = Q_(Dados_AT[i,10].value,AT_sheet.range('Q6').value)

    if Dados_AT[i,6].value==None: 
        V_test=True
        flowSS_v_AT = Q_(Dados_AT[i,7].value,AT_sheet.range('N6').value)
    else:
        V_test=False
        flowSS_m_AT = Q_(Dados_AT[i,6].value,AT_sheet.range('M6').value)

    fluidSS_AT=fluid_AT

    SS_AT = State.define(fluid=fluidSS_AT , p=Ps2_AT , T=TSS_AT)

    if V_test:
        flowSS_m_AT=flowSS_v_AT*SS_AT.rho()
        Dados_AT[i,6].value=flowSS_m_AT.to(AT_sheet.range('M6').value).magnitude
    else:
        flowSS_v_AT=flowSS_m_AT/SS_AT.rho()
        Dados_AT[i,7].value=flowSS_v_AT.to(AT_sheet.range('N6').value).magnitude


    if SS_config=='IN':
        flow2_m_AT=flow_m_AT+flowSS_m_AT
        RSS=flowSS_m_AT/flow2_m_AT
        R1=flow_m_AT/flow2_m_AT

        fluid2_AT=fluid_AT
        h2_AT=dischAT.h()*R1+SS_AT.h()*RSS

        suc2AT=State.define(fluid=fluid2_AT , p=Ps2_AT , h=h2_AT)
        disch2AT=State.define(fluid=fluid2_AT , p=Pd2_AT , T=Td2_AT)
        
    else:
        fluid2_AT=fluid_AT
        flow2_m_AT=flow_m_AT-flowSS_m_AT

        suc2AT=State.define(fluid=fluid2_AT , p=Ps2_AT , T=Td_AT)
        disch2FD=State.define(fluid=fluid2_AT , p=Pd2_AT , T=Td2_AT)
        
    Dados_AT[i,11].value=suc2AT.T().to(AT_sheet.range('R6').value).magnitude   
    
    Q1d_AT=flow_m_AT/dischAT.rho()
    Dados_AT[i,12].value=flowSS_v_AT.to('m³/h').magnitude/Q1d_AT.to('m³/h').magnitude/(flowSS_v_FD.to('m³/h').magnitude/Q1d_FD.to('m³/h').magnitude)

    P2_AT.append(ccp.Point(speed=speed_AT,flow_m=flow2_m_AT,suc=suc2AT,disch=disch2AT))
    if N==1:
        P2_AT.append(ccp.Point(speed=speed_AT,flow_m=flow2_m_AT*0.001,suc=suc2AT,disch=disch2AT))

        

Imp_AT = ccp.Impeller([P_AT[i] for i in range(len(P_AT))],b=b,D=D)
Imp2_AT = ccp.Impeller([P2_AT[i] for i in range(len(P2_AT))],b=b2,D=D2)    


speed_AT

if AT_sheet['U3'].value=='Vazão Seção 1':
    QQ=np.array(Dados_AT[:,1].value)
    
else:
    QQ=[]
    for i in range(N):
        QQ.append(P2_AT[i].flow_v.magnitude)
    
Id=list(np.argsort(QQ))

if len(Id)>1:
    Daux=Dados_AT.value
    Paux=[P for P in P_AT]
    P2aux=[P for P in P2_AT]
    for i in range(N):
        Dados_AT[i,:].value=Daux[Id[i]][:]
        P_AT[i]=Paux[Id[i]]
        P2_AT[i]=P2aux[Id[i]]


P_ATconv=[]
P2_ATconv=[]

Results_AT=AT_sheet['G22:AB31']
Results_AT.value=[[None]*len(Results_AT[0,:].value)]*10
Results_AT=Results_AT[0:N,:]

Results2_AT=AT_sheet['G37:AB46']
Results2_AT.value=[[None]*len(Results2_AT[0,:].value)]*10
Results2_AT=Results2_AT[0:N,:]

for i in range(N):

    if AT_sheet['C23'].value=='Yes':
        rug=AT_sheet['D24'].value

        ReAT=Imp_AT._reynolds(P_AT[i])
        Re2AT=Imp2_AT._reynolds(P2_AT[i])
        ReFD=Imp_FD._reynolds(P_FD)
        Re2FD=Imp2_FD._reynolds(P2_FD)

        RCAT=0.988/ReAT**0.243
        RC2AT=0.988/Re2AT**0.243
        RCFD=0.988/ReFD**0.243
        RC2FD=0.988/Re2FD**0.243

        RBAT=np.log(0.000125+13.67/ReAT)/np.log(rug+13.67/ReAT)
        RB2AT=np.log(0.000125+13.67/Re2AT)/np.log(rug+13.67/Re2AT)
        RBFD=np.log(0.000125+13.67/ReFD)/np.log(rug+13.67/ReFD)
        RB2FD=np.log(0.000125+13.67/Re2FD)/np.log(rug+13.67/Re2FD)

        RAAT=0.066+0.934*(4.8e6*b.to('ft').magnitude/ReAT)**RCAT
        RA2AT=0.066+0.934*(4.8e6*b2.to('ft').magnitude/Re2AT)**RC2AT
        RAFD=0.066+0.934*(4.8e6*b.to('ft').magnitude/ReFD)**RCFD
        RA2FD=0.066+0.934*(4.8e6*b2.to('ft').magnitude/Re2FD)**RC2FD

        corr=RAFD/RAAT*RBFD/RBAT
        corr2=RA2FD/RA2AT*RB2FD/RB2AT
        
        if abs(1-Imp_AT._phi(P_AT[i]).magnitude/Imp_FD._phi(P_FD).magnitude)<0.04:
            eff=1-(1-P_AT[i]._eff_pol_schultz())*corr
        else:
            eff=P_AT[i]._eff_pol_schultz()
            
        if abs(1-Imp2_AT._phi(P2_AT[i]).magnitude/Imp2_FD._phi(P2_FD).magnitude)<0.04:
            eff2=1-(1-P2_AT[i]._eff_pol_schultz())*corr2
        else:
            eff2=P2_AT[i]._eff_pol_schultz()
            
        Results_AT[i,21].value=eff.magnitude
        Results2_AT[i,21].value=eff2.magnitude
        
        P_ATconv.append(ccp.Point(suc=P_FD.suc, eff=eff,
                                  speed=speed_FD,flow_v=P_AT[i].flow_v*N_ratio,
                                 head=P_AT[i]._head_pol_schultz()*N_ratio**2))
        P2_ATconv.append(ccp.Point(suc=P2_FD.suc, eff=eff2,
                                  speed=speed_FD,flow_v=P2_AT[i].flow_v*N_ratio,
                                 head=P2_AT[i]._head_pol_schultz()*N_ratio**2))

    else:

        P_ATconv.append(ccp.Point(suc=P_FD.suc, eff=P_AT[i]._eff_pol_schultz(),
                                  speed=speed_FD,flow_v=P_AT[i].flow_v*N_ratio,
                                 head=P_AT[i]._head_pol_schultz()*N_ratio**2))
        P2_ATconv.append(ccp.Point(suc=P2_FD.suc, eff=P2_AT[i]._eff_pol_schultz(),
                                  speed=speed_FD,flow_v=P2_AT[i].flow_v*N_ratio,
                                 head=P2_AT[i]._head_pol_schultz()*N_ratio**2))
        Results_AT[i,21].value=P_AT[i]._eff_pol_schultz()
        Results2_AT[i,21].value=P2_AT[i]._eff_pol_schultz()

    ## Escrevendo resultados para a Seção 1
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
    
    
    ## Escrevendo resultados para Seção 2
    
    Results2_AT[i,0].value=1/P2_AT[i]._volume_ratio().magnitude
    Results2_AT[i,1].value=1/(P2_AT[i]._volume_ratio().magnitude/P2_FD._volume_ratio().magnitude)
    Results2_AT[i,2].value=Imp2_AT._mach(P2_AT[i]).magnitude
    Results2_AT[i,3].value=Imp2_AT._mach(P2_AT[i]).magnitude-Imp2_FD._mach(P2_FD).magnitude
    Results2_AT[i,4].value=Imp2_AT._reynolds(P2_AT[i]).magnitude
    Results2_AT[i,5].value=Imp2_AT._reynolds(P2_AT[i]).magnitude/Imp2_FD._reynolds(P2_FD).magnitude
    Results2_AT[i,6].value=Imp2_AT._phi(P2_AT[i]).magnitude
    Results2_AT[i,7].value=Imp2_AT._phi(P2_AT[i]).magnitude/Imp2_FD._phi(P2_FD).magnitude
    Results2_AT[i,8].value=Imp2_AT._psi(P2_AT[i]).magnitude
    Results2_AT[i,9].value=Imp2_AT._psi(P2_AT[i]).magnitude/Imp2_FD._psi(P2_FD).magnitude
    Results2_AT[i,10].value=P2_AT[i]._head_pol_schultz().to('kJ/kg').magnitude
    Results2_AT[i,11].value=P2_AT[i]._head_pol_schultz().to('kJ/kg').magnitude/P2_FD._head_pol_schultz().to('kJ/kg').magnitude
    Results2_AT[i,12].value=P2_ATconv[i]._head_pol_schultz().to('kJ/kg').magnitude
    Results2_AT[i,13].value=P2_ATconv[i]._head_pol_schultz().to('kJ/kg').magnitude/P2_FD._head_pol_schultz().to('kJ/kg').magnitude
    Results2_AT[i,14].value=P2_ATconv[i].flow_v.to('m³/h').magnitude
    Results2_AT[i,15].value=P2_ATconv[i].flow_v.to('m³/h').magnitude/P2_FD.flow_v.to('m³/h').magnitude
    Results2_AT[i,16].value=P2_AT[i]._power_calc().to('kW').magnitude
    Results2_AT[i,17].value=P2_AT[i]._power_calc().to('kW').magnitude/P2_FD._power_calc().to('kW').magnitude

    if AT_sheet['C25'].value=='Yes':

        HL2_FD=Q_(((suc2FD.T()+disch2FD.T()).to('degC').magnitude*0.8/2-25)*1.166*AT_sheet['D28'].value,'W')
        HL2_AT=Q_(((P2_AT[i].suc.T()+P2_AT[i].disch.T()).to('degC').magnitude*0.8/2-25)*1.166*AT_sheet['D28'].value,'W')

        Results2_AT[i,18].value=(P2_ATconv[i]._power_calc()-HL2_AT+HL2_FD).to('kW').magnitude
        Results2_AT[i,19].value=(P2_ATconv[i]._power_calc()-HL2_AT+HL2_FD).to('kW').magnitude/(P2_FD._power_calc()).to('kW').magnitude

    else:
        Results2_AT[i,18].value=P2_ATconv[i]._power_calc().to('kW').magnitude
        Results2_AT[i,19].value=P2_ATconv[i]._power_calc().to('kW').magnitude/P2_FD._power_calc().to('kW').magnitude


    Results2_AT[i,20].value=P2_AT[i]._eff_pol_schultz().magnitude
    
    
    
    

Phi=np.abs(1-np.array(Results_AT[0:N,7].value))
Phi2=np.abs(1-np.array(Results2_AT[0:N,7].value))

IdG=[]
IdG2=[]

for i in range(N):
    try:
        if Phi[i]<0.04:
            IdG.append(i)
    except:
        if Phi<0.04:
            IdG.append(i)
    try:
        if Phi2[i]<0.04:
            IdG2.append(i)
    except:
        if Phi2<0.04:
            IdG2.append(i)


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
    
if len(IdG2)==1:
    AT_sheet['G47:AB47'].value=Results2_AT[IdG2[0],:].value
elif len(IdG2)>1:
    IdG2=[int(k) for k in np.argsort(Phi2)[0:2]]
    IdG2=sorted(IdG2)
    aux1=np.array(Results2_AT[IdG2[0],:].value)
    aux2=np.array(Results2_AT[IdG2[1],:].value)
    f=(1-aux1[7])/(aux2[7]-aux1[7])
    
    aux=aux1+f*(aux2-aux1)
    AT_sheet['G47:AB47'].value=aux
else:
    
    AT_sheet['G47:AB47'].value=[None]*len(Results2_AT[0,:].value)