# Installation

To use ccp you will need python >= 3.6.

You can install `ccp` with:

```{code-block}
pip install ccp-performance
```

To run `ccp` you need to have `REFPROP` in your computer, and an environment variable called `RPPREFIX` pointing to the `REFPROP` path.

If you have not set a `RPPREFIX` environment variable set, you can do the following before importing ccp:

```{code-block} python
import os
os.environ['RPPREFIX'] = <path/to/REFPROP/folder>

import ccp
```
