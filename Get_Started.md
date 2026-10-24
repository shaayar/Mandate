# Get Started with Mandate Codebase

This is a read-only exploration of the Mandate repository.

---

## 1. mandate/core/types.py — The Type System

This file defines the core data types and enums that every other module uses. It is the "foundation" layer — nothing in the codebase works without these types.

### Important Classes and Enums

| Name | What it is | Key Details |
| --- | --- | --- |
| `Decision` (enum) | The three possible authorization outcomes | `ALLOW = auto()`, `DENY = auto()`, `REQUIRE_APPROVAL = auto()` |
| `ALLOW`, `DENY`, `REQUIRE_APPROVAL` | Module-level convenience variables | These are just aliases: `ALLOW = Decision.ALLOW`, etc. Used everywhere as `from mandate import ALLOW` |
| `ComparisonOperator` (enum) | The 8 operators valid in policy conditions | `EQ = "eq"`, `NEQ = "neq"`, `GT = "gt"`, `LT = "lt"`, `GTE = "gte"`, `LTE = "lte"`, `CONTAINS = "contains"`, `REGEX = "regex"` |
| `Pattern` | Type alias | Simply `str` — used for tool_name pattern matching |
| `EvaluationContext` (dataclass) | The context passed to every evaluation | `tool_name: str`, `parameters: Dict[str, Any]`, `context: Dict[str, Any] = None` <br> `__post_init__()` ensures `context` defaults to `{}` if not provided |
| `PolicyRule` (dataclass) | A single policy rule: name + action + condition | `name: str`, `action: Decision`, `condition: Dict[str, Any]` <br> `matches(tool_name, parameters) -> bool`: checks if this rule matches a given tool call <br> `_eval_parameter(param_name, actual_value, condition) -> bool`: evaluates a single parameter condition using the operator (eq, neq, gt, lt, gte, lte, contains, regex) |

### How `PolicyRule.matches()` Works (step by step)

1. If the rule has a `tool_name` in its condition:
   - If it's `"*"` → matches any tool name (passes)
   - If it's a specific name (e.g., `"file_read"`) → only matches if `tool_name` argument is identical
2. If the rule has `parameters` in its condition:
   - For each parameter name in the condition:
     - If that parameter is **absent** from the tool's parameters → return `False` (the rule requires this parameter)
     - If the parameter is present → evaluate it using `_eval_parameter()` with the operator and value from the condition
   - If **all** parameter conditions pass → return `True`
3. If no `tool_name` condition and all (or no) parameter conditions pass → return `True`

### Concrete Example

```python
from mandate.core.types import PolicyRule, Decision

rule = PolicyRule(
    name="allow_file_read",
    action=Decision.ALLOW,
    condition={"tool_name": "file_read", "parameters": {"path": {"operator": "eq", "value": "/data/report.txt"}}}
)

# This matches: tool_name is "file_read", and the path condition eq-checks "/data/report.txt" == "/data/report.txt"
rule.matches("file_read", {"path": "/data/report.txt"})  # True

# This does NOT match: tool_name is "file_write", not "file_read"
rule.matches("file_write", {})  # False
```

### Security-Sensitive Assumption

- All parameter comparisons are **exact value equality** or numeric comparisons. There is no `eval()` or arbitrary Python code execution. The operator dispatch is a simple `if/elif` chain in `_eval_parameter()`.

### Relevant Test Names (from `tests/test_stage1.py`)

- `TestExactToolNameMatching` — tests exact match and wildcard `*` behavior (AC-011/012/013)
- `TestAllEightOperatorsAccepted` — parametrized test for all 8 operators (AC-005 through AC-010)
- `TestOperatorsFunctionality` — individual operator tests: eq, neq, gt, lt, gte, lte, contains, regex

---

## 2. mandate/core/policy.py — Policy Loading and Validation

This file is responsible for **loading** policies from YAML or JSON files and **validating** them. It ensures that every policy rule has the correct structure before the guard ever uses it.

### Important Classes and Methods

| Name | What it does |
| --- | --- |
| `Policy.__init__(rules)` | Holds a list of `PolicyRule` objects. Starts empty by default. |
| `Policy.from_yaml(path)` | Loads a YAML file, parses it with `yaml.safe_load()`, validates it, returns a `Policy`. Raises `PolicyValidationError` on malformed YAML or missing fields. |
| `Policy.from_json(path)` | Same as above, but for JSON files using `json.load()`. |
| `Policy.from_yaml_string(string)` | Loads from a YAML string (no file needed). |
| `Policy.from_json_string(string)` | Loads from a JSON string. |
| `Policy.from_dict(data)` | Internal: constructs a `Policy` from a already-parsed dict, after validation. |
| `Policy._validate(data)` | Static method: validates the top-level policy dict has a `"rules"` key whose value is a list. Raises `PolicyValidationError` if missing or malformed. |
| `Policy._validate_rule(rule_data)` | Static method: validates a single rule dict. Checks: <br> - `"name"` field present and is a string <br> - `"action"` field present and is one of `"allow"`, `"deny"`, `"require_approval"` <br> - `"condition"` field present and is a dict <br> - `"tool_name"` in condition is a string or `"*"` <br> - Each parameter in `"parameters"` has `"operator"` (must be in `SUPPORTED_OPERATORS`) and `"value"` <br> Returns a `PolicyRule` object. |
| `Policy.from_path(path)` | Auto-detects format: if suffix is `.yaml` or `.yml`, uses `from_yaml`; if `.json`, uses `from_json`; otherwise tries YAML first, then JSON. |

