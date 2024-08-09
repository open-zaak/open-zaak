#!/bin/bash
#
# Dump the instance/runtime configuration.
#
# The resulting dump can be restored using the `loaddata` management command. The
# certificate files (certificates + private keys) are dumped into a zip file.
#
# Usage:
#
#   ./bin/dump_configuration.sh
#
# The files will be written to a temporary directory - the script emits the location of
# that directory. You can customize where the directory will be created through the
# `$TMPDIR` environment variable (defaults to /tmp).
#
# Run this from the root of the project.

output_dir=`mktemp -d`

# Dump the certificates to file
src/manage.py dump_certs --filename "$output_dir/certificates.zip"

# Dump the DB content in a fixture file
src/manage.py dumpdata \
    --indent 4 \
    --natural-foreign \
    --natural-primary \
    -o "$output_dir/config.json" \
    zgw_consumers.Service \
    zgw_consumers.Certificate \
    zgw_consumers.NLXConfig \
    vng_api_common.JWTSecret \
    mozilla_django_oidc_db.OpenIDConnectConfig \
    drc_cmis.CMISConfig \
    authorizations.Applicatie \
    autorisaties.CatalogusAutorisatie \
    config.FeatureFlags \
    notifications.NotificationsConfig \
    notifications.Subscription \
    selectielijst.ReferentieLijstConfig

echo "The configuration dump can be found in: $output_dir"
