import xlwings as xw
import ccp
from ccp import State, Q_
import numpy as np

wb = xw.Book('Modelo_1section.xlsx')  # connect to an existing file in the current working directory

FD_sheet=wb.sheets['DataSheet']
TP_sheet=wb.sheets['Test Procedure Data']

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