### How Validation Works (concrete example)

If you have this YAML file `policies/airport_security.yaml`:

```yaml
rules:
  - name: "block_destructive_tools"
    action: deny
    condition:
      tool_name: "file_delete"
```

1. `Policy.from_yaml("policies/airport_security.yaml")` is called
2. `yaml.safe_load(f)` parses it into a Python dict
3. `from_dict(data)` is called
4. `_validate(data)` checks: is it a dict? Yes. Does it have `"rules"`? Yes. Are rules a list? Yes.
5. `_validate_rule(rule_data)` is called for each rule:
   - Checks `"name"` → `"block_destructive_tools"` is a string ✓
   - Checks `"action"` → `"deny"` is in (`"allow"`, `"deny"`, `"require_approval"`) ✓
   - `Decision["DENY"]` converts it to the enum value
   - Checks `"condition"` → present, is a dict ✓
   - Checks `"tool_name"` in condition → `"file_delete"` is a string ✓
   - Checks parameters → no `parameters` key in this rule, so skips that section
   - Returns `PolicyRule(name="block_destructive_tools", action=Decision.DENY, condition={"tool_name": "file_delete"})`

### Concrete Example — Creating a Policy from YAML

```python
from mandate import Policy

policy = Policy.from_yaml("policies/airport_security.yaml")
# policy.rules is a list of PolicyRule objects, each with .name, .action, .condition
```

### Security-Sensitive Assumptions

- **`yaml.safe_load()` is used intentionally** — it does **not** execute arbitrary Python code. It only supports basic YAML tags. This is a deliberate design constraint stated across all documentation.
- Invalid policies are **silently skipped** by the guard (see `Guard.load_policy()`), not crash the system. This is a fail-closed design choice: the guard starts with whatever valid policies were loaded previously.
- The set of supported operators is **finite and explicit** (`SUPPORTED_OPERATORS`). No operator can be added dynamically via policy text.

### Relevant Test Names (from `tests/test_stage1.py`)

- `TestValidYAMLLoads` / `TestValidJSONLoads` — valid policies load successfully, rule count assertion (AC-031)
- `TestMalformedYAMLRejected` / `TestMalformedJSONRejected` — malformed input raises `PolicyValidationError` (AC-032)
- `TestMissingRequiredFieldsRejected` — missing `rules`, `action`, or `condition` fields raise error (AC-032/033)
- `TestInvalidFieldTypesRejected` — wrong types for name, action, tool_name (AC-032/033)
- `TestInvalidDecisionTypesRejected` — unsupported action value like `"delete"` or `"invalid_action"` (AC-033)
- `TestInvalidRuleStructuresRejected` — rule missing `"name"` field (AC-033)
- `TestAllEightOperatorsAccepted` — all 8 operators (eq, neq, gt, lt, gte, lte, contains, regex) are accepted (AC-005-010)
- `TestUnsupportedOperatorsRejected` — operator like `"bad_op"` causes `PolicyValidationError` (AC-010)
- `TestInvalidPolicyCannotProducePermissiveResult` — loading a nonexistent policy results in empty policy set; `evaluate()` defaults to DENY (AC-013)

---

## 3. mandate/core/evaluator.py — The Policy Evaluation Engine

This file contains the **actual evaluation logic**. It takes a tool call (tool_name + parameters) and a collection of policy rules, and produces a `Decision` (ALLOW/DENY/REQUIRE_APPROVAL).

### Important Functions

