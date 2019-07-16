import xlwings as xw
import ccp
from ccp import State, Q_
import numpy as np

wb = xw.Book('Modelo_2sections.xlsx')  # connect to an existing file in the current working directory

FD_sheet=wb.sheets['DataSheet']
TP_sheet=wb.sheets['Test Procedure Data']

### Reading and writing SECTION 1 from the FD sheet

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



### Reading and writing SECTION 2 from the FD sheet

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

D2 = Q_(FD_sheet.range('AB132').value,'mm')
b2 = Q_(FD_sheet.range('AQ132').value,'mm')

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

### Reading and writing SECTION 1 from the TP sheet

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

# P_TPconv = Imp_TP._calc_from_speed(point=P_TP,new_speed=P_FD.speed)

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
    
    TP_sheet['H37'].value=eff.magnitude
    
    P_TPconv = ccp.Point(suc=P_FD.suc, eff=eff,
                              speed=speed_FD,flow_v=P_TP.flow_v*N_ratio,
                             head=P_TP._head_pol_schultz()*N_ratio**2)
    
else:
    
    P_TPconv = ccp.Point(suc=P_FD.suc, eff=P_TP._eff_pol_schultz(),
                              speed=speed_FD,flow_v=P_TP.flow_v*N_ratio,
                             head=P_TP._head_pol_schultz()*N_ratio**2)
    TP_sheet['H37'].value=''

TP_sheet['R6'].value=dischTP.T().to(TP_sheet['S6'].value).magnitude
TP_sheet['G19'].value=1/P_TP._volume_ratio().magnitude
TP_sheet['H19'].value=1/(P_TP._volume_ratio().magnitude/P_FD._volume_ratio().magnitude)
TP_sheet['G20'].value=Imp_TP._mach(P_TP).magnitude
TP_sheet['H21'].value=Imp_TP._mach(P_TP).magnitude-Imp_FD._mach(P_FD).magnitude
TP_sheet['G22'].value=Imp_TP._reynolds(P_TP).magnitude
TP_sheet['H23'].value=Imp_TP._reynolds(P_TP).magnitude/Imp_FD._reynolds(P_FD).magnitude
TP_sheet['G24'].value=Imp_TP._phi(P_TP).magnitude
TP_sheet['H25'].value=Imp_TP._phi(P_TP).magnitude/Imp_FD._phi(P_FD).magnitude
TP_sheet['G26'].value=Imp_TP._psi(P_TP).magnitude
TP_sheet['H27'].value=Imp_TP._psi(P_TP).magnitude/Imp_FD._psi(P_FD).magnitude
TP_sheet['G28'].value=P_TP._head_pol_schultz().to('kJ/kg').magnitude
TP_sheet['H29'].value=P_TP._head_pol_schultz().to('kJ/kg').magnitude/P_FD._head_pol_schultz().to('kJ/kg').magnitude
TP_sheet['G30'].value=P_TPconv._head_pol_schultz().to('kJ/kg').magnitude
TP_sheet['H31'].value=P_TPconv._head_pol_schultz().to('kJ/kg').magnitude/P_FD._head_pol_schultz().to('kJ/kg').magnitude
TP_sheet['G32'].value=P_TP._power_calc().to('kW').magnitude
TP_sheet['H33'].value=P_TP._power_calc().to('kW').magnitude/P_FD._power_calc().to('kW').magnitude


if TP_sheet['C25'].value=='Yes':
    
    HL_FD=Q_(((sucFD.T()+dischFD.T()).to('degC').magnitude*0.8/2-25)*1.166*TP_sheet['D26'].value,'W')
    HL_TP=Q_(((sucTP.T()+dischTP.T()).to('degC').magnitude*0.8/2-25)*1.166*TP_sheet['D26'].value,'W')
    
    TP_sheet['G34'].value=(P_TPconv._power_calc()-HL_TP+HL_FD).to('kW').magnitude
    TP_sheet['H35'].value=(P_TPconv._power_calc()-HL_TP+HL_FD).to('kW').magnitude/(P_FD._power_calc()).to('kW').magnitude
    
else:
    TP_sheet['G34'].value=P_TPconv._power_calc().to('kW').magnitude
    TP_sheet['H35'].value=P_TPconv._power_calc().to('kW').magnitude/P_FD._power_calc().to('kW').magnitude


TP_sheet['G36'].value=P_TP._eff_pol_schultz().magnitude

### Reading and writing SECTION 2 from the TP sheet

Ps2_TP = Pd_TP*0.995

