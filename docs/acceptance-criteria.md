# Mandate Measurable Acceptance Criteria

## Overview
These acceptance criteria define the measurable thresholds that must be met for the Mandate MVP to be considered complete and ready for FRIDAY integration. Each criterion is testable and observable.

## 1. Core Functionality Criteria

### Criteria 1.1: Policy Evaluation Produces Correct Decisions
| ID | Test | Pass Condition |
|---|---|---|
| `AC-001` | ALLOW decision | When a policy rule with `action: allow` matches the tool call, `guard.evaluate()` returns `Decision.ALLOW` |
| `AC-002` | DENY decision | When a policy rule with `action: deny` matches the tool call, `guard.evaluate()` returns `Decision.DENY` |
| `AC-003` | REQUIRE_APPROVAL decision | When a policy rule with `action: require_approval` matches the tool call, `guard.evaluate()` returns `Decision.REQUIRE_APPROVAL` and sets `approval_id` |
| `AC-004` | Default-deny | When no policy rule matches the tool call, `guard.evaluate()` returns `Decision.DENY` |

### Criteria 1.2: Parameter Conditions Work Correctly
| ID | Test | Pass Condition |
|---|---|---|
| `AC-005` | `eq` operator | `guard.evaluate(tool_name="file_read", parameters={"path": "/data/report"}, condition={"operator": "eq", "value": "/data/report"})` matches |
| `AC-006` | `neq` operator | `guard.evaluate(tool_name="file_delete", parameters={"path": "/etc/passwd"}, condition={"operator": "neq", "value": "file_read"})` matches when tool_name ≠ value |
| `AC-007` | `gt` operator | `guard.evaluate(tool_name="data_export", parameters={"size": 150}, condition={"operator": "gt", "value": 100})` matches when size > 100 |
| `AC-008` | `lt` operator | `guard.evaluate(tool_name="data_export", parameters={"size": 50}, condition={"operator": "lt", "value": 100})` matches when size < 100 |
| `AC-009` | `contains` operator | `guard.evaluate(tool_name="file_read", parameters={"path": "/tmp/foo"}, condition={"operator": "contains", "value": "/tmp"})` matches |
| `AC-010` | `regex` operator | `guard.evaluate(tool_name="http_get", parameters={"url": "/api/data"}, condition={"operator": "regex", "value": "^/api/"})` matches |

### Criteria 1.3: Wildcard Tool Name Matching
| ID | Test | Pass Condition |
|---|---|---|
| `AC-011` | `*` matches all | `guard.evaluate(tool_name="anything", parameters={}, condition={"tool_name": "*"})` matches |
| `AC-012` | Exact match / wildcard match | `guard.evaluate(tool_name="file_read", parameters={}, condition={"tool_name": "file_read"})` matches; `guard.evaluate(tool_name="any_tool", parameters={}, condition={"tool_name": "*"})` matches any tool name |
| `AC-013` | Wildcard `*` matches any tool | `guard.evaluate(tool_name="http_get", parameters={}, condition={"tool_name": "*"})` matches `http_get` |

## 2. Approval Workflow Criteria

### Criteria 2.1: Approval Lifecycle States
| ID | Test | Pass Condition |
|---|---|---|
| `AC-014` | Pending state | `guard.request_approval()` returns approval with `state == "pending"` |
| `AC-015` | Approve transitions state | `guard.approve(approval.id)` changes state to `"approved"` |
| `AC-016` | Deny transitions state | `guard.deny(approval.id)` changes state to `"denied"` |
| `AC-017` | Expired state | After timeout, approval state becomes `"expired"`; action is DENYd |

### Criteria 2.2: Approval Binding and Invalidation
| ID | Test | Pass Condition |
|---|---|---|
| `AC-018` | Approval bound to action | `guard.is_approval_valid(approval.id, "file_read", {"path": "/data/x"})` returns True only for exact matching parameters |
| `AC-019` | Invalidation on parameter change | `guard.is_approval_valid(approval.id, "file_read", {"path": "/data/y"})` returns False when parameters differ |
| `AC-020` | Invalidation on tool name change | `guard.is_approval_valid(approval.id, "file_write", {"path": "/data/x"})` returns False when tool_name differs |
| `AC-021` | New approval required after change | After parameter change, `guard.request_approval()` with new parameters returns a new approval ID |

### Criteria 2.3: Approval Unavailability
| ID | Test | Pass Condition |
|---|---|---|
| `AC-022` | Unavailable approval → DENY | When approval mechanism is unavailable, REQUIRE_APPROVAL actions are DENYd |
| `AC-023` | Approval timeout → DENY | After timeout, re-evaluation yields DENY, not ALLOW |

## 3. Audit Criteria

### Criteria 3.1: Structured Event Emission
| ID | Test | Pass Condition |
|---|---|---|
| `AC-024` | Event emitted for every evaluation | Every `guard.evaluate()` call produces an audit event accessible via `guard.last_audit_event` |
| `AC-025` | Event has minimum required fields | Event contains: `event_type`, `timestamp`, `tool_name`, `parameters`, `decision`, `reason`, `approval_id`, `policy_ids`, `evaluation_time_ms` |

### Criteria 3.2: Data Sanitization
| ID | Test | Pass Condition |
|---|---|---|
| `AC-026` | No secrets in audit events | Audit events never contain raw passwords, API keys, or token values |
| `AC-027` | Sensitive parameters redacted | Parameters matching secret patterns are replaced with `"<redacted>"` |
| `AC-028` | Large parameters truncated | Oversized parameter objects are truncated with `"truncated": true` flag |

