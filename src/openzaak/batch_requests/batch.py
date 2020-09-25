from concurrent.futures import ThreadPoolExecutor as parallel
from dataclasses import dataclass
from typing import List

from rest_framework.request import Request
from rest_framework.response import Response


@dataclass
class BatchRequest:
    method: str
    url: str


def batch_requests(parent: Request, requests: List[BatchRequest]) -> List[Response]:
    import bpdb

    bpdb.set_trace()