if SS_config=='IN':
    TSS_TP = Q_(TP_sheet.range('R9').value,TP_sheet.range('S9').value)
else:
    TSS_TP = Td_TP

Pd2_TP = Q_(TP_sheet.range('P14').value,TP_sheet.range('Q14').value)


if TP_sheet.range('L9').value==None: 
    V_test=True
    flowSS_v_TP = Q_(TP_sheet.range('N9').value,TP_sheet.range('O9').value)
else:
    V_test=False
    flowSS_m_TP = Q_(TP_sheet.range('L9').value,TP_sheet.range('M9').value)

speed2_TP = Q_(TP_sheet.range('J14').value,TP_sheet.range('K14').value)    

fluidSS_TP=fluid_TP

SS_TP = State.define(fluid=fluidSS_TP , p=Ps2_TP , T=TSS_TP)

if V_test:
    flowSS_m_TP=flowSS_v_TP*SS_TP.rho()
    TP_sheet['L9'].value=flowSS_m_TP.to(TP_sheet.range('M9').value).magnitude
else:
    flowSS_v_TP=flowSS_m_TP/SS_TP.rho()
    TP_sheet['N9'].value=flowSS_v_TP.to(TP_sheet.range('O9').value).magnitude

if SS_config=='IN':
    flow2_m_TP=flow_m_TP+flowSS_m_TP
    
    TP_sheet['F14'].value=flow2_m_TP.to(TP_sheet.range('G14').value).magnitude
    
    RSS=flowSS_m_TP/flow2_m_TP
    R1=flow_m_TP/flow2_m_TP
    
    fluid2_TP=fluidSS_TP
    
    h2_TP=dischTP.h()*R1+SS_TP.h()*RSS

    suc2TP=State.define(fluid=fluid2_TP , p=Ps2_TP , h=h2_TP)
    flow2_v_TP=flow2_m_TP*suc2TP.v()
    TP_sheet['H14'].value=flow2_v_TP.to(TP_sheet.range('I14').value).magnitude
    
    
    
    
    TP_sheet['N14'].value=suc2TP.T().to(TP_sheet.range('O14').value).magnitude
    
    
else:
    fluid2_TP=fluid_TP
    flow2_m_TP=flow_m_TP-flowSS_m_TP
    TP_sheet['F14'].value=flow2_m_TP.to(TP_sheet.range('G14').value).magnitude
    
    suc2TP=State.define(fluid=fluid2_TP , p=Ps2_TP , T=Td_TP)
    
    flow2_v_TP=flow2_m_TP*suc2TP.v()
    TP_sheet['H14'].value=flow2_v_TP.to(TP_sheet.range('I14').value).magnitude
    
    TP_sheet['N14'].value=suc2FD.T().to(TP_sheet.range('O14').value).magnitude


disch2TPk=State.define(fluid=fluid2_TP , p=Pd2_TP , s=suc2TP.s())

hd2_TP=suc2TP.h()+(disch2TPk.h()-suc2TP.h())/P2_FD._eff_isen()
disch2TP=State.define(fluid=fluid2_TP , p=Pd2_TP , h=hd2_TP) 

TP_sheet['R14'].value=disch2TP.T().to(TP_sheet.range('S14').value).magnitude
   

P2_TP=ccp.Point(speed=speed2_TP,flow_m=flow2_m_TP,suc=suc2TP,disch=disch2TP)
P2_TP_=ccp.Point(speed=speed2_TP,flow_m=flow2_m_TP*0.001,suc=suc2TP,disch=disch2TP)
    

Imp2_TP = ccp.Impeller([P2_TP,P2_TP_],b=b2,D=D2)

# Imp2_TP.new_suc = P2_FD.suc

# P2_TPconv = Imp2_TP._calc_from_speed(point=P2_TP,new_speed=P_FD.speed)

N2_ratio=speed_FD/speed2_TP
if TP_sheet['C23'].value=='Yes':
    rug=TP_sheet['D24'].value
    
    Re2TP=Imp2_TP._reynolds(P2_TP)
    Re2FD=Imp2_FD._reynolds(P2_FD)

    RCTP=0.988/Re2TP**0.243
    RCFD=0.988/Re2FD**0.243

    RBTP=np.log(0.000125+13.67/Re2TP)/np.log(rug+13.67/ReTP)
    RBFD=np.log(0.000125+13.67/Re2FD)/np.log(rug+13.67/ReFD)

    RATP=0.066+0.934*(4.8e6*b.to('ft').magnitude/ReTP)**RCTP
    RAFD=0.066+0.934*(4.8e6*b.to('ft').magnitude/ReFD)**RCFD

    corr=RAFD/RATP*RBFD/RBTP
    
    eff=1-(1-P2_TP._eff_pol_schultz())*corr
    
    TP_sheet['M37'].value=eff.magnitude
    
    P2_TPconv = ccp.Point(suc=P2_FD.suc, eff=eff,
                              speed=speed_FD,flow_v=P2_TP.flow_v*N2_ratio,
                             head=P2_TP._head_pol_schultz()*N2_ratio**2)
    
