(engauge)=
# Getting performance points with Engauge Digitizer

In this guide we describe how to load a performance curve using the [Engauge Digitizer](https://markummitchell.github.io/engauge-digitizer/) application.

The first step is to copy the performance map. In the gif bellow we have and example of a head curve.

```{image} ../_static/img/step1.gif
```
After that we go to Engauge -> Edit -> Paste as New.

In the guide wizard we name the curves with the value of each speed:

```{image} ../_static/img/step2.gif
```

The next step is to select three axis points in the plot:

```{image} ../_static/img/step3.gif
```


Now we select a curve and mark the points using the 'Segment Fill Tool' or the 'Curve Point Tool'.

It is recommended to select at least 8 points for each curve to have a good interpolation.

```{image} ../_static/img/step4.gif
```

The last step is to configure the export format (Settings -> Export format).

Select 'Raws Xs and Ys' and 'One curve for each line'

After that go to File -> Export and save the .csv file as <curve-name>-head.csv.

Files should be saved with the following convention:
 - \<curve-name\>-head.csv
 - \<curve-name\>-eff.csv

```{image} ../_static/img/step5.gif
```

To the same steps for the efficiency curve.

After that we can load the data with the following code:

```{code-block} python3

import ccp
from pathlib import Path

data_dir = Path(...)

suc = ccp.State(
    p=Q_(4.08, "bar"),
    T=Q_(33.6, "degC"),
    fluid={
        "METHANE": 58.976,
        "ETHANE": 3.099,
        "PROPANE": 0.6,
        "N-BUTANE": 0.08,
        "I-BUTANE": 0.05,
        "N-PENTANE": 0.01,
        "I-PENTANE": 0.01,
        "NITROGEN": 0.55,
        "HYDROGEN SULFIDE": 0.02,
        "CARBON DIOXIDE": 36.605,
    },
)
imp = ccp.Impeller.load_from_engauge_csv(
    suc=suc,
    curve_name="lp-sec1-caso-a",
    curve_path=data_dir,
    b=Q_(5.7, "mm"),
    D=Q_(550, "mm"),
    head_units="kJ/kg",
    flow_units="m³/h",
    number_of_points=7,
)
```

In the case above in the data_dir directory we have the files `lp-sec1-caso-a-head.csv` and `lp-sec1-caso-a-eff.csv`.