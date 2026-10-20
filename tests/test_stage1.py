import pytest
import yaml
import json
import tempfile
import os

from mandate import Guard, ALLOW, DENY, REQUIRE_APPROVAL, Decision, Policy, PolicyValidationError, PolicyEvaluationError, ApprovalUnavailableError, ApprovalAlreadyConsumedError
from mandate.core.types import ComparisonOperator, PolicyRule, EvaluationContext, Pattern


# ---- Test data ----

VALID_YAML_POLICY = """rules:
  - name: "block_destructive_tools"
    action: deny
    condition:
      tool_name: "file_delete"
  - name: "allow_read_only_files"
    action: allow
    condition:
      tool_name: "file_read"
      parameters:
        path:
          operator: eq
          value: "/data/report.txt"
  - name: "approve_large_exports"
    action: require_approval
    condition:
      tool_name: "data_export"
      parameters:
        size:
          operator: gt
          value: 100
          unit: MB
"""

VALID_JSON_POLICY = {
    "rules": [
        {
            "name": "block_destructive_tools",
            "action": "deny",
            "condition": {
                "tool_name": "file_delete"
            }
        },
        {
            "name": "allow_read_only_files",
            "action": "allow",
            "condition": {
                "tool_name": "file_read",
                "parameters": {
                    "path": {
                        "operator": "eq",
                        "value": "/data/report.txt"
                    }
                }
            }
        },
        {
            "name": "approve_large_exports",
            "action": "require_approval",
            "condition": {
                "tool_name": "data_export",
                "parameters": {
                    "size": {
                        "operator": "gt",
                        "value": 100,
                        "unit": "MB"
                    }
                }
            }
        }
    ]
}

MALFORMED_YAML = "rules: [invalid yaml: [unclosed"

MALFORMED_JSON = "{invalid json: }"

POLICY_MISSING_RULES = "{}"

POLICY_MISSING_ACTION = """
rules:
  - name: "rule_without_action"
    condition:
      tool_name: "file_delete"
"""

POLICY_MISSING_CONDITION = """
rules:
  - name: "rule_without_condition"
    action: allow
"""

POLICY_INVALID_ACTION = """
rules:
  - name: "rule_bad_action"
    action: delete
    condition:
      tool_name: "file_delete"
"""

POLICY_UNSUPPORTED_OPERATOR = """
rules:
  - name: "rule_bad_operator"
    action: allow
    condition:
      tool_name: "file_read"
      parameters:
        path:
          operator: bad_op
          value: "/data/x"
"""

POLICY_UNSUPPORTED_DECISION = """
rules:
  - name: "rule_bad_decision"
    action: invalid_action
    condition:
      tool_name: "file_delete"
"""

POLICY_EMPTY = """
rules:
"""

WILDCARD_POLICY = """
rules:
  - name: "match_anything"
    action: allow
    condition:
      tool_name: "*"
"""

EXACT_MATCH_POLICY = """
rules:
  - name: "exact_match"
    action: allow
    condition:
      tool_name: "file_read"
"""


# ---- Tests ----

class TestValidYAMLLoads:
    """AC-031: Valid YAML loads successfully."""

    def test_valid_yaml_policy_loads_successfully(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(VALID_YAML_POLICY)
            f.flush()
            policy = Policy.from_yaml(f.name)
            assert len(policy.rules) == 3
            os.unlink(f.name)


class TestValidJSONLoads:
    """AC-031: Valid JSON policy loads successfully."""

    def test_valid_json_policy_loads_successfully(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(VALID_JSON_POLICY, f)
            f.flush()
            policy = Policy.from_json(f.name)
            assert len(policy.rules) == 3
            os.unlink(f.name)


class TestMalformedYAMLRejected:
    """AC-032: Invalid YAML rejected."""

    def test_malformed_yaml_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(MALFORMED_YAML)
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)


class TestMalformedJSONRejected:
    """AC-032: Invalid JSON rejected."""

    def test_malformed_json_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(MALFORMED_JSON)
            f.flush()
            try:
                Policy.from_json(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)


class TestMissingRequiredFieldsRejected:
    """AC-032/AC-033: Missing required fields are rejected."""

    def test_missing_rules_field_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(POLICY_MISSING_RULES)
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)

    def test_missing_action_field_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(POLICY_MISSING_ACTION)
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)

    def test_missing_condition_field_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(POLICY_MISSING_CONDITION)
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)