else:
    
    P2_TPconv = ccp.Point(suc=P2_FD.suc, eff=P2_TP._eff_pol_schultz(),
                              speed=speed_FD,flow_v=P2_TP.flow_v*N2_ratio,
                             head=P2_TP._head_pol_schultz()*N2_ratio**2)
    TP_sheet['M37'].value=''

Q1d_TP=flow_m_TP/dischTP.rho()
TP_sheet['R28'].value=flowSS_v_TP.to('m³/h').magnitude/Q1d_TP.to('m³/h').magnitude
TP_sheet['S28'].value=flowSS_v_TP.to('m³/h').magnitude/Q1d_TP.to('m³/h').magnitude/(flowSS_v_FD.to('m³/h').magnitude/Q1d_FD.to('m³/h').magnitude)

TP_sheet['R14'].value=disch2TP.T().to(TP_sheet.range('S14').value).magnitude
TP_sheet['L19'].value=1/P2_TP._volume_ratio().magnitude
TP_sheet['M19'].value=1/(P2_TP._volume_ratio().magnitude/P2_FD._volume_ratio().magnitude)
TP_sheet['L20'].value=Imp2_TP._mach(P2_TP).magnitude
TP_sheet['M21'].value=Imp2_TP._mach(P2_TP).magnitude-Imp2_FD._mach(P2_FD).magnitude
TP_sheet['L22'].value=Imp2_TP._reynolds(P2_TP).magnitude
TP_sheet['M23'].value=Imp2_TP._reynolds(P2_TP).magnitude/Imp2_FD._reynolds(P2_FD).magnitude
TP_sheet['L24'].value=Imp2_TP._phi(P2_TP).magnitude
TP_sheet['M25'].value=Imp2_TP._phi(P2_TP).magnitude/Imp2_FD._phi(P2_FD).magnitude
TP_sheet['L26'].value=Imp2_TP._psi(P2_TP).magnitude
TP_sheet['M27'].value=Imp2_TP._psi(P2_TP).magnitude/Imp2_FD._psi(P2_FD).magnitude
TP_sheet['L28'].value=P2_TP._head_pol_schultz().to('kJ/kg').magnitude
TP_sheet['M29'].value=P2_TP._head_pol_schultz().to('kJ/kg').magnitude/P2_FD._head_pol_schultz().to('kJ/kg').magnitude
TP_sheet['L30'].value=P2_TPconv._head_pol_schultz().to('kJ/kg').magnitude
TP_sheet['M31'].value=P2_TPconv._head_pol_schultz().to('kJ/kg').magnitude/P2_FD._head_pol_schultz().to('kJ/kg').magnitude
TP_sheet['L32'].value=P2_TP._power_calc().to('kW').magnitude
TP_sheet['M33'].value=P2_TP._power_calc().to('kW').magnitude/P2_FD._power_calc().to('kW').magnitude


if TP_sheet['C27'].value=='Yes':
    
    HL_FD=Q_(((suc2FD.T()+disch2FD.T()).to('degC').magnitude*0.8/2-25)*1.166*TP_sheet['D28'].value,'W')
    HL_TP=Q_(((suc2TP.T()+disch2TP.T()).to('degC').magnitude*0.8/2-25)*1.166*TP_sheet['D28'].value,'W')
    
    TP_sheet['L34'].value=(P2_TPconv._power_calc()-HL_TP+HL_FD).to('kW').magnitude
    TP_sheet['M35'].value=(P2_TPconv._power_calc()-HL_TP+HL_FD).to('kW').magnitude/(P2_FD._power_calc()).to('kW').magnitude
    
else:
    TP_sheet['L34'].value=P2_TPconv._power_calc().to('kW').magnitude
    TP_sheet['M35'].value=P2_TPconv._power_calc().to('kW').magnitude/P2_FD._power_calc().to('kW').magnitude


TP_sheet['L36'].value=P2_TP._eff_pol_schultz().magnitude