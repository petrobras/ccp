import os
import re
import sys

from setuptools import setup, find_packages


def read(path, encoding="utf-8"):
    path = os.path.join(os.path.dirname(__file__), path)
    with open(path, encoding=encoding) as fp:
        return fp.read()


def version(path):
    """Obtain the package version from a python file e.g. pkg/__init__.py
    See <https://packaging.python.org/en/latest/single_source_version.html>.
    """
    version_file = read(path)
    version_match = re.search(
        r"""^__version__ = ['"]([^'"]*)['"]""", version_file, re.M
    )
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


DESCRIPTION = "Centrifugal Compressor Performance calculation."
VERSION = version("ccp/__init__.py")

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

with open("requirements.txt") as f:
    REQUIRES = f.read().splitlines()
if sys.platform in ["win32", "cygwin", "msys"]:
    REQUIRES.append("xlwings")

setup(
    name="ccp-performance",
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Raphael Timbó",
    author_email="raphaelts@petrobras.com.br",
    project_urls={
        "Documentation": "https://ccp-centrifugal-compressor-performance.readthedocs.io/en/stable/",
        "Bug Tracker": "https://github.com/petrobras/ccp/issues",
        "Source Code": "https://github.com/petrobras/ccp",
    },
    package_data={"ccp.config": ["new_units.txt"], "ccp.tests.data": ["*"]},
    python_requires=">=3.6",
    install_requires=REQUIRES,
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "coverage",
            "codecov",
            "sphinx",
            "nbsphinx",
            "numpydoc",
            "sphinxcontrib-bibtex",
            "black",
            "isort",
            "myst-nb",
            "linkify-it-py",
            "sphinx-book-theme",
            "sphinx-panels",
            "sphinx-copybutton",
            "sphinx-rtd-theme",
        ],
    },
    py_modules=[],
    license="Apache License 2.0",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Operating System :: OS Independent",
    ],
)