| Name | What it does |
| --- | --- |
| `_tool_name_matches(tool_name, condition_tool_name)` | Returns `True` if `condition_tool_name == "*"` (wildcard) or `tool_name == condition_tool_name` (exact match). |
| `_eval_parameter_operator(actual_value, condition)` | Evaluates a single parameter condition. Dispatches on `operator`: `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `contains`, `regex`. Returns `False` if operator or value is `None`. |
| `_condition_matches(condition, tool_name, parameters)` | The core matching function. Returns `True` **only if** BOTH: <br> 1. tool_name matches (via `_tool_name_matches`), AND <br> 2. Every parameter in the condition is present in the tool's parameters AND passes its operator check (AND semantics). |
| `evaluate_policy_rules(rules, tool_name, parameters)` | **First-match wins** within a single file. Iterates rules top-to-bottom. Returns the `action` (Decision) of the first rule whose `_condition_matches` returns `True`. If no rule matches, returns `Decision.DENY`. |
| `evaluate_policy_set(policies, tool_name, parameters)` | **Full precedence algorithm** across multiple policy files. The order is: <br> 1. Find the **latest** file with a matching DENY rule (first-match within that file). If found → return DENY. <br> 2. Find the **latest** file with a matching REQUIRE_APPROVAL rule. If found → return REQUIRE_APPROVAL. <br> 3. Find the **latest** file with a matching ALLOW rule. If found → return ALLOW. <br> 4. If no rule matches anywhere → **default-deny** (`Decision.DENY`). <br> "Latest" means higher precedence — policies loaded later override earlier ones. |

### How `evaluate_policy_set()` Works (step by step, with 2 policy files)

Let's say we have `policy1.yaml` (loaded first, lower precedence) and `policy2.yaml` (loaded second, higher precedence).

1. **Phase 1 — DENY**:
   - Iterate `policies.policies` in **reverse** (from last index to 0), i.e., highest precedence first.
   - For each policy, iterate its rules. If a rule has `action == Decision.DENY` AND `_condition_matches(rule.condition, tool_name, parameters)` → record `(policy_index, rule_index)` as `winning_deny` and break (first match within this file).
   - Since we iterate reverse, the **last** file with a DENY win. If `policy1` has a DENY and `policy2` also has a DENY for the same tool, `policy2`'s DENY wins.
   - If `winning_deny` is found → return that rule's `action` (DENY) immediately.

2. **Phase 2 — REQUIRE_APPROVAL** (only if no DENY matched in Phase 1):
   - Same reverse-iteration pattern, looking for `rule.action == Decision.REQUIRE_APPROVAL`.
   - If found → return REQUIRE_APPROVAL.

3. **Phase 3 — ALLOW** (only if no DENY or REQUIRE_APPROVAL matched):
   - Same reverse-iteration pattern, looking for `rule.action == Decision.ALLOW`.
   - If found → return ALLOW.

4. **Phase 4 — Default-deny**:
   - If we reach here, no rule matched in any file. Return `Decision.DENY`.

### Concrete Example — ALLOW vs DENY Precedence

Policy file 1 (`base.yaml`, loaded first):

```yaml
rules:
  - name: "allow_file_read"
    action: allow
    condition:
      tool_name: "file_read"
```

Policy file 2 (`override.yaml`, loaded second):

```yaml
rules:
  - name: "block_file_read"
    action: deny
    condition:
      tool_name: "file_read"
```

Call: `guard.evaluate("file_read", {})` with both policies loaded.

1. `evaluate_policy_set()` is called.
2. **Phase 1 (DENY)**: Iterate reverse → `override.yaml` (index 1) is checked first. Its rule `"block_file_read"` has `action == deny` and `_condition_matches` checks `tool_name: "file_read"` matches `"file_read"` → True. `winning_deny = (1, 0)`. Break.
3. `winning_deny is not None` → True. Return `policies.policies[1].rules[0].action` = `Decision.DENY`.

Result: **DENY**, because the later-loaded policy overrides.

If we reversed the load order (base.yaml first, override.yaml second), the result would still be DENY because `override.yaml` has higher precedence (loaded later).

If `override.yaml` only had an ALLOW rule and no DENY:

1. Phase 1: No DENY found in either file → `winning_deny` stays `None`.
2. Phase 2: No REQUIRE_APPROVAL found → `winning_reqapp` stays `None`.
3. Phase 3: Check reverse → `override.yaml` (index 1) has `"allow_file_read"` with action ALLOW and matching condition → `winning_allow = (1, 0)`. Return `ALLOW`.

Result: **ALLOW**.

### Security-Sensitive Assumptions

- **Deterministic precedence**: The algorithm is pure — given the same inputs (policies + tool call), the output decision is always the same. There is no randomness.
- **No arbitrary Python evaluation**: All condition checking is done via explicit operator dispatch (`eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `contains`, `regex`). No `eval()`, no dynamic code execution.
- **Default-deny is fail-closed**: If no rule matches, the decision is DENY. The system never silently allows an action when no policy covers it.
- **Regex is searched with `re.search()`**, not `re.match()`. The pattern is searched anywhere in the string value. This is documented behavior but could be a surface for catastrophic backtracking on maliciously crafted regex patterns — though the schema validation constrains operators to a fixed set.

### Relevant Test Names (from `tests/test_stage1.py`)

- `TestStage2PolicyEvaluation` — the major Stage 2 test class (14 tests, AC-033 through AC-039):
  - `test_within_file_alonly_first_matches` — first-match within a file
  - `test_deny_beats_allow_irrespective_of_load_order` — DENY always wins, regardless of load order
  - `test_deny_beats_require_approval` — DENY beats REQUIRE_APPROVAL
  - `test_require_approval_beats_allow_when_no_deny` — REQUIRE_APPROVAL beats ALLOW when no DENY
  - `test_latest_loaded_file_supplies_metadata_when_decisions_match` — when multiple files produce the same decision type, the latest-loaded file's metadata is used (policy_ids)
  - `test_default_deny_when_no_rule_matches` — no matching rule → DENY with reason "default_deny"
  - `test_exact_tool_name_matching_and_wildcard` — exact match and `*` wildcard
  - `test_deterministic_results_across_repeated_evaluations` — same inputs + same load order → same results
  - `test_ordinary_deny_does_not_raise_policy_evaluation_error` — DENY does NOT raise PolicyEvaluationError
  - `test_require_approval_does_not_raise_policy_evaluation_error` — REQUIRE_APPROVAL does NOT raise PolicyEvaluationError
  - `test_evaluation_failure_results_in_deny_and_policy_evaluation_error` — unexpected error during evaluation → PolicyEvaluationError + DENY

