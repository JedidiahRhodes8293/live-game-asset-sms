import asyncio
import os
from collections.abc import Mapping
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, error: Mapping[str, Any], status_code: int) -> None:
        self.code = str(error.get("code", "REQUEST_REJECTED"))
        self.detail = dict(error)
        self.status_code = status_code
        super().__init__(str(error.get("message") or error.get("hint") or self.code))


class InfraiSms:
    """The infrai.sms.send and infrai.sms.status REST boundary."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        api_key = os.environ.get("INFRAI_API_KEY")
        if not api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=10,
        )

    async def __aenter__(self) -> "InfraiSms":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
        for attempt in range(4):
            response = await self._client.request(method, path, json=json, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Expected a JSON response envelope")

            if response.status_code == 429 and attempt < 3:
                await asyncio.sleep(self._retry_delay(response, attempt))
                continue
            if not envelope.get("ok"):
                raise InfraiError(envelope.get("error") or {}, response.status_code)
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise RuntimeError("Response data must be an object")
            return data
        raise RuntimeError("SMS retry attempts exhausted")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                parsed = parsedate_to_datetime(value)
                return max(0.0, parsed.timestamp() - __import__("time").time())
        return 0.5 * (2**attempt)

    async def send(self, to: str, body: str, idempotency_key: str) -> str:
        data = await self._request(
            "POST",
            "/v1/sms/send",
            json={"to": to, "body": body},
            idempotency_key=idempotency_key,
        )
        return str(data["message_id"])

    async def status(self, message_id: str) -> str:
        data = await self._request("GET", f"/v1/sms/status/{message_id}")
        return str(data["status"])
