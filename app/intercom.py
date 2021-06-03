import asyncio
import logging
from typing import Any, Dict, Literal, Protocol

import httpx

logger = logging.getLogger(__name__)


class IntercomClient(Protocol):
    async def send(
        self, method: Literal["POST"], path: str, data: Dict[str, Any]
    ) -> None:
        """Send a message to Intercom; return after Intercom acknowledges it.

        Follow retry logic laid out in README.md.
        """

    async def close(self) -> None:
        """Close resources associated with this client.

        Maybe log, but never error.
        """


class IntercomMockClient:
    async def send(
        self, method: Literal["POST"], path: str, data: Dict[str, Any]
    ) -> None:
        """Log and pretend we sent a message to Intercom."""
        logger.info("(mocked) %s %s %r", method, path, data)

    async def close(self) -> None:
        """Pretend we closed an HTTP connection."""
        pass


class IntercomRestClient:
    def __init__(self, api_token):
        self.client = httpx.AsyncClient(
            base_url="https://api.intercom.io",
            headers={
                "Authorization": "Bearer " + api_token,
                "Accept": "application/json",
            },
        )

    async def send(
        self, method: Literal["POST"], path: str, data: Dict[str, Any]
    ) -> None:
        """Send a message to Intercom; return after Intercom acknowledges it.

        Follow retry logic laid out in README.md.
        """

        logger.info("%s %s", method, path)  # data anonymized for production
        last_response_was_http_50x = False

        while True:
            try:
                response = await self.client.request(method, path, json=data)
            except httpx.RequestError:
                logger.exception("Failed to reach Intercom; will retry")
                await asyncio.sleep(1)  # prevent spamming logs
                last_response_was_http_50x = False
                continue  # retry

            if response.status_code == 429:
                # Intercom permits new requests every 10s
                # https://developers.intercom.com/intercom-api-reference/reference#section-when-does-the-amount-of-requests-reset-
                logger.warning("HTTP 429 Too Many Requests; waiting 10s")
                await asyncio.sleep(10)
                last_response_was_http_50x = False
                continue  # retry
            elif response.status_code == 404:
                logger.warning("HTTP 404; treating this as OK")
                return
            elif response.status_code >= 500 and not last_response_was_http_50x:
                logger.warning("HTTP %d; retrying", response.status_code)
                await asyncio.sleep(1)  # prevent spamming logs
                last_response_was_http_50x = True
                continue  # retry
            elif response.status_code >= 400:
                logger.error(
                    "HTTP %d; please investigate! Headers: %r; Body: %r",
                    response.status_code,
                    response.headers,
                    response.content,
                )
                return
            else:
                return  # Intercom said OK

    async def close(self) -> None:
        """Close resources associated with this client.

        Maybe log, but never error.
        """
        try:
            await self.client.close()
        except Exception:
            logger.exception("Failed to close httpx.AsyncClient")
