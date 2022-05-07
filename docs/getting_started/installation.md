# Installation

To use ccp you will need python >= 3.6.

```{warning}
If you have python >= 3.9, before installing `ccp`, you will need to install `CoolProp` dev version with:

  `pip install -i https://test.pypi.org/simple/ CoolProp==6.4.2.dev0`

This is related to [this issue](https://github.com/CoolProp/CoolProp/issues/2119).
```

You can install `ccp` with:

```{code-block}
pip install ccp-performance
```

To run `ccp` you need to have `REFPROP` in your computer, and an environment variable called `RPPREFIX` pointing to the `REFPROP` path.

If you have set a `RPPREFIX` environment variable set, or maybe want to point to a different path, you can do that before importing ccp with:

```{code-block} python
import os
os.environ['RPPREFIX'] = <path/to/REFPROP/folder>

import ccp
```
