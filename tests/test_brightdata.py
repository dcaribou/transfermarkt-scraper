import asyncio
import json

from crawlee import Request
from crawlee.http_clients import HttpClient, HttpCrawlingResult

from tfmkt.brightdata import (
    BRIGHTDATA_ENDPOINT,
    WebUnlockerHttpClient,
    build_http_client,
    looks_blocked,
)


class FakeResponse:
    http_version = 'HTTP/1.1'

    def __init__(self, status_code, body):
        self.status_code = status_code
        self.headers = {'content-type': 'text/html'}
        self.body = body

    async def read(self):
        return self.body

    async def read_stream(self):
        yield self.body


class FakeHttpClient(HttpClient):
    def __init__(self, direct_response, unlocked_response):
        super().__init__()
        self.direct_response = direct_response
        self.unlocked_response = unlocked_response
        self.unlock_call = None
        self.cleaned_up = False

    async def crawl(self, request, **kwargs):
        request.loaded_url = request.url
        return HttpCrawlingResult(http_response=self.direct_response)

    async def send_request(self, url, **kwargs):
        self.unlock_call = (url, kwargs)
        return self.unlocked_response

    def stream(self, url, **kwargs):
        raise NotImplementedError

    async def cleanup(self):
        self.cleaned_up = True


class FakeStatistics:
    def __init__(self):
        self.status_codes = []

    def register_status_code(self, status_code):
        self.status_codes.append(status_code)


def test_looks_blocked_detects_statuses_and_datadome_markers():
    for status_code in (202, 403, 405, 429):
        assert looks_blocked(status_code, b'')

    assert looks_blocked(200, b'<title>Human Verification</title>')
    assert looks_blocked(200, b'<script src="https://captcha-delivery.com/captcha.js">')
    assert looks_blocked(200, b'Enable JavaScript and then reload the page.')
    assert not looks_blocked(200, b'<html><title>Transfermarkt</title></html>')


def test_blocked_crawl_retries_through_web_unlocker():
    inner = FakeHttpClient(
        FakeResponse(405, b'Human Verification'),
        FakeResponse(200, b'<html>unlocked</html>'),
    )
    client = WebUnlockerHttpClient(inner, 'secret', 'test-zone')
    request = Request.from_url('https://www.transfermarkt.co.uk/example')
    statistics = FakeStatistics()

    result = asyncio.run(client.crawl(request, statistics=statistics))

    assert asyncio.run(result.http_response.read()) == b'<html>unlocked</html>'
    assert inner.unlock_call[0] == BRIGHTDATA_ENDPOINT
    kwargs = inner.unlock_call[1]
    assert kwargs['headers']['Authorization'] == 'Bearer secret'
    assert json.loads(kwargs['payload']) == {
        'zone': 'test-zone',
        'url': request.url,
        'format': 'raw',
    }
    assert request.loaded_url == request.url
    assert statistics.status_codes == [200]
    assert client.attempted == 1
    assert client.unlocked == 1


def test_unblocked_crawl_returns_replayable_direct_response():
    inner = FakeHttpClient(FakeResponse(200, b'direct'), FakeResponse(200, b'unused'))
    client = WebUnlockerHttpClient(inner, 'secret', 'test-zone')

    result = asyncio.run(client.crawl(Request.from_url('https://example.com')))

    assert asyncio.run(result.http_response.read()) == b'direct'
    assert asyncio.run(result.http_response.read()) == b'direct'
    assert inner.unlock_call is None
    assert client.attempted == 1
    assert client.unlocked == 0


def test_build_http_client_requires_non_empty_key(monkeypatch):
    monkeypatch.delenv('BRIGHTDATA_API_KEY', raising=False)
    assert build_http_client() is None

    monkeypatch.setenv('BRIGHTDATA_API_KEY', '')
    assert build_http_client() is None

    monkeypatch.setenv('BRIGHTDATA_API_KEY', 'secret')
    monkeypatch.setenv('BRIGHTDATA_ZONE', 'custom-zone')
    client = build_http_client()
    assert isinstance(client, WebUnlockerHttpClient)
    assert client._zone == 'custom-zone'
