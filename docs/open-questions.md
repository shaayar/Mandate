# Mandate Open Questions and Decisions Requiring Approval

## Overview
These are the design trade-offs and open questions that require your explicit approval before implementation begins. Each option presents trade-offs, and the user has approved Option A for all decisions.

---

## 1. Policy Format for MVP

### Options
| Option | Description |
|---|---|
| **A: JSON/YAML only** | Policies defined exclusively in JSON or YAML. No Python predicate support in MVP. |
| **B: JSON/YAML + Python predicates** | Policies in JSON/YAML plus optional Python callback functions for complex logic. |

### Approval: Option A (approved)
**Reasoning**: The MVP goal is a small, secure, framework-agnostic release. Supporting Python predicates requires defining a safe callback interface, avoiding `eval`, and adding significant complexity. deferring this to v2 keeps the MVP focused and the attack surface smaller.

---

## 2. Wildcard/Tool Name Matching

### Options
| Option | Description |
|---|---|
| **A: `*` wildcard matches any tool name** | `tool_name: "*"` matches any tool. Simple and comprehensive. |
| **B: Prefix matching only** | `tool_name: "file_"` matches tools starting with "file_"; no `*` wildcard. |
| **C: Exact string matching only** | `tool_name` must match exactly; no wildcard or prefix support. |

### Approval: Option A (approved)
**Reasoning**: Wildcards are essential for practical policy expression. `*` matching any tool + exact string matching gives maximum flexibility while remaining simple to implement and test. Exact-only matching (Option C) would be overly restrictive; prefix-only (Option B) is acceptable but less expressive. Note: prefix matching such as `file_*` is not supported in MVP unless explicitly approved in a future version.

---

## 3. Comparison Operators in Parameter Conditions

