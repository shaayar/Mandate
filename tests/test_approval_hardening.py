"""Approval lifecycle hardening: consumption, identity and expiry.

Each test pins a rule from public-api.md §5.5 or threat-model.md
("Single-Use Approval Consumption"): a pending, denied, expired or
already-consumed approval must never be consumable, and every request
gets its own approval.
"""

import threading
import time

from mandate import Guard


def approved(_request):
    return {"state": "approved", "is_approved": True}


def pending(_request):
    return None


def test_pending_approval_cannot_be_consumed():
    g = Guard(approval_mechanism=pending)
    approval = g.request_approval("data_export", {"dest": "s3://reports"})
    assert g.consume_approval(approval["id"]) is False


def test_denied_approval_cannot_be_consumed():
    g = Guard(approval_mechanism=pending)
    approval = g.request_approval("data_export", {"dest": "s3://reports"})
    g.deny(approval["id"])
    assert g.consume_approval(approval["id"]) is False


def test_expired_approval_cannot_be_consumed():
    g = Guard(approval_mechanism=approved, approval_timeout_ms=1000)
    approval = g.request_approval(
        "data_export", {"dest": "s3://reports"}, {"timestamp": time.time() - 5}
    )
    assert g.consume_approval(approval["id"]) is False


def test_approval_without_timestamp_still_expires():
    g = Guard(approval_mechanism=approved, approval_timeout_ms=1)
    approval = g.request_approval("data_export", {"dest": "s3://reports"})
    time.sleep(0.01)
    assert not g.is_approval_valid(approval["id"], "data_export", {"dest": "s3://reports"})
    assert g.consume_approval(approval["id"]) is False


def test_approving_again_does_not_revive_a_consumed_approval():
    g = Guard(approval_mechanism=approved)
    approval = g.request_approval("data_export", {"dest": "s3://reports"})
    assert g.consume_approval(approval["id"]) is True
    g.approve(approval["id"])
    assert not g.is_approval_valid(approval["id"], "data_export", {"dest": "s3://reports"})
    assert g.consume_approval(approval["id"]) is False


def test_identical_requests_get_distinct_approvals():
    g = Guard(approval_mechanism=approved)
    first = g.request_approval("data_export", {"dest": "s3://reports"})
    second = g.request_approval("data_export", {"dest": "s3://reports"})
    assert first["id"] != second["id"]
    assert g.consume_approval(first["id"]) is True
    assert g.consume_approval(second["id"]) is True
    assert g.consume_approval(first["id"]) is False


def test_nested_parameters_and_context_are_accepted():
    g = Guard(approval_mechanism=approved)
    approval = g.request_approval(
        "http_post",
        {"url": "https://api.example.com", "body": {"items": [1, 2]}},
        {"session": {"id": "abc"}},
    )
    assert g.is_approval_valid(
        approval["id"],
        "http_post",
        {"url": "https://api.example.com", "body": {"items": [1, 2]}},
    )


def test_concurrent_consumption_succeeds_exactly_once():
    g = Guard(approval_mechanism=approved)
    approval = g.request_approval("data_export", {"dest": "s3://reports"})
    threads_count = 32
    barrier = threading.Barrier(threads_count)
    results = []

    def consume():
        barrier.wait()
        results.append(g.consume_approval(approval["id"]))

    threads = [threading.Thread(target=consume) for _ in range(threads_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 1
    assert results.count(False) == threads_count - 1


def test_evaluation_time_is_measured_not_the_timeout():
    g = Guard(evaluation_timeout_ms=999_999)
    result = g.evaluate("file_read", {"path": "/data/report.txt"})
    assert result["evaluation_time_ms"] < 999_999
    assert g.last_audit_event["evaluation_time_ms"] == result["evaluation_time_ms"]
