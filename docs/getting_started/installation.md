# Installation

To use ccp you will need python >= 3.6.

## Core Library

You can install the core `ccp` library with:

```{code-block}
pip install ccp-performance
```

## Optional Dependencies

### Streamlit Web Application

To use the Streamlit web application interface, install with the `app` extra:

```{code-block}
pip install ccp-performance[app]
```

### Development Dependencies

For development work, install with the `dev` extra:

```{code-block}
pip install ccp-performance[dev]
```

You can also combine extras:

```{code-block}
pip install ccp-performance[dev,app]
```

To run `ccp` you need to have `REFPROP` in your computer, and an environment variable called `RPPREFIX` pointing to the `REFPROP` path.

If you have not set a `RPPREFIX` environment variable, you can do the following before importing ccp:

```{code-block} python
import os
os.environ['RPPREFIX'] = <path/to/REFPROP/folder>

import ccp
```