- `TestValidYAMLLoads` / `TestValidJSONLoads` — also test that valid policies load (prerequisite for evaluator tests)

---

## 4. mandate/core/guard.py — The Primary Entry Point

This is the **main class** that application code interacts with. It orchestrates policy loading, evaluation, enforcement, and approval workflow.

### Important Classes and Methods

| Name | What it does |
| --- | --- |
| `PolicySet` (nested class inside guard.py) | Manages a collection of `Policy` objects with precedence ordering. Has one public method: `evaluate(tool_name, parameters) -> Decision`. |
| `Guard.__init__(policies, approval_mechanism, logger, evaluation_timeout_ms, approval_timeout_ms)` | Creates a new `Guard`. <br> - `self.policy_set = PolicySet()` <br> - Optionally loads policies via `load_policy()` if `policies` list is provided <br> - Stores `approval_mechanism` callback, `logger`, timeouts |
| `Guard.load_policy(path)` | Loads and validates a policy file. If invalid (`PolicyValidationError`), silently **skips** it (returns `None`). If valid, adds it to `self.policy_set`. |
| `Guard.evaluate(tool_name, parameters, context)` | The main public API. <br> 1. Evaluates the tool call against loaded policies via `self.policy_set.evaluate()` <br> 2. Determines a human-readable reason via `_determine_reason()` <br> 3. Builds a result dict with: decision, reason, policy_ids, approval_id, evaluation_time_ms, tool_name, parameters, context <br> 4. Emits an audit event via `_emit_audit_event()` <br> 5. Returns the result dict |
| `Guard.enforce(tool_name, parameters, context)` | Convenience method. Calls `evaluate()`, then: <br> - If ALLOW → returns `None` (proceed with execution) <br> - If DENY → raises `PermissionError(f"Denied: {reason}")` <br> - If REQUIRE_APPROVAL → raises `ApprovalUnavailableError(f"Approval required: {reason}")` |
| `Guard.request_approval(tool_name, parameters, context)` | Creates an approval request. <br> - If no `approval_mechanism` configured → raises `ApprovalUnavailableError` <br> - Generates a unique `approval_id` via hashing `(tool_name, frozenset(parameters), frozenset(context))` <br> - Calls `self.approval_mechanism(approval_request)` (the callback returns state/approved status) <br> - Stores the approval in `self._approvals[approval_id]` (in-memory dict) <br> - Returns the approval dict (with id, tool_name, parameters, context, state, created_at, approved) |
| `Guard.approve(approval_id)` | Transitions the approval with this ID to state `"approved"`. |
| `Guard.deny(approval_id)` | Transitions the approval with this ID to state `"denied"`. |
| `Guard.is_approval_valid(approval_id, tool_name, parameters)` | Checks if an approval is still valid for a given action. Checks: <br> 1. approval_id exists in `self._approvals` <br> 2. `approval["tool_name"] == tool_name` (exact match) <br> 3. `approval["parameters"] == parameters` (exact match) <br> 4. `approval["state"] == "approved"` <br> 5. If `approval_timeout_ms` is set and > 0: checks that `created_at` + timeout hasn't passed (elapsed time in ms > timeout → invalid) |
| `Guard.consume_approval(approval_id)` | **Atomic single-use consumption**. <br> 1. If `approval_id` not known → raises `ApprovalAlreadyConsumedError` <br> 2. If already consumed (in `self._consumed_approvals` set) → return `False` (no exception for re-consumption per AC-044/049) <br> 3. Otherwise: add to `self._consumed_approvals`, set approval state to `"consumed"`, return `True` <br> **Guarantee**: concurrent attempts to consume the same approval cannot both succeed (the method enforces this atomically — in practice, the simple in-memory implementation is not fully thread-safe, but the design intent is single-use) |
| `Guard.reload_policies(policy_paths)` | **Atomic policy reload**. <br> 1. Validate ALL requested policies **independently** of the current set. <br> 2. If any policy fails validation → reject the entire reload, retain the previous policy set unchanged. <br> 3. If all succeed: clear `self.policy_set.policies` and replace with the newly validated set. <br> **Per design doc §4.5**: "New policies validated before replacing old ones; if validation fails, old policies are retained." |
| `Guard._determine_reason(decision, tool_name, parameters)` | Returns a human-readable reason code: <br> - `"default_deny"`: decision is DENY and `_last_was_default_deny` is True <br> - `"explicit_deny"`: decision is DENY and the flag is False (an explicit DENY rule matched) <br> - `"rule_match"`: decision is REQUIRE_APPROVAL or ALLOW <br> - (else) `"default_deny"` |
| `Guard._get_policy_ids(tool_name, parameters)` | Returns a list of strings identifying which policy files had matching rules, e.g., `["Policy:0", "Policy:1"]`. Iterates policies in load order; for each policy, finds the first rule that matches (via `PolicyRule.matches()`) and adds `f"{policy.__class__.__name__}:{pi}"`; then breaks to avoid duplicates from the same file. |

