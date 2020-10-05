from concurrent.futures import ThreadPoolExecutor as parallel
from copy import deepcopy
from dataclasses import dataclass
from typing import List

from rest_framework.request import Request
from rest_framework.response import Response


@dataclass
class BatchRequest:
    method: str
    url: str


def batch_requests(parent: Request, requests: List[BatchRequest]) -> List[Response]:
    responses = []
    for request in requests:
        parent_copy = deepcopy(parent)
        response = handle_batch_request(parent_copy, request)
        responses.append(response)
    return responses


def handle_batch_request(parent: Request, request: BatchRequest) -> Response:
    import bpdb

    bpdb.set_trace()
