#!/bin/bash
#
# NOTE: only run this uninstall script on Open Zaak 1.8.0+. On earlier versions,
# the auth-adfs-db dependency is still present and enabled, causing the tables to be
# re-created on container restarts.
#

cd /app
src/manage.py dbshell < /app/bin/uninstall_django_auth_adfs_db.sql
