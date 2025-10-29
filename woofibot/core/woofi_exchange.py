"""
WOOFi / Orderly live exchange client (conservative test-net default).

• Requires env vars WOOFI_API_KEY and WOOFI_API_SECRET.
• Defaults to test-net base.  Set testnet=False or base_url to switch to main-net.
• Idempotency keys + back-off on 429/503.
• Exposes place_order / cancel_order / get_position / get_account.
"""

from __future__ import annotations

import os
import time
import hmac
import hashlib
import uuid
import json
import logging
from typing import Dict, Any, Optional

import requests

log = logging.getLogger("woofi_exchange")
log.setLevel(logging.INFO)

DEFAULT_TESTNET_BASE = "https://testnet-api-evm.orderly.org"
DEFAULT_MAINNET_BASE = "https://api-evm.orderly.org"


class WOOFiExchange:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 2,
        backoff: float = 0.5,
        testnet: bool = True,
    ) -> None:
        self.api_key = api_key or os.getenv("WOOFI_API_KEY")
        self.api_secret = api_secret or os.getenv("WOOFI_API_SECRET")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.session = requests.Session()
        self.base_url = base_url or (DEFAULT_TESTNET_BASE if testnet else DEFAULT_MAINNET_BASE)
        self.default_headers = {"Content-Type": "application/json"}
        if not (self.api_key and self.api_secret):
            log.warning("Live exchange instantiated without credentials; requests will fail until keys are set.")

    # ---------------------------------------------------------------------
    # Signing helpers (adapt if Orderly changes spec)
    # ---------------------------------------------------------------------
    def _sign(self, method: str, path: str, body: str, ts: str) -> str:
        payload = f"{ts}{method.upper()}{path}{body}"
        return hmac.new(self.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    def _headers(self, method: str, path: str, body: Dict[str, Any] | None) -> Dict[str, str]:
        ts = str(int(time.time() * 1000))
        body_str = json.dumps(body, separators=(",", ":"), sort_keys=True) if body else ""
        sig = self._sign(method, path, body_str, ts) if self.api_secret else ""
        h = {
            **self.default_headers,
            "X-API-KEY": self.api_key or "",
            "X-API-TIMESTAMP": ts,
            "X-API-SIGN": sig,
            "Idempotency-Key": str(uuid.uuid4()),
        }
        return h

    def _request(self, method: str, path: str, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        attempt = 0
        while attempt <= self.max_retries:
            try:
                resp = self.session.request(
                    method,
                    url,
                    json=body or {},
                    headers=self._headers(method, path, body),
                    timeout=self.timeout,
                )
                if resp.status_code in (200, 201, 202):
                    return resp.json()
                if resp.status_code in (429, 503, 504):
                    wait = self.backoff * (2 ** attempt)
                    log.warning("%s %s returned %s, retry in %.2fs", method, path, resp.status_code, wait)
                    time.sleep(wait)
                    attempt += 1
                    continue
                log.error("Error %s: %s", resp.status_code, resp.text)
                break
            except requests.RequestException as exc:
                wait = self.backoff * (2 ** attempt)
                log.warning("Request error %s %s: %s (retry %.2fs)", method, path, exc, wait)
                time.sleep(wait)
                attempt += 1
        return {"success": False, "error": f"Failed after {self.max_retries} retries"}

    # ------------------------------------------------------------------
    # Public minimal API wrappers
    # ------------------------------------------------------------------
    def place_order(
        self,
        symbol: str,
        side: str,
        qty_quote: float,
        price: float | None = None,
        order_type: str = "market",
        client_order_id: str | None = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "qty_quote": float(qty_quote),
        }
        if price is not None:
            body["price"] = float(price)
        if client_order_id:
            body["client_order_id"] = client_order_id
        return self._request("POST", "/v1/private/order/place", body)

    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        body = {"symbol": symbol, "order_id": order_id}
        return self._request("POST", "/v1/private/order/cancel", body)

    def get_position(self, symbol: str) -> Dict[str, Any]:
        return self._request("GET", f"/v1/private/position?symbol={symbol}")

    def get_account(self) -> Dict[str, Any]:
        return self._request("GET", "/v1/private/account")

    # Convenience adapter used by existing bot code
    def place_order_from_dict(self, od: Dict[str, Any]) -> Dict[str, Any]:
        return self.place_order(
            symbol=od["symbol"],
            side=od.get("side", "buy"),
            qty_quote=float(od.get("qty_quote", 0.0)),
            price=od.get("price"),
            order_type=od.get("type", "market"),
            client_order_id=od.get("meta", {}).get("client_id"),
        )