### Options
| Option | Operators Included |
|---|---|
| **A: Full set** | `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `contains`, `regex` |
| **B: Core numeric operators** | `eq`, `neq`, `gt`, `lt`, `gte`, `lte` |
| **C: String operators only** | `eq`, `neq`, `contains` |

### Approval: Option A (approved)
**Reasoning**: All 8 operators support the three representative tool categories comprehensively:
- `file_read`/`file_write`: `contains` (path segments), `eq` (exact path)
- `data_export`: `gt`/`lt` (size comparisons), `eq` (destination match)
- `http_get`/`http_post`: `regex` (URL patterns), `contains` (header values)

Excluding operators would limit policy expressivity without significant simplicity gain.

---

## 4. Approval Mechanism Implementation

### Options
| Option | Description |
|---|---|
| **A: Callback-based** | Adapter provides `f(approval_request) -> approval_result` callback. MVP uses a simple CLI prompt or env var for demo. |
| **B: HTTP endpoint** | Approval mechanism is an HTTP API that FRIDAY calls. More suitable for production UI. |
| **C: Database-driven** | Approval requests stored in DB; human responds via web UI. Heaviest setup. |

### Approval: Option A (approved)
**Reasoning**: Keeps Mandate framework-agnostic. The adapter implements the callback. For MVP demo, a simple CLI prompt or environment variable suffices. HTTP endpoint (Option B) and DB-driven (Option C) are deferred to v1.1/v2 when a production UI is needed.

---

## 5. Policy Precedence Across Files

### Options
| Option | Description |
|---|---|
| **A: Earlier files lower precedence** | Rules from earlier-loaded files are checked first; later files override. This means file[n] overrides file[n-1]. |
| **B: Later files lower precedence** | Rules from later-loaded files are checked first; earlier files override. Less intuitive but opposite convention. |
| **C: Single policy file only** | Only one policy file can be loaded at a time. No multi-file precedence. |

### Approval: Option A (approved)
**Reasoning**: This is the more intuitive model: base policies are loaded first (defaults), then override policies are loaded later (customizations). This allows FRIDAY integrations to declare `base.yaml` with default rules and `override.yaml` to override specific rules. Option C (single file) defeats the purpose of modular policies.

---

## 6. Base Policies Shipped with Mandate

### Options
| Option | Description |
|---|---|
| **A: No base policies** | Guard starts empty; user must explicitly load their own policies. Keeps library agnostic. |
| **B: minimal base policies** | Ship with a minimal set of base policies (e.g., `allow_read_only` for file_read) as documentation/example starting point. |

### Approval: Option A (approved)
**Reasoning**: Keeping Mandate truly framework-agnostic means no opinions on what policies are "correct." An empty guard starting state makes the contract clear: the caller defines the policies. Option B creates a de facto opinion and could confuse users who expect different defaults.

---

## 7. Evaluation Error Exception Type

### Options
| Option | Description |
|---|---|
| **A: `PolicyEvaluationError` subclass of `Exception`** | Specific exception type; adapter catches and translates. |
| **B: Generic `MandateError`** | All Mandate errors use a base `MandateError` subclass pattern. |
| **C: No exceptions; error codes only** | Errors returned as result objects, never raised as exceptions. |

### Approval: Option A (approved)
**Reasoning**: Python idiom to use specific exception types for error handling. Allows the adapter to catch `PolicyEvaluationError` specifically while letting other exceptions propagate. Option C (error codes) is less Pythonic; Option B is too generic to be useful.

---

## 8. Audit Event Sanitization Scope

### Options
| Option | Description |
|---|---|
| **A: Library-redacted + adapter-final say** | Mandate redacts known secret patterns (password, api_key, token, secret). Adapter controls final log output and can further sanitize. |
| **B: Adapter-full responsibility** | Mandate emits raw parameters; adapter is 100% responsible for sanitization. |
| **C: Library-redacted only, no adapter involvement** | Mandate redacts secrets; adapter passes events through unchanged. |

### Approval: Option A (approved)
**Reasoning**: Defense-in-depth. Mandate redacts common secret patterns as a baseline guarantee. The adapter then controls the final log output and can apply FRIDAY-specific redaction. Option B abandons the library's guarantee; Option C leaves no adapter control surface for FRIDAY-specific needs.

---

## 9. Tool Categories for MVP Integration

### Options
| Option | Description |
|---|---|
| **A: File system + data export + web request** | Three categories as designed in the MVP scope. |
| **B: File system only** | Only file tools (`file_read`, `file_write`, `file_delete`). Simpler but less coverage. |
| **C: File system + data export only** | Two categories, omits web request. Slightly narrower but sufficient for REQUIRE_APPROVAL demo. |

### Approval: Option A (approved)
**Reasoning**: All three categories demonstrate different aspects of the API:
- File system: basic ALLOW/DENY, parameter patterns (paths)
- Data export: REQUIRE_APPROVAL flow, large parameter conditions
- Web request: context-aware evaluation, URL pattern matching

Option B is too narrow; Option C is acceptable but misses the web request use case. Three categories provides the best demo coverage for an MVP.

---

## 10. JSON vs. YAML Policy Format

### Options
| Option | Description |
|---|---|
| **A: YAML primary, JSON supported** | YAML is the primary/preferred format; JSON also supported for round-tripping. |
| **B: JSON primary, YAML supported** | JSON is the primary format; YAML supported via conversion. |
| **C: YAML only** | Only YAML format supported; JSON not implemented. |

### Approval: Option A (approved)
**Reasoning**: YAML is more human-readable for policy documents, supports comments, and is the more common format for configuration policies. Supporting JSON ensures round-tripping and gives users a choice. The YAML loader uses `yaml.safe_load()` exclusively (no `eval`), so there's no security difference between formats.

---

## 11. Guard Initialization: Empty vs. With Policies

### Options
| Option | Description |
|---|---|
| **A: Empty guard by default** | `Guard()` creates a guard with no policies loaded. User must call `load_policy()` or pass `policies` constructor arg. |
| **B: Policies via constructor only** | `Guard(policies=[...])` is the only way to load policies; no `load_policy()` method. |
| **C: Auto-discover policies** | Guard auto-finds policy files in default locations/paths. |

### Approval: Option A (approved)
**Reasoning**: Keeps the API simple and explicit. The constructor can optionally accept policies, but the guard starts empty by default so there are no silent assumptions about what policies apply. Option B limits flexibility; Option C introduces magic behavior.

---

## 12. Version 0.1.0 Release Model

### Options
| Option | Description |
|---|---|
| **A: Source-only release** | Mandate is released as source code; users `pip install` from a git repo or install locally. |
| **B: Binary wheel** | Mandate is packaged as a pip wheel with pre-built binaries. |
| **C: Development-only** | Mandate is not published; used only in-source within FRIDAY. |

### Approval: Option A (approved)
**Reasoning**: The MVP is being built by an individual developer; source-only is the simplest distribution method. A wheel can be produced post-MVP if adoption requires it. Option B requires CI/CD setup; Option C limits external feedback.

---

## Summary - Decisions Approved

| # | Decision | User Approval |
|---|---|---|
| 1 | Policy format for MVP | A |
| 2 | Wildcard/tool_name matching | A |
| 3 | Comparison operators | A |
| 4 | Approval mechanism | A |
| 5 | Policy precedence across files | A |
| 6 | Base policies shipped | A |
| 7 | Evaluation error exception type | A |
| 8 | Audit event sanitization scope | A |
| 9 | Tool categories for MVP | A |
| 10 | JSON vs. YAML format | A |
| 11 | Guard initialization | A |
| 12 | Release model | A |

All 12 design decisions have been approved with Option A. The documentation below reflects these approved choices and serves as the baseline for implementation planning.