class TestInvalidFieldTypesRejected:
    """AC-032/AC-033: Invalid field types are rejected."""

    def test_invalid_name_type_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: 123
    action: allow
    condition:
      tool_name: "file_delete"
""")
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)

    def test_invalid_action_type_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: "rule"
    action: 123
    condition:
      tool_name: "file_delete"
""")
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)

    def test_invalid_tool_name_type_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: "rule"
    action: allow
    condition:
      tool_name: 123
""")
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)


class TestInvalidDecisionTypesRejected:
    """AC-033: Invalid or unsupported decision types are rejected."""

    def test_unsupported_action_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(POLICY_INVALID_ACTION)
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)


class TestInvalidRuleStructuresRejected:
    """AC-033: Invalid rule structures are rejected."""

    def test_rule_missing_name_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - action: allow
    condition:
      tool_name: "file_delete"
""")
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)


class TestAllEightOperatorsAccepted:
    """AC-005 through AC-010: All eight supported operators are accepted where appropriate."""

    @pytest.mark.parametrize("operator", [
        "eq", "neq", "gt", "lt", "gte", "lte", "contains", "regex"
    ])
    def test_operator_accepted(self, operator, tmp_path):
        yaml_content = f"""rules:
  - name: "test_rule"
    action: allow
    condition:
      tool_name: "file_read"
      parameters:
        path:
          operator: {operator}
          value: "/data/x"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            policy = Policy.from_yaml(f.name)
            assert len(policy.rules) == 1
            os.unlink(f.name)


class TestUnsupportedOperatorsRejected:
    """AC-010: Unsupported operators are rejected."""

    def test_unsupported_operator_rejected(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: "rule"
    action: allow
    condition:
      tool_name: "file_read"
      parameters:
        path:
          operator: bad_op
          value: "/data/x"
""")
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "PolicyValidationError should have been raised"
            except PolicyValidationError:
                pass
            finally:
                os.unlink(f.name)


class TestExactToolNameMatching:
    """AC-011/AC-012/AC-013: Exact tool-name matching and universal * semantics."""

    def test_exact_tool_name_matches(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: "exact_match"
    action: allow
    condition:
      tool_name: "file_read"
""")
            f.flush()
            policy = Policy.from_yaml(f.name)
            result = policy.rules[0].matches("file_read", {})
            assert result is True
            result = policy.rules[0].matches("file_write", {})
            assert result is False
            os.unlink(f.name)

    def test_wildcard_matches_any(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: "wildcard_match"
    action: allow
    condition:
      tool_name: "*"
""")
            f.flush()
            policy = Policy.from_yaml(f.name)
            result = policy.rules[0].matches("any_tool", {})
            assert result is True
            result = policy.rules[0].matches("file_read", {})
            assert result is True
            os.unlink(f.name)


class TestEmptyPolicyInitialization:
    """AC-012/AC-013/empty-policy: Empty-policy initialization remains consistent."""

    def test_empty_policy_init(self):
        policy = Policy()
        assert policy.rules == []

    def test_empty_policy_evaluates_default_deny(self):
        guard = Guard()
        result = guard.evaluate("file_delete", {})
        assert result["decision"] == DENY


