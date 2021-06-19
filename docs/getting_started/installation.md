# Installation

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
