# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2024 Dimpact
def preprocess_exclude_endpoints(endpoints, **kwargs):
    """
    preprocessing hook that filters out endpoints from OAS
    """
    exclude = "callbacks"
    return [
        (path, path_regex, method, callback)
        for path, path_regex, method, callback in endpoints
        if not path.split("/")[-1] == exclude
    ]