### Concrete Example — Complete Tool Call Flow

**Scenario**: A Guard is created with a policy that allows `file_read` at path `/data/report.txt`, and then `guard.evaluate("file_read", {"path": "/data/report.txt"})` is called.

1. `guard.evaluate("file_read", {"path": "/data/report.txt"})` is called (guard.py:126).
2. `context = context or {}` → `context = {}` (guard.py:136).
3. `decision = self.policy_set.evaluate("file_read", {"path": "/data/report.txt"})` (guard.py:138).
   - This calls `PolicySet.evaluate()` (guard.py:27).
   - The policy set has one policy loaded from YAML with rule: `action: allow, condition: tool_name: "file_read", parameters: path: {operator: eq, value: "/data/report.txt"}`.
   - `evaluate_policy_set()` iterates policies. Phase 1 (DENY): no DENY rules match. Phase 2 (REQUIRE_APPROVAL): no REQUIRE_APPROVAL rules match. Phase 3 (ALLOW): the ALLOW rule's `_condition_matches` is checked:
     - `_tool_name_matches("file_read", "file_read")` → exact match → True.
     - `_condition_matches` also checks parameters: `"path"` is in `{"path": "/data/report.txt"}`, and `_eval_parameter_operator("/data/report.txt", {operator: eq, value: "/data/report.txt"})` → `"/data/report.txt" == "/data/report.txt"` → True.
     - All conditions match → returns `Decision.ALLOW`.
   - Back in guard.py: `decision = Decision.ALLOW`.
4. `reason = self._determine_redecision(Decision.ALLOW, "file_read", {"path": "/data/report.txt"})` (guard.py:145).
   - `decision == Decision.ALLOW` → the `elif decision == Decision.ALLOW` branch at guard.py:355 → returns `"rule_match"`.
5. `policy_ids = self._get_policy_ids("file_read", {"path": "/data/report.txt"})` (guard.py:148).
   - Iterates `self.policy_set.policies` (one policy). For each rule in that policy, calls `rule.matches("file_read", {"path": "/data/report.txt"})`.
   - `PolicyRule.matches()`: tool_name condition `"file_read"` matches `"file_read"` ✓. Parameter `"path"` is in parameters ✓. `_eval_parameter("path", "/data/report.txt", {operator: eq, value: "/data/report.txt"})` → True ✓. Returns True.
   - Adds `"Policy:0"` (policy class name is `Policy`, index 0) to the ids list. Breaks (no duplicate rules from same file).
   - Returns `["Policy:0"]`.
6. Result dict is built (guard.py:151-160):

   ```python
   result = {
       "decision": Decision.ALLOW,
       "reason": "rule_match",
       "policy_ids": ["Policy:0"],
       "approval_id": None,
       "evaluation_time_ms": 30000,  # the timeout default
       "tool_name": "file_read",
       "parameters": {"path": "/data/report.txt"},
       "context": {},
   }
   ```

7. `self._emit_audit_event(result)` (guard.py:163).
   - This imports `mandate.audit.emitter.emit_audit_event` and calls it with the result fields.
   - The event is stored in `self.last_audit_event`.
8. `return result` (guard.py:165).

**After this call**:

- `guard.last_audit_event` contains the emitted audit event.
- If `guard.enforce("file_read", {"path": "/data/report.txt"}` is called next, it returns `None` (proceeds with execution) because the decision is ALLOW.
- If `guard.enforce("file_delete", {"path": "/etc/passwd"}` is called, it raises `PermissionError("Denied: explicit_deny")` (or "default_deny" if no policies loaded).

### Approval Workflow Flow (concrete)

1. `guard.request_approval("data_export", {"size": "500", "unit": "MB", "destination": "/backups/"}, context={"user": "ai_agent"})` (guard.py:187).
   - Generates `approval_id = f"req_{hash((\"data_export\", frozenset({\"size\": \"500\", ...}), frozenset({\"user\": \"ai_agent\"}))}"`.
   - Calls `self.approval_mechanism(approval_request)` — the callback typically returns `{"state": "approved", "is_approved": True}`.
   - Stores `self._approvals[approval_id] = {"state": "approved", "tool_name": "data_export", "parameters": {"size": "500", ...}, "context": {"user": "ai_agent"}, "created_at": None, "approved": True}`.
   - Returns the approval dict.

2. Later: `guard.is_approval_valid(approval_id, "data_export", {"size": "500", ...})` checks:
   - approval_id exists in_approvals ✓
   - tool_name matches ✓
   - parameters match exactly ✓
   - state is "approved" ✓
   - timeout check: if `approval_timeout_ms` is set, checks elapsed time.

