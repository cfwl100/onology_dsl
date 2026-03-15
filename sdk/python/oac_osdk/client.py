from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib import request


@dataclass
class OacClient:
    """Python OSDK: 面向 OAC 服务的轻量客户端。"""

    endpoint: str
    timeout: float = 5.0

    def validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("validate", payload)

    def explain(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("explain", payload)

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("execute", payload)

    def _post(self, mode: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.endpoint.rstrip('/')}/oac/{mode}"
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url=url, method="POST", data=data, headers={"Content-Type": "application/json"})
        with request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
