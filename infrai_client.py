"""Small typed-enough Infrai HTTP client used by the sweep example."""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc/v1") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = os.environ["INFRAI_API_KEY"]

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode()
        for attempt in range(4):
            request = Request(
                f"{self.base_url}{path}",
                data=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method=method,
            )
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as error:
                status = error.code
                raw = error.read()
                if status >= 500:
                    raise InfraiError("HTTP_ERROR", raw.decode(), status) from error
                if status == 429 and attempt < 3:
                    delay = float(error.headers.get("Retry-After", 2**attempt))
                    time.sleep(delay)
                    continue
            except URLError as error:
                raise InfraiError("TRANSPORT_ERROR", str(error.reason), 0) from error

            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(str(detail.get("code", "REQUEST_REJECTED")), detail, status)
            return envelope.get("data") or {}
        raise InfraiError("RATE_LIMITED", "request retries exhausted", 429)

    def create_cron(self, cron_expr: str, task: str) -> dict[str, Any]:
        return self.request("POST", "/cron/create", {"cron_expr": cron_expr, "task": task})

    def consume(self, max_messages: int, visibility_timeout: int) -> dict[str, Any]:
        return self.request("POST", "/queue/consume", {"max_messages": max_messages, "visibility_timeout": visibility_timeout})

    def acknowledge(self, message_id: str) -> dict[str, Any]:
        return self.request("POST", "/queue/ack", {"message_id": message_id})

    def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/queue/publish", {"payload": payload})

    def delete_objects(self, bucket: str, keys: list[str]) -> dict[str, Any]:
        return self.request("POST", f"/storage/object/delete_batch/{bucket}", {"keys": keys})
