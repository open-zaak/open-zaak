#!/bin/bash
#
# Start the 'VM'.
#
# Fixes the file permissions for the mounted .ssh/authorized keys so that
# passwordless ssh is possible, and then start up the SSHD daemon.
#

chown root:root -R ~/.ssh/

/usr/sbin/sshd -D
