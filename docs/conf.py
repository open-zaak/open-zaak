# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------
import os
import sys

import django
from django.utils.translation import activate

sys.path.insert(0, os.path.abspath("../src"))
os.environ["LOG_REQUESTS"] = "false"

import openzaak  # noqa isort:skip
from openzaak.setup import setup_env  # noqa isort:skip

setup_env()
django.setup()

# from openzaak.setup import setup_env  # noqa isort:skip

# TODO: This needs to be enabled when we want to use autodoc to grab
# documentation from classes and functions. However, enabling django.setup()
# causes RTD to fail because GDAL is not present in the RTD environment.
# See: https://github.com/readthedocs/readthedocs-docker-images/issues/114#issuecomment-570566599
#
# setup_env()
# django.setup()

# -- Project information -----------------------------------------------------

project = "Open Zaak"
copyright = "2019 - 2020, Dimpact"
author = openzaak.__author__

# The full version, including alpha/beta/rc tags
release = openzaak.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.todo",
    "recommonmark",
    "sphinx_markdown_tables",
    "sphinx_tabs.tabs",
    "sphinx.ext.autodoc",
    "django_setup_configuration.documentation.setup_config_example",
    "django_setup_configuration.documentation.setup_config_usage",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# Also set the language to English for Django, to make sure that any translatable text
# is also shown in English (for instance the help texts for setup configuration examples)
activate("en")

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = [".rst", ".md"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_logo = "logo.svg"
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

todo_include_todos = True

linkcheck_ignore = [
    r"https?://.*\.gemeente.nl",
    r"http://localhost:\d+/",
    r"http://127\.0\.0\.1:\d+/",
    r"https://.*sentry\.openzaak\.nl.*",
    r"https://jwt.io.*",  # raises 500 errors when making requests with curl/requests
]

sphinx_tabs_valid_builders = ["linkcheck"]