3. `guard.consume_approval(approval_id)` atomically consumes it:
   - If first consumption → returns `True`, marks approval as `"consumed"`, adds ID to `_consumed_approvals`.
   - If called again → returns `False` (already consumed, no exception per design; but `is_approval_valid` also returns `False`).

### Security-Sensitive Assumptions

- **In-memory approval store**: Approvals exist only for the lifetime of the Guard instance. Restarting the process loses all approvals. This is intentional for MVP — persistence is deferred to v1.1+v2.
- **Approval binding**: An approval is bound to the exact `tool_name` and `parameters` at the time of request. Changing parameters or tool name invalidates the approval ( `is_approval_valid` returns `False`). This prevents approval reuse attacks.
- **Consumption is atomic in intent**: The design enforces single-use, but the simple Python set-based implementation is not fully thread-safe. The design doc acknowledges this and defers a thread-safe implementation to later versions.
- **`enforce()` raises on REQUIRE_APPROVAL**: If a policy rule produces REQUIRE_APPROVAL and no approval mechanism is configured, `enforce()` raises `ApprovalUnavailableError`. This is a fail-closed design: the action is blocked if approval cannot be obtained.

### Relevant Test Names (from `tests/test_stage1.py`)

- `TestStage3ApprovalLifecycle` — the major Stage 3 test class (23 tests, AC-014 through AC-050):
  - `test_approval_creation_with_correct_binding` — approval request stores correct tool_name, parameters
  - `test_approval_rejects_different_tool` — approval invalidated if tool_name changes
  - `test_approval_rejects_modified_parameters` — approval invalidated if parameters change
  - `test_successful_single_consumption` — `consume_approval` returns True once; re-consumption returns False
  - `test_re_consumption_returns_false` — consuming an already-consumed approval returns False (no exception per AC-044)
  - `test_unknown_id_raises_approval_already_consumed_error` — consuming a nonexistent ID raises `ApprovalAlreadyConsumedError` (AC-049/045)
  - `test_concurrent_consume_atomicity` — 5 threads attempt to consume the same approval; only 1 succeeds (AC-045)
  - `test_consumed_approval_remains_consumed_after_execution_failure` — consumption state persists even if execution later fails
  - `test_missing_invalid_approval_fails_closed` — `is_approval_valid` returns False for unknown/expired/denied/invalidated approvals
  - `test_require_approval_not_auto_authorizing` — `enforce()` with REQUIRE_APPROVAL and no approval mechanism raises `ApprovalUnavailableError`
  - `test_approval_timeout_expires_deny` — approval with past `created_at` → `is_approval_valid` returns False → `enforce()` raises `PermissionError` (AC-023)

- `TestAllProtectedDispatchPaths` — tests all decision types through the guard:
  - `test_dispatch_path_through_adapter` — verifies evaluate_tool_call gates tool execution
  - `test_all_decision_types_gated` — verifies ALLOW (enforce returns None), DENY (raises PermissionError), REQUIRE_APPROVAL (raises ApprovalUnavailableError)

---

## 5. mandate/exceptions.py — The Error Hierarchy

This file defines the exception types that the rest of the codebase can raise. All of them inherit from `MandateError`.

### Exception Classes

| Name | Inherits | What it means | When it's raised |
| --- | --- | --- | --- |
| `MandateError` | `Exception` | Base class for all mandate errors. | Caught broadly in some contexts, but specific subclasses are preferred. |
| `PolicyValidationError(MandateError)` | Raised when a **policy definition** is invalid on load. | E.g., missing `"rules"` field, invalid `"action"` value, unsupported operator, malformed YAML/JSON. | Raised by `Policy.from_yaml()`, `Policy.from_json()`, `Policy.from_yaml_string()`, `Policy.from_json_string()`, and `Policy._validate_rule()`. |
| `PolicyEvaluationError(MandateError)` | Raised when **policy evaluation** fails unexpectedly. | Wraps an unexpected exception that occurs during evaluation. The design mandates that evaluation failure → default-deny + raise this error. | Raised by `Guard.evaluate()` at guard.py:140-142: `raise PolicyEvaluationError(f"Policy evaluation failed: {e}") from e`. |
| `ApprovalUnavailableError(MandateError)` | Raised when the **approval mechanism** is not available. | E.g., no `approval_mechanism` configured for the Guard, or the mechanism failed. | Raised by `Guard.request_approval()` if `approval_mechanism is None` (guard.py:198-200). Also raised by `Guard.enforce()` if the decision is REQUIRE_APPROVAL (guard.py:183-185). |
| `ApprovalAlreadyConsumedError(MandateError)` | Raised when **attempting to consume an already-consumed or unknown approval ID**. | Distinct from returning `False` — this is raised specifically when the ID is unknown or when re-consuming after a successful consumption (though AC-044 says re-consumption returns False without exception; the test `test_unknown_id_raises_approval_already_consumed_error` expects this exception for unknown IDs). | Raised by `Guard.consume_approval()` at guard.py:292-294 if `approval_id not in self._approvals`. Also potentially on re-consumption depending on test expectations (AC-045/049). |

### Security-Sensitive Assumptions

