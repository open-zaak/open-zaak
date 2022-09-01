# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
import functools
import socket


@functools.cache
def can_connect(hostname: str):
    # adapted from https://stackoverflow.com/a/28752285
    hostname, port = hostname.split(":")
    try:
        host = socket.gethostbyname(hostname)
        s = socket.create_connection((host, int(port)), 2)
        s.close()
        return True
    except Exception:
        return False