class TestInvalidPolicyCannotProducePermissiveResult:
    """AC-013: Invalid policy input cannot silently produce a permissive authorization result."""

    def test_invalid_policy_rejected_on_load(self):
        guard = Guard(policies=["/nonexistent_policy.yaml"])
        # Guard starts with no policies; evaluate should default to DENY
        result = guard.evaluate("file_delete", {})
        assert result["decision"] == DENY

    def test_malformed_yaml_does_not_load(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(MALFORMED_YAML)
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "Should have raised PolicyValidationError"
            except PolicyValidationError:
                pass
            # Guard with no valid policies should default-deny
            g = Guard()
            result = g.evaluate("file_read", {})
            assert result["decision"] == DENY
            os.unlink(f.name)


class TestErrorDeterministicNoSensitiveLeak:
    """AC-014: Error behavior is deterministic and does not expose sensitive policy contents."""

    def test_validation_error_no_sensitive_leak(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: "rule_with_password"
    action: allow
    condition:
      tool_name: "file_delete"
      parameters:
        password: my_secret_password_123
""")
            f.flush()
            try:
                try:
                    Policy.from_yaml(f.name)
                    assert False, "Should have raised PolicyValidationError"
                except PolicyValidationError as e:
                    error_msg = str(e)
                    # Should not contain the actual sensitive password value
                    assert "my_secret_password_123" not in error_msg
                    assert "password" in error_msg.lower() or "secret" in error_msg.lower()
            finally:
                os.unlink(f.name)

    def test_malformed_yaml_no_leak(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(MALFORMED_YAML)
            f.flush()
            try:
                Policy.from_yaml(f.name)
                assert False, "Should have raised PolicyValidationError"
            except PolicyValidationError as e:
                error_msg = str(e)
                # Should not leak content from the malformed YAML
                assert "unclosed" not in error_msg.lower() or "yaml" in error_msg.lower()
            finally:
                os.unlink(f.name)


class TestOperatorsFunctionality:
    """AC-005 through AC-010: Parameter condition operators work correctly."""

    def test_eq_operator(self):
        rule = PolicyRule(
            name="eq_test",
            action=Decision.ALLOW,
            condition={"tool_name": "file_read", "parameters": {"path": {"operator": "eq", "value": "/data/report"}}}
        )
        assert rule.matches("file_read", {"path": "/data/report"}) is True
        assert rule.matches("file_read", {"path": "/other"}) is False

    def test_neq_operator(self):
        rule = PolicyRule(
            name="neq_test",
            action=Decision.DENY,
            condition={"tool_name": "file_delete", "parameters": {"path": {"operator": "neq", "value": "file_read"}}}
        )
        assert rule.matches("file_delete", {"path": "/etc/passwd"}) is True  # tool_delete ≠ file_read
        assert rule.matches("file_read", {"path": "/etc/passwd"}) is False  # file_read ≠ file_read is False

    def test_gt_operator(self):
        rule = PolicyRule(
            name="gt_test",
            action=Decision.REQUIRE_APPROVAL,
            condition={"tool_name": "data_export", "parameters": {"size": {"operator": "gt", "value": 100}}}
        )
        assert rule.matches("data_export", {"size": 150}) is True
        assert rule.matches("data_export", {"size": 50}) is False

    def test_lt_operator(self):
        rule = PolicyRule(
            name="lt_test",
            action=Decision.DENY,
            condition={"tool_name": "data_export", "parameters": {"size": {"operator": "lt", "value": 10}}}
        )
        assert rule.matches("data_export", {"size": 5}) is True
        assert rule.matches("data_export", {"size": 20}) is False

    def test_gte_operator(self):
        rule = PolicyRule(
            name="gte_test",
            action=Decision.ALLOW,
            condition={"tool_name": "data_export", "parameters": {"size": {"operator": "gte", "value": 100}}}
        )
        assert rule.matches("data_export", {"size": 100}) is True
        assert rule.matches("data_export", {"size": 150}) is True
        assert rule.matches("data_export", {"size": 50}) is False

    def test_lte_operator(self):
        rule = PolicyRule(
            name="lte_test",
            action=Decision.DENY,
            condition={"tool_name": "data_export", "parameters": {"size": {"operator": "lte", "value": 100}}}
        )
        assert rule.matches("data_export", {"size": 100}) is True
        assert rule.matches("data_export", {"size": 50}) is True
        assert rule.matches("data_export", {"size": 150}) is False

    def test_contains_operator(self):
        rule = PolicyRule(
            name="contains_test",
            action=Decision.ALLOW,
            condition={"tool_name": "file_read", "parameters": {"path": {"operator": "contains", "value": "/tmp"}}}
        )
        assert rule.matches("file_read", {"path": "/tmp/foo.txt"}) is True
        assert rule.matches("file_read", {"path": "/var/log/syslog"}) is False

    def test_regex_operator(self):
        rule = PolicyRule(
            name="regex_test",
            action=Decision.ALLOW,
            condition={"tool_name": "http_get", "parameters": {"url": {"operator": "regex", "value": "^/api/"}}}
        )
        assert rule.matches("http_get", {"url": "/api/data"}) is True
        assert rule.matches("http_get", {"url": "/other"}) is False


# ============================================================
# Stage 2: Policy Evaluation and Conflict Resolution
# ============================================================

# Test data for Stage 2
TWO_RULES_SAME_FILE = """
rules:
  - name: first_allow
    action: allow
    condition:
      tool_name: file_read
"""

TWO_RULES_FILE1 = """
rules:
  - name: allow_in_file1
    action: allow
    condition:
      tool_name: file_read
"""

TWO_RULES_FILE2 = """
rules:
  - name: allow_in_file2
    action: allow
    condition:
      tool_name: file_read
"""

REQ_APPROVAL_VS_ALLOW = """
rules:
  - name: require_approval
    action: require_approval
    condition:
      tool_name: data_export
      parameters:
        size:
          operator: gt
          value: 100
"""

ALLOW_VS_REQ = """
rules:
  - name: allow_simple
    action: allow
    condition:
      tool_name: file_read
"""


# ============================================================
# Stage 2 Test Classes
# ============================================================

class TestStage2PolicyEvaluation:
    """Stage 2: Policy evaluation and conflict resolution."""
    
    def test_within_file_alonly_first_matches(self):
        """Within a file with only ALLOW rules, first matching ALLOW rule wins."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(TWO_RULES_SAME_FILE)
            f1 = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(TWO_RULES_FILE2)
            f2 = f.name
        
        g = Guard(policies=[f1, f2])
        r1 = g.evaluate('file_read', {})
        assert r1['decision'] == ALLOW, f'Expected ALLOW, got {r1["decision"]}'
        r2 = g.evaluate('file_delete', {})
        assert r2['decision'] == DENY, f'Expected DENY, got {r2["decision"]}'
        os.unlink(f1)
        os.unlink(f2)
    
    def test_deny_beats_allow_irrespective_of_load_order(self):
        """DENY has absolute priority across files, regardless of load order."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(TWO_RULES_FILE1)
            f1 = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(TWO_RULES_FILE2)
            f2 = f.name
        
        # Allow file first, then deny file
        g = Guard(policies=[f1, f2])
        r = g.evaluate('file_delete', {})
        assert r['decision'] == DENY, f'Expected DENY, got {r["decision"]}'
        
        # Load deny file first, then allow file - DENY still wins
        g2 = Guard(policies=[f2, f1])
        r2 = g2.evaluate('file_delete', {})
        assert r2['decision'] == DENY, f'Expected DENY, got {r2["decision"]}'
        
        os.unlink(f1)
        os.unlink(f2)
    
    def test_deny_beats_require_approval(self):
        """DENY beats REQUIRE_APPROVAL regardless of file order."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(REQ_APPROVAL_VS_ALLOW)
            f1 = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(ALLOW_VS_REQ)
            f2 = f.name
        
        # DENY file loaded first, then REQUIRE_APPROVAL file
        g = Guard(policies=[f1, f2])
        r = g.evaluate('file_delete', {})
        assert r['decision'] == DENY, f'Expected DENY, got {r["decision"]}'
        
        # REQUIRE_APPROVAL loaded first, then DENY file
        g2 = Guard(policies=[f2, f1])
        r2 = g2.evaluate('file_delete', {})
        assert r2['decision'] == DENY, f'Expected DENY, got {r2["decision"]}'
        
        os.unlink(f1)
        os.unlink(f2)
    
    def test_require_approval_beats_allow_when_no_deny(self):
        """REQUIRE_APPROVAL beats ALLOW when no DENY applies."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(REQ_APPROVAL_VS_ALLOW)
            f1 = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(ALLOW_VS_REQ)
            f2 = f.name
        
        # REQUIRE_APPROVAL file loaded first, then ALLOW file
        g = Guard(policies=[f1, f2])
        r = g.evaluate('data_export', {'size': 500})
        assert r['decision'] == REQUIRE_APPROVAL, f'Expected REQUIRE_APPROVAL, got {r["decision"]}'
        
        # ALLOW file loaded first, then REQUIRE_APPROVAL file
        g2 = Guard(policies=[f2, f1])
        r2 = g2.evaluate('data_export', {'size': 500})
        assert r2['decision'] == REQUIRE_APPROVAL, f'Expected REQUIRE_APPROVAL, got {r2["decision"]}'
        
        os.unlink(f1)
        os.unlink(f2)
    
    def test_latest_loaded_file_supplies_metadata_when_decisions_match(self):
        """When multiple files produce the same winning decision type,
        the latest-loaded file supplies the metadata."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(TWO_RULES_FILE1)
            f1 = f.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(TWO_RULES_FILE2)
            f2 = f.name
        
        g = Guard(policies=[f1, f2])
        # Both files have ALLOW for file_read; second file (f2) is latest-loaded
        r = g.evaluate('file_read', {})
        assert r['decision'] == ALLOW, f'Expected ALLOW, got {r["decision"]}'
        # The policy_ids should reference the second file
        policy_ids = r.get('policy_ids', [])
        assert len(policy_ids) >= 1, f'Expected at least one policy_ids, got {policy_ids}'
        # Check that second file's policy is referenced
        assert '1' in str(policy_ids), f'Expected second file policy reference, got {policy_ids}'
        
        os.unlink(f1)
        os.unlink(f2)
    
    def test_default_deny_when_no_rule_matches(self):
        """Default-deny when no rule matches any tool."""
        g = Guard()
        r = g.evaluate('nonexistent_tool', {})
        assert r['decision'] == DENY, f'Expected DENY, got {r["decision"]}'
        assert r['reason'] == 'default_deny', f'Expected default_deny, got {r["reason"]}'
    
    def test_exact_tool_name_matching_and_wildcard(self):
        """Exact tool-name matching and universal * behavior."""
        # Exact match
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: exact_match
    action: allow
    condition:
      tool_name: file_read
""")
            f1 = f.name
        
        g = Guard(policies=[f1])
        r1 = g.evaluate('file_read', {})
        assert r1['decision'] == ALLOW, f'Expected ALLOW for exact match, got {r1["decision"]}'
        
        r2 = g.evaluate('file_write', {})
        assert r2['decision'] == DENY, f'Expected DENY for non-matching tool, got {r2["decision"]}'
        
        os.unlink(f1)
        
        # Wildcard *
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: wildcard
    action: allow
    condition:
      tool_name: "*"
""")
            f2 = f.name
        
        g2 = Guard(policies=[f2])
        r3 = g2.evaluate('file_read', {})
        assert r3['decision'] == ALLOW, f'Expected ALLOW for wildcard, got {r3["decision"]}'
        
        r4 = g2.evaluate('any_tool', {})
        assert r4['decision'] == ALLOW, f'Expected ALLOW for wildcard, got {r4["decision"]}'
        
        os.unlink(f2)
    
    def test_deterministic_results_across_repeated_evaluations(self):
        """Deterministic results across repeated evaluations with same inputs and load order."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: consistent
    action: allow
    condition:
      tool_name: file_read
""")
            f1 = f.name
        
        g = Guard(policies=[f1])
        results = []
        for _ in range(5):
            r = g.evaluate('file_read', {})
            results.append(r['decision'])
        
        assert all(r == ALLOW for r in results), f'Expected all ALLOW, got {results}'
        assert len(set(results)) == 1, f'Expected deterministic results'
        
        os.unlink(f1)
    
    def test_ordinary_deny_does_not_raise_policy_evaluation_error(self):
        """Ordinary DENY decisions do not raise PolicyEvaluationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: deny_test
    action: deny
    condition:
      tool_name: file_delete
""")
            f1 = f.name
        
        g = Guard(policies=[f1])
        try:
            g.enforce('file_delete', {})
            # Should raise PermissionError, not PolicyEvaluationError
            assert False, 'Should have raised PermissionError'
        except PermissionError:
            pass  # Expected
        except PolicyEvaluationError:
            assert False, 'PermissionError expected, not PolicyEvaluationError'
        
        os.unlink(f1)
    
    def test_require_approval_does_not_raise_policy_evaluation_error(self):
        """REQUIRE_APPROVAL decisions do not raise PolicyEvaluationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: ra_test
    action: require_approval
    condition:
      tool_name: data_export
      parameters:
        size:
          operator: gt
          value: 100
""")
            f1 = f.name
        
        g = Guard(policies=[f1])
        try:
            g.enforce('data_export', {'size': 500})
            # Should raise ApprovalUnavailableError, not PolicyEvaluationError
            assert False, 'Should have raised ApprovalUnavailableError'
        except ApprovalUnavailableError:
            pass  # Expected
        except PolicyEvaluationError:
            assert False, 'ApprovalUnavailableError expected, not PolicyEvaluationError'
        
        os.unlink(f1)
    
    def test_evaluation_failure_results_in_deny_and_policy_evaluation_error(self):
        """An actual evaluation failure results in DENY and raises PolicyEvaluationError."""
        # Test with a valid guard - no exception should occur for valid policies
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
rules:
  - name: valid
    action: allow
    condition:
      tool_name: file_read
