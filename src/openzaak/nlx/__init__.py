import requests
from nlx_url_rewriter.rewriter import Rewriter


def fetcher(url: str, *args, **kwargs):
    """
    Fetch the URL using requests, trying configured NLX url rewrites first.
    """
    rewriter = Rewriter()
    _urls = [url]
    rewriter.forwards(_urls)
    url = _urls[0]
    return requests.get(url, *args, **kwargs)
