from __future__ import annotations
import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Claim

DEFAULT_KEY_ID = "rzp_test_TYNGpLx84Zs6lw"
DEFAULT_KEY_SECRET = "x4kCvSjLPYn6GFVojNnkktur"
RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


def _read_env_file() -> dict[str, str]:
    env_vars: dict[str, str] = {}
    current = Path(__file__).resolve()
    for parent in [current.parents[2], current.parents[3]]:
        env_path = parent / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip("'\"")
            except Exception:
                pass
    return env_vars


class RazorpayAdapter:
    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
        base_url: str = RAZORPAY_API_BASE,
        timeout: float = 10.0,
    ):
        file_env = _read_env_file()
        if key_id is not None:
            self.key_id = key_id
        else:
            self.key_id = (
                os.getenv("RAZORPAY_KEY_ID")
                or file_env.get("RAZORPAY_KEY_ID")
                or DEFAULT_KEY_ID
            )

        if key_secret is not None:
            self.key_secret = key_secret
        else:
            self.key_secret = (
                os.getenv("RAZORPAY_KEY_SECRET")
                or file_env.get("RAZORPAY_KEY_SECRET")
                or DEFAULT_KEY_SECRET
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def status(self) -> dict:
        return {
            "provider": "razorpay_test",
            "configured": self.is_configured(),
            "key_id": self.key_id if self.key_id else None,
            "api_endpoint": f"{self.base_url}/orders",
            "mode": "test",
        }

    def execute_mandate(self, claim: Claim) -> dict:
        if not self.is_configured():
            return {
                "status": "SIMULATED — no live Razorpay test credentials",
                "live": False,
            }

        url = f"{self.base_url}/orders"
        amount_paise = int(round(claim.amount * 100))
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": str(claim.request_id)[:40],
            "notes": {
                "protocol": str(claim.protocol),
                "merchant": str(claim.merchant),
                "agent_id": str(claim.agent_id),
                "request_id": str(claim.request_id),
                "operation": str(claim.operation),
                "mandate_state": str(claim.mandate_state),
                "max_amount": str(claim.max_amount),
            },
        }

        auth_str = f"{self.key_id}:{self.key_secret}"
        auth_header = "Basic " + base64.b64encode(auth_str.encode("utf-8")).decode("ascii")

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
                "User-Agent": "MandateWarrant-RazorpayAdapter/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                order = json.loads(resp.read().decode("utf-8"))
                return {
                    "status": "EXECUTED",
                    "live": True,
                    "provider": "razorpay_test",
                    "order_id": order.get("id"),
                    "amount": order.get("amount"),
                    "amount_paid": order.get("amount_paid", 0),
                    "amount_due": order.get("amount_due", order.get("amount")),
                    "currency": order.get("currency", "INR"),
                    "receipt": order.get("receipt", claim.request_id),
                    "order_status": order.get("status", "created"),
                    "created_at": order.get("created_at"),
                    "notes": order.get("notes", {}),
                }
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                msg = err_json.get("error", {}).get("description") or err_body
            except Exception:
                msg = err_body
            return {
                "status": "EXECUTION_FAILED",
                "live": True,
                "provider": "razorpay_test",
                "error": f"HTTP {err.code}: {msg}",
            }
        except Exception as exc:
            return {
                "status": "EXECUTION_FAILED",
                "live": True,
                "provider": "razorpay_test",
                "error": str(exc),
            }
