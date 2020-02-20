# <img src="docs/ccp.PNG" alt="drawing" width="40"/> Centrifugal Compressor Performance

Biblioteca para cálculo de performance de compressores centrífugos em python.

---

Para avaliação dos resultados pode ser utilizada aplicação web que pode
ser disponibilizada através de recurso de núvem.

# Guia básico

Definição de estados termodinâmicos:

```python
import ccp
# ccp uses pint to handle units. Q_ is a pint quantity.
# If a pint quantity is not provided, SI units are assumed.
from ccp import Q_

# Define the fluid as a dictionary:
fluid = dict(methane=0.69945,
             ethane=0.09729,
             propane=0.0557,
             nbutane=0.0178,
             ibutane=0.0102,
             npentane=0.0039,
             ipentane=0.0036,
             nhexane=0.0018,
             n2=0.0149,
             co2=0.09259,
             h2s=0.00017,
             water=0.002)
             
# Define suction state:
suc = ccp.State.define(p=Q_(1.6995, 'MPa'), T=311.55, fluid=fluid)

# Create performance point(s):
p0 = ccp.Point(suc=suc, flow_v=Q_(6501.67, 'm**3/h'), speed=Q_(11145, 'RPM'),
           head=Q_(179.275, 'kJ/kg'), eff=0.826357)
p1 = ccp.Point(suc=suc, flow_v=Q_(7016.72, 'm**3/h'), speed=Q_(11145, 'RPM'),
           head=Q_(173.057, 'kJ/kg'), eff=0.834625)

# Create an impeller that will hold and convert curves.
imp = ccp.Impeller([p0, p1], b=Q_(28.5, 'mm'), D=Q_(365, 'mm'))

# Define new suction state
new_suc = ccp.State.define(p=Q_(0.2, 'MPa'), T=301.58,
                           fluid='nitrogen')

# setting a new suction
imp.new_suc = new_suc

# after the new suctions is created, a new impeller is available with the 
# converted curves
imp.new.curves
```

# Instalação

Para a instalação é necessário o pip 19.1.1. 
Para atualizar o pip utilizar o comando:

`pip install --upgrade pip` 

Para instalar o ccp:

`pip install git+ssh://git@gitlab.cenpes.petrobras.com.br/equipamentos-dinamicos/ccp.git`
