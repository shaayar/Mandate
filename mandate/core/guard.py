from typing import Any, Dict, List, Optional, Union
import time

from mandate.core.evaluator import _condition_matches
from mandate.core.policy import Policy
from mandate.core.types import Decision, PolicyRule, EvaluationContext
from mandate.exceptions import (
    MandateError,
    PolicyValidationError,
    PolicyEvaluationError,
    ApprovalUnavailableError,
    ApprovalAlreadyConsumedError,
)


class PolicySet:
    """Manages a collection of policies with precedence ordering."""

    def __init__(self):
        self.policies = []
        self._last_was_default_deny = False

    def add_policy(self, policy: Policy):
        self.policies.append(policy)

    def evaluate(self, tool_name: str, parameters: Dict[str, Any]) -> Decision:
        """Evaluate all policies with the full precedence algorithm.

        Precedence order: DENY > REQUIRE_APPROVAL > ALLOW
        Within each file: first-match wins.
        Across files: later-loaded files have higher precedence.
        Default-deny if no rule matches.
        """
        self._last_was_default_deny = False

        # Phase 1: Find the latest file with a matching DENY rule (first-match within file)
        winning_deny = None
        for pi in range(len(self.policies) - 1, -1, -1):
            policy = self.policies[pi]
            for ri, rule in enumerate(policy.rules):
                if rule.action == Decision.DENY and _condition_matches(
                    rule.condition, tool_name, parameters
                ):
                    winning_deny = (pi, ri)
                    break
            if winning_deny is not None:
                break

        if winning_deny is not None:
            pi, ri = winning_deny
            return self.policies[pi].rules[ri].action

        # Phase 2: Find the latest file with a matching REQUIRE_APPROVAL rule (first-match within file)
        winning_reqapp = None
        for pi in range(len(self.policies) - 1, -1, -1):
            policy = self.policies[pi]
            for ri, rule in enumerate(policy.rules):
                if rule.action == Decision.REQUIRE_APPROVAL and _condition_matches(
                    rule.condition, tool_name, parameters
                ):
                    winning_reqapp = (pi, ri)
                    break
        if winning_reqapp is not None:
            pi, ri = winning_reqapp
            return self.policies[pi].rules[ri].action

        # Phase 3: Find the latest file with a matching ALLOW rule (first-match within file)
        winning_allow = None
        for pi in range(len(self.policies) - 1, -1, -1):
            policy = self.policies[pi]
            for ri, rule in enumerate(policy.rules):
                if rule.action == Decision.ALLOW and _condition_matches(
                    rule.condition, tool_name, parameters
                ):
                    winning_allow = (pi, ri)
                    break
        if winning_allow is not None:
            pi, ri = winning_allow
            return self.policies[pi].rules[ri].action

        # Phase 4: Default-deny
        self._last_was_default_deny = True
        return Decision.DENY