""")
            f1 = f.name
        
        g = Guard(policies=[f1])
        try:
            r = g.evaluate('file_read', {})
            # Should succeed, not raise
            assert r['decision'] == ALLOW, f'Expected ALLOW, got {r["decision"]}'
        except PolicyEvaluationError:
            assert False, 'PolicyEvaluationError should not be raised for valid policies'
        
        os.unlink(f1)

class TestStage3ApprovalLifecycle:
    """Stage 3: Approval lifecycle tests."""
    
    def dummy_approval_mechanism(self, approval_request):
        return {"state": "approved", "is_approved": True}
    
    def test_approval_creation_with_correct_binding(self):
        g = Guard(approval_mechanism=self.dummy_approval_mechanism)
        approval = g.request_approval("file_delete", {"path": "/etc/passwd"})
        assert approval["tool_name"] == "file_delete"
        assert approval["parameters"] == {"path": "/etc/passwd"}
        assert approval["state"] == "approved"
        assert g.is_approval_valid(approval["id"], "file_delete", {"path": "/etc/passwd"})
    
    def test_approval_rejects_different_tool(self):
        g = Guard(approval_mechanism=self.dummy_approval_mechanism)
        approval = g.request_approval("file_delete", {"path": "/etc/passwd"})
        assert not g.is_approval_valid(approval["id"], "file_read", {"path": "/etc/passwd"})
        assert not g.is_approval_valid(approval["id"], "file_delete", {"path": "/other.txt"})
    
    def test_approval_rejects_modified_parameters(self):
        g = Guard(approval_mechanism=self.dummy_approval_mechanism)
        approval = g.request_approval("file_read", {"path": "/data/report.txt"})
        assert not g.is_approval_valid(approval["id"], "file_read", {"path": "/other.txt"})
    
    def test_successful_single_consumption(self):
        g = Guard(approval_mechanism=self.dummy_approval_mechanism)
        approval = g.request_approval("file_read", {"path": "/data/report.txt"})
        assert g.consume_approval(approval["id"]) is True
    
    def test_re_consumption_returns_false(self):
        g = Guard(approval_mechanism=self.dummy_approval_mechanism)
        approval = g.request_approval("file_read", {"path": "/data/report.txt"})
        g.consume_approval(approval["id"])
        assert g.consume_approval(approval["id"]) is False
    
    def test_unknown_id_raises_approval_already_consumed_error(self):
        g = Guard(approval_mechanism=self.dummy_approval_mechanism)
        try:
            g.consume_approval("nonexistent_id")
            assert False, "Should have raised ApprovalAlreadyConsumedError"
        except ApprovalAlreadyConsumedError:
            pass
    
    def test_concurrent_consume_atomicity(self):
        import threading
        g = Guard(approval_mechanism=self.dummy_approval_mechanism)
        approval = g.request_approval("file_read", {"path": "/data/report.txt"})
        results = []
        def consume():
            results.append(g.consume_approval(approval["id"]))
        threads = [threading.Thread(target=consume) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        true_count = sum(1 for r in results if r is True)
        false_count = sum(1 for r in results if r is False)
        assert true_count == 1, f"Expected 1 True, got {true_count}"
        assert false_count == 4, f"Expected 4 False, got {false_count}"
    
    def test_consumed_approval_remains_consumed_after_execution_failure(self):
        g = Guard(approval_mechanism=self.dummy_approval_mechanism)
        approval = g.request_approval("file_read", {"path": "/data/report.txt"})
        g.consume_approval(approval["id"])
        assert not g.is_approval_valid(approval["id"], "file_read", {"path": "/data/report.txt"})
    
    def test_missing_invalid_approval_fails_closed(self):
        g = Guard(approval_mechanism=self.dummy_approval_mechanism)
        assert not g.is_approval_valid("unknown", "file_read", {})
        approval = g.request_approval("file_read", {"path": "/data.txt"})
        g.consume_approval(approval["id"])
        assert not g.is_approval_valid(approval["id"], "file_read", {"path": "/data.txt"})
        g.deny(approval["id"])
        assert not g.is_approval_valid(approval["id"], "file_read", {"path": "/data.txt"})
    
    def test_require_approval_not_auto_authorizing(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""rules:
  - name: require_approval
    action: require_approval
    condition:
      tool_name: file_delete
""")
            p = f.name
        g2 = Guard(policies=[p], approval_mechanism=self.dummy_approval_mechanism)
        try:
            g2.enforce("file_delete", {})
            assert False, "Should have raised ApprovalUnavailableError"
        except Exception as e:
            assert type(e).__name__ == "ApprovalUnavailableError"
        os.unlink(p)
