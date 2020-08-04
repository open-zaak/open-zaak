# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact
"""
Manage the Django settings configuration.

Configuration files are structured so that each target environment is
defined in this package - i.e. dev, docker, staging, production and ci.
Those are the 'final' settings files.

All settings modules in the includes/ package, are meant to support the
target environments:

* ``api.py``: contains the settings specific to the API (DRF, SWAGGER) and
  vng-api-common setting overrides.
* ``base.py``: literally the base settings for each environment. Most config
  that can be changed, is pulled from the environment. Override by setting the
  maching key in your .env file in the root of the project.
* ``environ.py``: contains helper(s) to pull settings from the environment
* ``local.py``: created from ``local_example.py``, NOT in version control. Use
  this to implement local overrides for your own dev environment.
* ``plugins.py``: essentially a hook to install/register plugins via Docker
  volume mounts. Chances are low you'll need this.
"""
