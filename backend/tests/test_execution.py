from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import tempfile
from unittest.mock import MagicMock

from backend.app.execution.adapter import RazorpayAdapter
from backend.app.models import Claim
from backend.app.service import WardenService


def make_claim(**overrides) -> Claim:
    values = {
        "request_id": "test-req-001",
        "protocol": "upi_autopay",
        "operation": "modify",
        "merchant": "Cloudflow",
        "amount": 8000,
        "max_amount": 10000,
        "agent_id": "agent-17",
        "delegation_active": True,
        "mandate_state": "active",
        "notice_hours": 24,
        "merchant_match": True,
        "operations_last_hour": 1,
        "request_nonce": "nonce-001",
        "replayed": False,
    }
    values.update(overrides)
    return Claim(**values)


def test_adapter_configuration():
    adapter = RazorpayAdapter(key_id="rzp_test_testkey", key_secret="testsecret")
    assert adapter.is_configured() is True
    status = adapter.status()
    assert status["configured"] is True
    assert status["key_id"] == "rzp_test_testkey"
    assert status["provider"] == "razorpay_test"


def test_adapter_unconfigured():
    adapter = RazorpayAdapter(key_id="", key_secret="")
    assert adapter.is_configured() is False
    res = adapter.execute_mandate(make_claim())
    assert res["live"] is False
    assert "SIMULATED" in res["status"]


def test_blocked_claim_never_executes_adapter():
    with tempfile.TemporaryDirectory() as folder:
        mock_adapter = MagicMock()
        service = WardenService(str(Path(folder) / "audit.db"), adapter=mock_adapter)
        service_mod = __import__(
            "backend.app.service", fromlist=["normalize", "match_context"]
        )
        orig_norm = service_mod.normalize
        orig_match = service_mod.match_context
        try:
            # Blocked by merchant mismatch
            service_mod.normalize = lambda p: (
                make_claim(**p),
                {"extraction_confidence": 0.95, "provider": "test-double"},
            )
            service_mod.match_context = lambda c: {
                "merchant_match": False,
                "match_confidence": 0.9,
                "match_reason": "mismatch",
                "provider": "test-double",
            }
            res = service.evaluate(make_claim(merchant_match=False).payload())
        finally:
            service_mod.normalize = orig_norm
            service_mod.match_context = orig_match

        assert res["decision"]["decision"] == "blocked"
        assert "BLOCKED" in res["execution"]["status"]
        assert mock_adapter.execute_mandate.call_count == 0
        events = [r["event"] for r in service.db.audit_rows()]
        assert "mandate_executed" not in events
        assert service.db.verify_chain() is True


def test_approved_claim_executes_and_audits():
    with tempfile.TemporaryDirectory() as folder:
        mock_adapter = MagicMock()
        mock_adapter.execute_mandate.return_value = {
            "status": "EXECUTED",
            "live": True,
            "provider": "razorpay_test",
            "order_id": "order_mock12345",
            "amount": 800000,
            "currency": "INR",
            "receipt": "test-req-001",
        }
        service = WardenService(str(Path(folder) / "audit.db"), adapter=mock_adapter)
        service_mod = __import__(
            "backend.app.service", fromlist=["normalize", "match_context"]
        )
        orig_norm = service_mod.normalize
        orig_match = service_mod.match_context
        try:
            service_mod.normalize = lambda p: (
                make_claim(**p),
                {"extraction_confidence": 0.95, "provider": "test-double"},
            )
            service_mod.match_context = lambda c: {
                "merchant_match": True,
                "match_confidence": 0.95,
                "match_reason": "match",
                "provider": "test-double",
            }
            res = service.evaluate(make_claim().payload())
        finally:
            service_mod.normalize = orig_norm
            service_mod.match_context = orig_match

        assert res["decision"]["decision"] == "approved"
        assert res["execution"]["status"] == "EXECUTED"
        assert res["execution"]["order_id"] == "order_mock12345"
        assert mock_adapter.execute_mandate.call_count == 1
        events = [r["event"] for r in service.db.audit_rows()]
        assert "mandate_executed" in events
        assert service.db.verify_chain() is True


def test_live_razorpay_order_execution():
    """Verify live integration with Razorpay test credentials against api.razorpay.com."""
    adapter = RazorpayAdapter(
        key_id="rzp_test_TYNGpLx84Zs6lw",
        key_secret="x4kCvSjLPYn6GFVojNnkktur",
    )
    claim = make_claim(request_id="live-test-001", amount=5000)
    result = adapter.execute_mandate(claim)
    assert result["status"] == "EXECUTED", f"Execution failed: {result}"
    assert result["live"] is True
    assert result["provider"] == "razorpay_test"
    assert result["currency"] == "INR"
    assert result["amount"] == 500000
    assert result["order_id"].startswith("order_")
