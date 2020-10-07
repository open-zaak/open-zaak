import json
from concurrent.futures import ThreadPoolExecutor as parallel
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

from django.core.handlers.wsgi import WSGIRequest
from django.urls import get_resolver

from rest_framework.request import Request
from rest_framework.response import Response


@dataclass
class BatchRequest:
    method: str
    url: str


def batch_requests(parent: Request, requests: List[BatchRequest]) -> List[Response]:
    with parallel() as executor:
        responses = executor.map(
            lambda req: handle_batch_request(parent, req), requests
        )
    return list(responses)


def handle_batch_request(parent: Request, request: BatchRequest) -> Response:
    request_path = urlparse(request.url).path

    # copy the underlying environ to clone the request, and change the method + path
    new_environ = {
        **parent.environ,
        "REQUEST_METHOD": request.method,
        "PATH_INFO": request_path,
    }
    cloned_request = WSGIRequest(new_environ)
    cloned_request.jwt_auth = parent.jwt_auth

    # run the URL resolver
    resolver = get_resolver()
    resolver_match = resolver.resolve(cloned_request.path_info)
    callback, callback_args, callback_kwargs = resolver_match
    cloned_request.resolver_match = resolver_match

    # execute the view
    response = callback(cloned_request, *callback_args, **callback_kwargs)

    # render the response
    if hasattr(response, "render") and callable(response.render):
        response = response.render()

    # convert post-processed data back
    assert response["Content-Type"].startswith("application/json")
    response.data = json.loads(response.content)

    return response