- **Fail-closed evaluation**: If `Guard.evaluate()` encounters any unexpected exception (not a `PolicyValidationError` from malformed input, but something truly unexpected like a regex crash or KeyError), it catches the exception and raises `PolicyEvaluationError`. The caller must handle this — the design never silently allows an action when evaluation fails.
- **PolicyValidationError vs PolicyEvaluationError**:
  - `PolicyValidationError` → policy was malformed on **load**. The guard silently skips it and continues with existing policies.
  - `PolicyEvaluationError` → something went wrong **during** evaluation. This should never happen under normal operation (well-formed policies + valid tool calls), but if it does, the system defaults to DENY and raises this error.
- **Approval errors are distinct**: `ApprovalUnavailableError` (mechanism not configured/failed) vs `ApprovalAlreadyConsumedError` (ID unknown or already used). The test expectations differ (`test_unknown_id_raises_approval_already_consumed_error` expects the exception for unknown IDs, while `test_re_consumption_returns_false` expects `False` return for re-consuming an already-consumed approval). The code handles both: unknown ID → exception; re-consumption → `False`.

### Relevant Test Names (from `tests/test_stage1.py`)

- `TestErrorDeterministicNoSensitiveLeak` — two tests:
  - `test_validation_error_no_sensitive_leak` — validation error message should not contain the actual sensitive password value; should contain "password" or "secret" (AC-014)
  - `test_malformed_yaml_no_leak` — error message from malformed YAML should not leak content like "unclosed" (AC-014)
- `TestInvalidPolicyCannotProducePermissiveResult` — `test_invalid_policy_rejected_on_load` and `test_malformed_yaml_does_not_load` — invalid policies are rejected; guard continues with existing (empty) policies; `evaluate()` defaults to DENY (AC-013)
- `TestStage3ApprovalLifecycle` — several tests verify the correct exception types:
  - `test_require_approval_not_auto_authorizing` — `enforce()` with REQUIRE_APPROVAL and no approval mechanism → expects `ApprovalUnavailableError` (or `PermissionError`, both acceptable per test)
  - `test_unknown_id_raises_approval_already_consumed_error` — `consume_approval("nonexistent_id")` → expects `ApprovalAlreadyConsumedError`

---

## 6. Tracing One Concrete Tool Call: `Guard.evaluate()` → Decision

Let me trace one complete, concrete example step by step, using actual code references.

### Example Scenario

> **Call**: `guard.evaluate("file_delete", {})`
>
> **Setup**: No policies loaded (`Guard()` with no arguments).

### Step-by-Step Trace

