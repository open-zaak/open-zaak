#!/bin/sh

python src/manage.py dumpdata --indent 4 \
                zgw_consumers.Service \
                zgw_consumers.Certificate \
                zgw_consumers.NLXConfig \
                vng_api_common.JWTSecret \
                mozilla_django_oidc_db.OpenIDConnectConfig \
                drc_cmis.CMISConfig \
                authorizations.Applicatie \
                config.FeatureFlags \
                notifications.NotificationsConfig \
                notifications.Subscription \
                selectielijst.ReferentieLijstConfig \
                > config.json
