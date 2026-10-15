# Mandate Package and Module Structure

## Overall Layout

```
mandate/
├── __init__.py          # Package version, public API imports
├── core/                # Core authorization engine
│   ├── __init__.py
│   ├── guard.py         # Guard class - primary entry point
│   ├── policy.py        # Policy loading, validation, management
│   ├── evaluator.py     # Policy evaluation engine
│   └── types.py         # Shared type definitions
├── policies/            # Policy format definitions and validators
│   ├── __init__.py
│   ├── yaml_loader.py   # YAML policy loading with validation
│   ├── condition.py     # Condition expression evaluation
│   └── schema.py        # Policy JSON/YAML schema definition
├── approval/            # Approval workflow management
│   ├── __init__.py
│   ├── request.py       # Approval request lifecycle
│   ├── store.py         # In-memory approval store (MVP)
│   └── exceptions.py    # Approval-related exceptions
├── audit/               # Audit event emission
│   ├── __init__.py
│   ├── emitter.py       # Structured audit event emission
│   └── schema.py        # Audit event JSON schema
└── exceptions.py        # Custom exceptions used across the library
```

## Key Modules

### `mandate/__init__.py`
```python
# Public API exports
from mandate.core.guard import Guard
from mandate.core.types import (
    ALLOW, DENY, REQUIRE_APPROVAL,
    Decision, PolicyRule, EvaluationContext
)
from mandate.approval.request import ApprovalRequest
from mandate.audit.emitter import emit_audit_event
```

### `mandate/core/guard.py` - Primary Entry Point
The `Guard` class orchestrates policy evaluation and enforcement:
- `Guard()` - construct a new guard
- `Guard.load_policy(policy)` - load a validated Policy object
- `Guard.evaluate(tool_name, parameters, context)` - produce a Decision
- `Guard.enforce(tool_name, parameters, context)` - throw if not ALLOW
- `Guard.request_approval(tool_name, parameters, context)` - start approval flow
- `Guard.reload_policies()` - hot-reload all policy files

### `mandate/core/policy.py` - Policy Management
- `Policy.from_yaml(path)` - load and validate a YAML policy file
- `Policy.from_json(path)` - load and validate a JSON policy file
- `Policy.validate(data)` - validate policy dict against schema
- `Policy.rules` - iterable of PolicyRule objects

### `mandate/core/evaluator.py` - Evaluation Engine
The core evaluation logic:
- Rule matching with first-wins precedence
- Parameter condition evaluation (operators: eq, neq, gt, lt, gte, lte, contains, regex)
- Context integration
- Decision production (ALLOW/DENY/REQUIRE_APPROVAL)
- Error handling (evaluation failure → DENY)

### `mandate/types.py` - Shared Type Definitions
- `Decision` enum: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`
- `Action` enum: matching the three decision types
- `ComparisonOperator` enum: `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `contains`, `regex`
- `Pattern` type: string or compiled pattern for matching
- `EvaluationContext` dataclass: `tool_name`, `parameters`, `context`, `timestamp`
- `AuditEvent` dataclass: structured event with all required fields

### `mandate/policies/yaml_loader.py` - YAML Policy Loading
- Safe YAML loading (no `eval`, no arbitrary code execution)
- Schema validation on load
- Error translation to `PolicyValidationError`

### `mandate/policies/schema.py` - Policy Validation Schema
- Required fields per rule
- Valid action values
- Valid comparison operators
- Pattern syntax validation
- Error reporting with line/column positions

### `mandate/approval/request.py` - Approval Workflow
- `ApprovalRequest` dataclass: `id`, `tool_name`, `parameters`, `context`, `state`, `timestamp`, `timeout`
- `ApprovalStore` (in-memory for MVP):
  - `request_approval()` - create pending approval
  - `approve()/deny()` - transition state
  - `is_valid(approval_id, tool_name, parameters)` - check if approval matches current action
  - `expire()` - timeout handling
- Timeout configuration and expired state handling

### `mandate/approval/exceptions.py`
- `ApprovalError` base exception
- `ApprovalNotFoundError`
- `ApprovalExpiredError`
- `ApprovalInvalidatedError` - when action changes

### `mandate/audit/emitter.py` - Audit Event Emission
- `emit_decision_event(decision, evaluation_context, reason)` - emit structured event
- Event formatting to JSON (sandboxed/sanitized parameters)
- Integration hook for adapter to send to FRIDAY JSONL

### `mandate/audit/schema.py` - Audit Event JSON Schema
- Minimum required fields
- Sanitization rules
- Validation on event construction

### `mandate/exceptions.py` - Library Exceptions
- `MandateError` base exception
- `PolicyEvaluationError` - policy engine failure
- `PolicyValidationError` - invalid policy definition
- `ApprovalUnavailableError` - approval mechanism failure
- `PermissionError` - raised when DENY decision is enforced

## Design Rationale

1. **No `eval` anywhere**: All policy evaluation uses explicit operator dispatch, never dynamic code execution.
2. **Framework-agnostic**: Core modules have no FRIDAY dependencies. The adapter layer provides the FRIDAY connection.
3. **In-memory approval store for MVP**: No persistent approval store needed for initial release. The adapter can persist as needed.
4. **Small, focused modules**: Each module has a single responsibility and clear interfaces.
5. **Testable units**: Each module can be unit-tested in isolation.