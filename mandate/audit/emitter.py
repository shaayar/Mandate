import json
import re
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _redact_secrets(value: Any) -> Any:
    """Redact secret-like values from parameters for audit event emission.

    Patterns redacted: anything matching common secret key names
    (password, secret, key, token) and common API credential patterns.
    """
    if isinstance(value, str):
        lower = value.lower()
        # Check if the value matches common secret patterns
        secret_patterns = [
            r"(?:password|passwd|pwd)\s*[:=]\s*\S+",
            r"(?:api_key|apikey|api-token)\s*[:=]\s*\S+",
            r"(?:auth|access|refresh)\s*token\s*[:=]\s*\S+",
            r"(?:api_secret|secret_key)\s*[:=]\s*\S+",
        ]
        for pattern in secret_patterns:
            if re.search(pattern, lower):
                return "<redacted>"
        # Check for bare secret-like values (all caps, or common patterns)
        if re.search(r"(?:password|secret|key|token)\s*=\s*['\"]?\S+['\"]?", lower):
            return "<redacted>"
        return value
    elif isinstance(value, dict):
        result = {}
        for k, v in value.items():
            # Mask keys that look like secrets
            key_lower = k.lower()
            if any(
                s in key_lower
                for s in ["password", "secret", "key", "token", "credential"]
            ):
                result[k] = "<redacted>"
            else:
                result[k] = _redact_secrets(v)
        return result
    elif isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    return value


def _sanitize_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize parameters before audit event emission."""
    sanitized = _redact_secrets(parameters)
    # Truncate large objects
    if isinstance(sanitized, dict) and len(str(sanitized)) > 1000:
        return {"_value_truncated": True, **{k: _redact_secrets(v) for k, v in sanitized.items()}}
    return sanitized


def emit_audit_event(
    decision: Decision,
    tool_name: str,
    parameters: Dict[str, Any],
    reason: str,
    approval_id: Any = None,
    policy_ids: List[str] = None,
    evaluation_time_ms: int = 0,
) -> Dict[str, Any]:
    """Emit a structured authorization audit event.

    Returns a dictionary representing the audit event JSON.
    """
    sanitized_params = _sanitize_parameters(parameters)

    event = {
        "event_type": "authorization_decision",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "guard_version": "0.1.0",
        "tool_name": tool_name,
        "parameters": sanitized_params,
        "decision": decision.value if hasattr(decision, "value") else str(decision),
        "reason": reason,
        "approval_id": approval_id,
        "policy_ids": policy_ids or [],
        "evaluation_time_ms": evaluation_time_ms,
        "sanitized": True,
    }

    return event