# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Settings for plugins
"""
import os
import sys
from importlib import import_module

__all__ = ["PLUGIN_INSTALLED_APPS"]

_PLUGINS = os.getenv("PLUGINS", "")
PLUGINS = _PLUGINS.split(",") if _PLUGINS else []

_PLUGIN_DIRS = os.getenv("PLUGIN_DIRS", "")
PLUGIN_DIRS = _PLUGIN_DIRS.split(",") if _PLUGIN_DIRS else []

# set up the python path for plugins
for path in PLUGIN_DIRS:
    if path not in sys.path:
        sys.path.append(path)

PLUGIN_INSTALLED_APPS = []

for plugin in PLUGINS:
    try:
        import_module(plugin)
    except ImportError as exc:
        msg = (
            f"{exc.args[0]}. \nTried the following python path: {':'.join(sys.path)}. \n"
            "Try specifying the PLUGIN_DIRS environment variable."
        )
        raise ImportError(msg)

    PLUGIN_INSTALLED_APPS.append(plugin)