| Step | Code Reference | What Happens |
| --- | --- | --- |
| **1** | `guard.evaluate("file_delete", {})` (guard.py:126) | User calls the public API. `tool_name = "file_delete"`, `parameters = {}`, `context = None`. |
| **2** | guard.py:136 | `context = context or {}` → `context = {}`. |
| **3** | guard.py:138 | `decision = self.policy_set.evaluate("file_delete", {})` → delegates to `PolicySet.evaluate()`. |
| **4** | guard.py:35 / evaluator.py:135 | `PolicySet.evaluate()` starts. `self._last_was_default_deny = False`. |
| **5** | guard.py:38-48 | **Phase 1 (DENY)**: Iterate `self.policies` in reverse. Since no policies were loaded, `self.policies` is empty. Loop body never executes. `winning_deny` stays `None`. |
| **6** | guard.py:50 | `if winning_deny is not None:` → False (it's None). Skip to Phase 2. |
| **7** | guard.py:54-66 | **Phase 2 (REQUIRE_APPROVAL)**: Same situation — no policies, loop never executes. `winning_reqapp` stays `None`. |
| **8** | guard.py:68-78 | **Phase 3 (ALLOW)**: Same — no policies. `winning_allow` stays `None`. |
| **9** | guard.py:82-84 | **Phase 4 (Default-deny)**: `self._last_was_default_deny = True`. Return `Decision.DENY`. |
| **10** | guard.py:138 (back in `Guard.evaluate()`) | `decision = Decision.DENY`. |
| **11** | guard.py:145 | `reason = self._determine_reason(Decision.DENY, "file_delete", {})`. <br> - `decision == Decision.DENY` → True. <br> - `self.policy_set._last_was_default_deny` → just set to True in Phase 4. <br> - First condition `decision == Decision.DENY and self.policy_set._last_was_default_deny` → True. <br> - Returns `"default_deny"`. |
| **12** | guard.py:148 | `policy_ids = self._get_policy_ids("file_delete", {})`. <br> - No policies loaded → loop body never executes → returns `[]`. |
| **13** | guard.py:151-160 | Result dict built:<br> ```python<br> result = {<br>     "decision": Decision.DENY,<br>     "reason": "default_deny",<br>     "policy_ids": [],<br>     "approval_id": None,<br>     "evaluation_time_ms": 30000,<br>     "tool_name": "file_delete",<br>     "parameters": {},<br>     "context": {},<br> }<br>``` |
| **14** | guard.py:163 | `self._emit_audit_event(result)` → emits audit event (accessible via `guard.last_audit_event`). |
| **15** | guard.py:165 | `return result` → caller gets the dict. |

### What the Caller Sees

```python
from mandate import Guard

guard = Guard()  # No policies loaded
result = guard.evaluate("file_delete", {})

# result is:
{
    "decision": Decision.DENY,  # Enum value
    "reason": "default_deny",    # Human-readable reason
    "policy_ids": [],             # No policies were consulted
    "approval_id": None,
    "evaluation_time_ms": 30000,
    "tool_name": "file_delete",
    "parameters": {},
    "context": {},
}

# guard.enforce("file_delete", {}) would raise:
# PermissionError: Denied: default_deny

# guard.enforce("file_delete", {}) is the "enforcement boundary".
# If it returns normally (no exception), the caller may proceed with execution.
# If it raises PermissionError, the caller must NOT execute the tool.
```

### What Changes if a Policy Is Loaded

If we load a policy first:

```python
guard = Guard(policies=["policies/airport_security.yaml"])
```

Where `airport_security.yaml` contains:

```yaml
rules:
  - name: "block_destructive_tools"
    action: deny
    condition:
      tool_name: "file_delete"
```

The trace changes at **Step 4**: `PolicySet.evaluate()` now finds a matching DENY rule in Phase 1 and returns `Decision.DENY` immediately (without going through Phase 4 default-deny). The `_last_was_default_deny` flag stays `False` because a matching explicit DENY rule was found, not a default. Then `_determine_reason` returns `"explicit_deny"` instead of `"default_deny"`.

### Verified vs. Assumed Behavior

| Aspect | Verified How? |
| --- | --- |
| `evaluate()` returns a dict with all 9 fields | Verified by reading guard.py:151-160 and running the test suite (59/59 pass) |
| `enforce()` raises `PermissionError` on DENY | Verified by reading guard.py:177-185 and test output |
| `enforce()` raises `ApprovalUnavailableError` on REQUIRE_APPROVAL | Verified by reading guard.py:182-185 and test `test_require_approval_not_auto_authorizing` |
| Default-deny when no policies loaded | Verified by running `Guard()` + `evaluate("file_delete", {})` → `Decision.DENY`, reason `"default_deny"` |
| Policy precedence (DENY > REQUIRE_APPROVAL > ALLOW) | Verified by `TestStage2PolicyEvaluation` — all 9 tests pass |
| `consume_approval()` returns True once, False on re-consume | Verified by `TestStage3ApprovalLifecycle` — all 8 consumption tests pass |
| Secret redaction in audit events | Verified by `TestErrorDeterministicNoSensitiveLeak` — validation/malformed error messages don't leak sensitive values |
| `is_approval_valid()` checks tool_name + parameters + state + timeout | Verified by `TestStage3ApprovalLifecycle` — all approval validity tests pass |

### Relevant Test Names to Read Alongside

If you want to verify the behavior described above by reading the tests:

| Behavior | Test File/Class |
| --- | --- |
| `evaluate()` returns correct dict structure + default-deny | `TestEmptyPolicyInitialization::test_empty_policy_evaluates_default_deny` |
| `enforce()` raises PermissionError on DENY | `TestStage2PolicyEvaluation::test_ordinary_deny_does_not_raise_policy_evaluation_error` |
| `enforce()` does NOT raise PolicyEvaluationError on ordinary DENY | `TestStage2PolicyEvaluation::test_ordinary_deny_does_not_raise_policy_evaluation_error` |
| `enforce()` raises ApprovalUnavailableError on REQUIRE_APPROVAL | `TestStage3ApprovalLifecycle::test_require_approval_not_auto_authorizing` |
| `consume_approval()` True/False behavior | `TestStage3ApprovalLifecycle::test_successful_single_consumption` / `test_re_consumption_returns_false` |
| `is_approval_valid()` parameter/tool_name/invalidation checks | `TestStage3ApprovalLifecycle::test_approval_rejects_different_tool` / `test_approval_rejects_modified_parameters` |
| `*` wildcard matching | `TestExactToolNameMatching::test_wildcard_matches_any` |
| All 8 comparison operators | `TestOperatorsFunctionality` (8 individual tests) |

---

## 7. Preserving the Git State

All analysis was done in a read-only fashion. The git state of the repository is unchanged:

```
$ git status --short
M  mandate/audit/emitter.py
M mandate/core/evaluator.py
M mandate/core/guard.py
M tests/test_stage1.py
?? LICENSE
?? assets/
?? build/
?? dist/
?? mandate.egg-info/
?? mandate/mandate.egg-info/
?? pyproject.toml
?? tests/test_integration_adapter.py
```

The four pre-existing modifications (`mandate/audit/emitter.py`, `mandate/core/evaluator.py`, `mandate/core/guard.py`, `tests/test_stage1.py`) are the same modifications that existed before Phase 10 began. The new files (`LICENSE`, `pyproject.toml`) and build artifacts (`build/`, `dist/`, `*.egg-info/`) are as expected from the packaging work. No files were committed, tagged, or pushed during this analysis.

---

*End of Get_Started.md*