### Criteria 3.3: FRIDAY JSONL Integration
| ID | Test | Pass Condition |
|---|---|---|
| `AC-029` | Event format compatible with JSONL | Emitted events are valid JSON that can be appended to a JSONL log file |
| `AC-030` | Adapter can proxy events | FRIDAY adapter receives events and writes them to FRIDAY's JSONL log without Mandate depending on FRIDAY's logging implementation |

## 4. Policy Criteria

### Criteria 4.1: Policy Validation and Loading
| ID | Test | Pass Condition |
|---|---|---|
| `AC-031` | Valid YAML loads successfully | Correct YAML policy file is loaded without error |
| `AC-032` | Invalid YAML rejected | Malformed YAML raises `PolicyValidationError`; guard continues with existing policies |
| `AC-033` | Policy rules evaluated top-to-first-match | First matching rule's action wins, regardless of order |

### Criteria 4.2: Policy Precedence
| ID | Test | Pass Condition |
|---|---|---|
| `AC-034` | Earlier files lower precedence | When two policies have conflicting rules for same tool and same decision type, the rule from the later-loaded file takes precedence; if conflict involves different decision types, severity order (DENY > REQUIRE_APPROVAL > ALLOW) determines the winner. |
| `AC-035` | Hot reload works | `guard.reload_policies()` re-reads files; new valid policies replace old ones; invalid ones are retained |

### Criteria 4.3: Evaluation Failure
| ID | Test | Pass Condition |
|---|---|---|
| `AC-036` | Evaluation failure → DENY | When policy evaluation fails (e.g., unexpected error, pathological regex), the guard defaults to DENY decision and raises `PolicyEvaluationError` |
| `AC-037` | Exception/type contract | `PolicyEvaluationError` is raised for unexpected policy-evaluation failures; `PolicyValidationError` is raised for invalid policy configuration on load. Ordinary DENY decisions and REQUIRE_APPROVAL decisions do not raise these exceptions. |

## 5. Security Criteria

### Criteria 5.1: Unauthorized Execution Blocked (Integration)
| ID | Test | Pass Condition |
|---|---|---|
| `AC-038` | Unguarded tool execution blocked (integration) | In the FRIDAY dispatch pipeline, a tool call that bypasses `guard.evaluate()` raises `PermissionError`; the tool does not execute. This test validates the FRIDAY adapter enforces the boundary, not the standalone library. |

### Criteria 5.2: Policy Conflict Resolution
| ID | Test | Pass Condition |
|---|---|---|
| `AC-039` | First-match precedence | Conflicting rules resolved by first-match; documented and deterministic |

### Criteria 5.3: Audit Logging Integrity
| ID | Test | Pass Condition |
|---|---|---|
| `AC-040` | No sensitive data leakage | Zero occurrences of passwords, API keys, or token values in 100 consecutive audit events (verified by regex scan) |

### Criteria 5.4: Approval Bypass Prevention
| ID | Test | Pass Condition |
|---|---|---|
| `AC-041` | REQUIRE_APPROVAL cannot be bypassed | Skipping approval flow for REQUIRE_APPROVAL action results in DENY, not ALLOW |
| `AC-042` | Stale approval invalidated | Using approval after action change results in invalid approval; new approval required |

## 6. Threshold for MVP Completion

The MVP is considered complete when **all** of the following are true:

- [ ] 50/50 acceptance criteria pass (AC-001 through AC-050)

## 7. Single-Use Consumption Criteria

### Criteria 7.1: Single-Use Consumption
| ID | Test | Pass Condition |
|---|---|---|
| `AC-043` | Single-use consumption | After `guard.consume_approval(approval.id)` returns `True`, the approval is marked as consumed and cannot authorize another execution with the identical tool_name, parameters, and context. |
| `AC-044` | Repeated consumption rejected | After an approval is consumed, `guard.consume_approval(approval.id)` returns `False` and does not raise an exception when attempted again. |
| `AC-045` | Concurrent double consumption prevented | Mandate enforces that concurrent attempts to consume the same approval cannot both succeed. Only one consumer may consume the approval. |
| `AC-046` | Expired/invalidated/rejected approvals blocked | Expired, denied, invalidated, or already-consumed approvals must never authorize execution. Any attempt results in a DENY decision and an `approval_consumed` or `approval_invalidated` reason code. |
| `AC-047` | Fresh authorization after execution failure | A retry after execution failure requires fresh authorization. Where applicable (REQUIRE_APPROVAL), a new approval must be requested; the previously consumed approval cannot be reused. |

### Criteria 7.2: Approval State Distinctions
| ID | Test | Pass Condition |
|---|---|---|
| `AC-048` | Consumed state | After `guard.consume_approval(approval.id)` returns `True`, the approval's state is marked as `consumed` and `guard.is_approval_valid(approval.id, tool_name, parameters)` returns `False`. |
| `AC-049` | Already-consumed rejection | Attempting `guard.consume_approval(approval.id)` on an already-consumed approval returns `False` and does not raise an exception (the approval was already consumed). |
| `AC-050` | State transitions | The approval lifecycle states are: `pending` → `approved` → `consumed`. States `denied`, `expired`, and `invalidated` are terminal and cannot transition to `consumed`.



- [ ] All security test matrix tests from threat-model.md pass
- [ ] FRIDAY adapter can route a tool call through the guard end-to-end
- [ ] Audit events are emitted and writable as JSONL
- [ ] No secrets leak in audit events across test scenarios
- [ ] Documentation (design, API, scope) is complete and published

Failed any of the above → MVP not complete; address failures before integration.