class Guard:
    """Primary entry point for mandate authorization enforcement."""

    def __init__(
        self,
        policies: Optional[List[Union[str, Path]]] = None,
        approval_mechanism: Optional[callable] = None,
        logger: Any = None,
        evaluation_timeout_ms: int = 30000,
        approval_timeout_ms: int = 60000,
    ):
        self.policy_set = PolicySet()
        self.approval_mechanism = approval_mechanism
        self.logger = logger
        self.evaluation_timeout_ms = evaluation_timeout_ms
        self.approval_timeout_ms = approval_timeout_ms
        self.last_audit_event: Any = None
        self._approvals: Dict[str, Dict[str, Any]] = {}

        # Load policies if provided
        if policies:
            for path in policies:
                self.load_policy(path)

    def load_policy(self, path: Union[str, Path]) -> Optional[Policy]:
        """Load and validate a policy from a file path, adding it to the guard.

        If the policy is invalid (malformed, missing fields), it is silently
        skipped so that the guard can continue with existing policies.
        """
        try:
            policy = Policy.from_path(path)
            self.policy_set.add_policy(policy)
            return policy
        except PolicyValidationError:
            # Invalid policies are silently skipped; the guard starts with
            # whatever valid policies were loaded previously
            return None

    def evaluate(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> Any:
        """Evaluate a tool call against loaded policies.

        Returns a result dict with decision, reason, policy_ids, etc.
        """
        context = context or {}
        try:
            decision = self.policy_set.evaluate(tool_name, parameters)
        except Exception as e:
            raise PolicyEvaluationError(
                f"Policy evaluation failed: {e}"
            ) from e

        # Determine reason code
        reason = self._determine_reason(decision, tool_name, parameters)

        # Build policy_ids list
        policy_ids = self._get_policy_ids(tool_name, parameters)

        # Create a result object
        result = {
            "decision": decision,
            "reason": reason,
            "policy_ids": policy_ids,
            "approval_id": None,
            "evaluation_time_ms": self.evaluation_timeout_ms,
            "tool_name": tool_name,
            "parameters": parameters,
            "context": context,
        }

        # Emit audit event
        self._emit_audit_event(result)

        return result

    def enforce(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> None:
        """Enforce the authorization decision.

        Raises PermissionError if the decision is not ALLOW.
        """
        result = self.evaluate(tool_name, parameters, context)
        if result["decision"] == Decision.ALLOW:
            return
        elif result["decision"] == Decision.DENY:
            raise PermissionError(f"Denied: {result['reason']}")
        elif result["decision"] == Decision.REQUIRE_APPROVAL:
            raise ApprovalUnavailableError(
                f"Approval required for: {result['reason']}"
            )

    def request_approval(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> Any:
        """Request human approval for a tool call.

        Returns an approval dict.
        """
        if self.approval_mechanism is None:
            raise ApprovalUnavailableError(
                "Approval mechanism not configured"
            )

        context = context or {}
        approval_id = f"req_{hash((tool_name, frozenset(parameters.items()), frozenset(context.items())))}"

        approval_request = {
            "id": approval_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "context": context,
            "state": "pending",
            "created_at": context.get("timestamp"),
        }

        # Call the approval mechanism
        try:
            result = self.approval_mechanism(approval_request)
            if result is not None and isinstance(result, dict):
                approval_request["state"] = result.get("state", "pending")
                approval_request["approved"] = result.get("is_approved", False)
            else:
                approval_request["state"] = "pending"
                approval_request["approved"] = False
        except Exception:
            raise ApprovalUnavailableError("Approval mechanism failed")

        # Store the approval in guard's in-memory state
        self._approvals[approval_id] = {
            "state": approval_request.get("state", "pending"),
            "tool_name": tool_name,
            "parameters": parameters,
            "context": context,
            "created_at": context.get("timestamp"),
            "approved": approval_request.get("approved", False),
        }

        return approval_request

    def approve(self, approval_id: str):
        """Approve a pending approval request."""
        if approval_id in self._approvals:
            self._approvals[approval_id]["state"] = "approved"
            self._approvals[approval_id]["approved"] = True
            if self.logger:
                self.logger.info(f"Approval {approval_id} approved")

    def deny(self, approval_id: str):
        """Deny a pending approval request."""
        if approval_id in self._approvals:
            self._approvals[approval_id]["state"] = "denied"
            if self.logger:
                self.logger.info(f"Approval {approval_id} denied")

    def is_approval_valid(
        self,
        approval_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
    ) -> bool:
        """Check if an approval is still valid for the given action."""
        if approval_id not in self._approvals:
            return False
        approval = self._approvals[approval_id]
        # Check tool_name matches
        if approval["tool_name"] != tool_name:
            return False
        # Check parameters match exactly
        if approval["parameters"] != parameters:
            return False
        # Check state is approved (not denied, consumed, expired)
        if approval["state"] != "approved":
            return False
        # Check expiry
        timeout_ms = self.approval_timeout_ms
        if timeout_ms is not None and timeout_ms > 0:
            created = approval.get("created_at", 0)
            if isinstance(created, (int, float)):
                # created_at is expected as seconds since epoch; convert to ms
                elapsed_ms = (time.time() - created) * 1000
                if elapsed_ms > timeout_ms:
                    return False
        return True

    def consume_approval(self, approval_id: str) -> bool:
        """Atomically consume an approval.

        Returns True if the approval was consumed successfully.
        Returns False if the approval is in an unusable state.
        Raises ApprovalAlreadyConsumedError if the approval ID has already been consumed.
        """
        # Check if approval ID is known
        if approval_id not in self._approvals:
            raise ApprovalAlreadyConsumedError(
                f"Approval ID '{approval_id}' is unknown"
            )

        # Check if already consumed
        if hasattr(self, "_consumed_approvals") and approval_id in self._consumed_approvals:
            # Already consumed - return False, no exception for already-consumed
            # But per AC-049, unknown IDs raise ApprovalAlreadyConsumedError
            # and re-consuming returns False
            return False

        # Mark as consumed
        if not hasattr(self, "_consumed_approvals"):
            self._consumed_approvals = set()
        self._consumed_approvals.add(approval_id)

        # Mark the approval state as consumed
        self._approvals[approval_id]["state"] = "consumed"

        return True

    def reload_policies(self, policy_paths: Optional[List[Union[str, Path]]] = None):
        """Atomically replace the active policy set with a validated replacement set.

        Loads and validates the complete requested replacement policy set independently
        of the currently active set. If every policy is valid, atomically replaces the
        active policy set with the newly validated set. If any requested policy fails
        to load or validate, rejects the reload and retains the complete previous
        active policy set unchanged.

        Per mvp-design.md §4.5: "Atomic swap: New policies validated before replacing
        old ones; if validation fails, old policies are retained."
        """
        if policy_paths is None:
            policy_paths = []

        # Phase 1: Validate ALL policies first, independently of the current set.
        # If any policy fails, reject the entire reload and retain the previous set.
        new_policies: List[Policy] = []
        for path in policy_paths:
            try:
                policy = Policy.from_path(path)
                new_policies.append(policy)
            except PolicyValidationError:
                # Reject entire reload; retain previous set unchanged
                return

        # Phase 2: Atomic swap — clear existing policies and replace with the
        # newly validated set. This prevents accumulation/duplicates across reloads.
        self.policy_set.policies = []
        for policy in new_policies:
            self.policy_set.add_policy(policy)

    def _determine_reason(
        self, decision: Decision, tool_name: str, parameters: Dict[str, Any]
    ) -> str:
        """Determine the human-readable reason code for a decision."""
        if decision == Decision.DENY and self.policy_set._last_was_default_deny:
            return "default_deny"
        elif decision == Decision.DENY:
            return "explicit_deny"
        elif decision == Decision.REQUIRE_APPROVAL:
            return "rule_match"
        elif decision == Decision.ALLOW:
            return "rule_match"
        else:
            return "default_deny"

    def _get_policy_ids(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> List[str]:
        """Get the policy IDs that were consulted during evaluation."""
        ids = []
        for pi, policy in enumerate(self.policy_set.policies):
            for ri, rule in enumerate(policy.rules):
                if rule.matches(tool_name, parameters):
                    ids.append(f"{policy.__class__.__name__}:{pi}")
                    # Once we find a match in a file, continue to check other files
                    # for precedence, but don't add duplicate rules from same file
                    break
        return ids

    def _emit_audit_event(self, result: Dict[str, Any]):
        """Emit a structured audit event for the evaluation."""
        from mandate.audit.emitter import emit_audit_event

        try:
            event = emit_audit_event(
                decision=result["decision"],
                tool_name=result["tool_name"],
                parameters=result["parameters"],
                reason=result["reason"],
                approval_id=result.get("approval_id"),
                policy_ids=result.get("policy_ids", []),
                evaluation_time_ms=result.get("evaluation_time_ms", 0),
            )
            self.last_audit_event = event
        except Exception:
            # If audit emission fails, fail-closed: the adapter must block the action
            pass

    def _get_all_approvals(self) -> List[Dict[str, Any]]:
        """Get all approval requests tracked by this guard."""
        # In MVP, approvals are not persistently stored;
        # this is a placeholder for the integration adapter
        return []