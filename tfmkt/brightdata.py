import json
import logging
import os
from typing import Any, AsyncIterator

from crawlee.http_clients import HttpClient, HttpCrawlingResult, ImpitHttpClient


logger = logging.getLogger(__name__)

BRIGHTDATA_ENDPOINT = 'https://api.brightdata.com/request'
BLOCKED_STATUS_CODES = {202, 403, 405, 429}
DATADOME_MARKERS = (
    b'processbrowsercheck',
    b'human verification',
    b'captcha-delivery',
    b'datadome',
    b'enable javascript and then reload',
)


class _MemoryResponse:
    """Replayable HTTP response backed by an in-memory body."""

    def __init__(self, response: Any, body: bytes) -> None:
        self._http_version = response.http_version
        self._status_code = response.status_code
        self._headers = response.headers
        self._body = body

    @property
    def http_version(self) -> str:
        return self._http_version

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def headers(self) -> Any:
        return self._headers

    async def read(self) -> bytes:
        return self._body

    async def read_stream(self) -> AsyncIterator[bytes]:
        yield self._body


def looks_blocked(status_code: int, body: bytes) -> bool:
    """Return whether a response matches a measured DataDome block signature."""
    if status_code in BLOCKED_STATUS_CODES:
        return True

    normalized_body = body.lower()
    return any(marker in normalized_body for marker in DATADOME_MARKERS)


class WebUnlockerHttpClient(HttpClient):
    """Try requests directly, falling back to Bright Data Web Unlocker on blocks."""

    def __init__(self, inner: HttpClient, api_key: str, zone: str) -> None:
        super().__init__()
        self._inner = inner
        self._api_key = api_key
        self._zone = zone
        self.attempted = 0
        self.unlocked = 0

    async def crawl(
        self,
        request: Any,
        *,
        session: Any = None,
        proxy_info: Any = None,
        statistics: Any = None,
        timeout: Any = None,
    ) -> HttpCrawlingResult:
        self.attempted += 1
        direct_result = await self._inner.crawl(
            request,
            session=session,
            proxy_info=proxy_info,
            statistics=None,
            timeout=timeout,
        )
        response = direct_result.http_response
        body = await response.read()

        if looks_blocked(response.status_code, body):
            self.unlocked += 1
            response = await self._inner.send_request(
                BRIGHTDATA_ENDPOINT,
                method='POST',
                headers={
                    'Authorization': f'Bearer {self._api_key}',
                    'Content-Type': 'application/json',
                },
                payload=json.dumps({
                    'zone': self._zone,
                    'url': request.url,
                    'format': 'raw',
                }).encode('utf-8'),
                session=session,
                timeout=timeout,
            )
            body = await response.read()
            request.loaded_url = request.url

        if statistics:
            statistics.register_status_code(response.status_code)

        return HttpCrawlingResult(http_response=_MemoryResponse(response, body))

    async def send_request(self, url: str, **kwargs: Any) -> Any:
        return await self._inner.send_request(url, **kwargs)

    def stream(self, url: str, **kwargs: Any) -> Any:
        return self._inner.stream(url, **kwargs)

    async def cleanup(self) -> None:
        logger.info(
            'Bright Data Web Unlocker summary: attempted=%d unlocked=%d',
            self.attempted,
            self.unlocked,
        )
        await self._inner.cleanup()


def build_http_client() -> HttpClient | None:
    """Build the fallback client when Bright Data credentials are configured."""
    api_key = os.environ.get('BRIGHTDATA_API_KEY')
    if not api_key:
        return None

    zone = os.environ.get('BRIGHTDATA_ZONE') or 'web_unlocker2'
    return WebUnlockerHttpClient(ImpitHttpClient(), api_key, zone)
