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

## AI assistance

ccp ships with an agent skill — a set of concise compressor-performance
recipes in the [Agent Skills](https://agentskills.io) open standard that
teaches AI coding agents how to build states, points and impellers and run
performance analyses with ccp. After installing ccp, install the skill with:

```{code-block}
ccp-install-skill
```

This detects the AI coding agents on your machine (Claude Code, GitHub
Copilot, Cursor, Codex) and copies the skill to each one's personal skills
directory. Useful variations:

```{code-block}
ccp-install-skill --project          # install into the current project (shared with your team)
ccp-install-skill --agent claude     # install for a specific agent only
ccp-install-skill --uninstall        # remove the skill
```

Once installed, the skill activates automatically whenever you ask your agent
about centrifugal compressor performance with ccp — for example, "create an
impeller from these test points and convert the curves to the new suction
condition". In Claude Code you can also invoke it explicitly with the `/ccp`
slash command.

The skill is a snapshot of the recipes for the installed ccp version, so
re-run `ccp-install-skill` after upgrading ccp.

## REFPROP

To run `ccp` you need to have `REFPROP` in your computer, and an environment variable called `RPPREFIX` pointing to the `REFPROP` path.

If you have not set a `RPPREFIX` environment variable, you can do the following before importing ccp:

```{code-block} python
import os
os.environ['RPPREFIX'] = <path/to/REFPROP/folder>

import ccp
```
