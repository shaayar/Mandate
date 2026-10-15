# Mandate MVP Scope and Out-of-Scope List

## 1. MVP Scope - Smallest Useful Release

The MVP focuses on demonstrating the core security value of Mandate as a reusable Python library that enforces authorization policies for AI agent tool calls before execution. The scope is intentionally limited to enable an individual developer to build, test, document, and demonstrate the first release within a reasonable timeframe.

### 1.1 Core Features (In Scope)

| Feature | Description |
|---|---|
| **Guard evaluation** | `guard.evaluate(tool_name, parameters, context)` produces ALLOW/DENY/REQUIRE_APPROVAL decisions |
| **Policy loading from YAML** | Policies defined in YAML format with rules, conditions, and actions |
| **Three decision types** | ALLOW (proceed), DENY (block), REQUIRE_APPROVAL (pending human approval) |
| **Parameter conditions** | Conditions on tool parameters using comparison operators (eq, neq, gt, lt, gte, lte, contains, regex) |
| **Wildcard tool_name matching** | `*` matches any tool; prefix patterns supported |
| **Default-deny** | Actions not covered by any ALLOW rule are denied |
| **Approval request/response** | `guard.request_approval()`, `guard.approve()`, `guard.deny()` |
| **Approval invalidation** | Approval invalidated when tool name or parameters change |
| **Structured audit events** | JSON events with sanitized parameters for every evaluation |
| **Policy validation on load** | Schema validation; invalid policies rejected |
| **Hot reload** | `guard.reload_policies()` re-reads policy files |
| **Error handling** | `PolicyEvaluationError`, `PolicyValidationError`, `ApprovalUnavailableError` |
| **Three representative tool categories** | File system, data export, web request tools |

### 1.2 Representative Tool Categories

| Category | Tools | Why Suitable for MVP |
|---|---|---|
| **File system** | `file_read`, `file_write`, `file_delete` | High-risk, common in AI agent workflows; clear parameter patterns (paths); easy to test and demonstrate. Wildcard matching uses exact tool names or `*` only. |
| **Data export** | `data_export`, `scan_directory` | REQUIRE_APPROVAL use case for large data transfers; audit logging critical for compliance; parameter-driven conditions (size, destination). |
| **Web request** | `http_get`, `http_post` | Network operations with clear security boundary; can enforce ALLOW/DENY based on URL patterns; demonstrates context-aware evaluation |

### 1.3 Minimal Dependency Set

| Dependency | Reason |
|---|---|
| `pyyaml` (or `yaml` std-adjacent) | YAML policy loading |
| `python-dotenv` (optional) | Environment variable patterns for testing |
| Standard library only for core | No external runtime dependencies beyond policy YAML parsing |

### 1.4 Documentation (MVP Level)

- Design document (this file)
- Public API specification
- Basic README with installation and quick-start
- Inline docstrings on public API
- No tutorial or advanced guide in MVP

---

## 2. Out-of-Scope List - Not in MVP

### 2.1 Out of Scope

| Category | Items Excluded |
|---|---|
| **Python predicate support** | No `eval`, no arbitrary code execution in policies. Python predicates deferred to v2. |
| **Persistent approval store** | MVP uses in-memory only. Persistence deferred to v1.1 or v2. |
| **Policy versioning** | No built-in policy version tracking or rollback. Basic hot-reload only. |
| **Advanced condition operators** | `between`, `starts_with`, `ends_with` deferred to v2. MVP has: eq, neq, gt, lt, gte, lte, contains, regex. |
| **Multi-factor approval** | Simple approve/deny flow. No MFA, no quorum, no threshold-based approval. |
| **Approval UI component** | No built-in web UI, CLI dialog, or window. Adapter implements the UI. |
| **Policy visualization** | No dashboard or visual policy editor. YAML files are hand-edited or generated externally. |
| **Policy composition/inheritance** | No "extends" or "import" in policies. Flat rule lists only. |
| **Rate limiting** | No request rate limiting or throttling. |
| **Caching** | No evaluation result caching. Each evaluation is fresh. |
| **Distributed tracing** | No OpenTelemetry or distributed tracing integration. |
| **Metric collection** | No Prometheus metrics or StatsD integration. |
| **Multiple concurrent users** | No built-in multi-tenant or per-user policy isolation. Single policy set per Guard instance. |
| **Agent framework integration** | No tight coupling to LangChain, AutoGPT, or any specific framework. Framework-agnostic by design. |
| **Transport security** | No TLS, no network security. Assumes underlying infrastructure provides this. |
| **Process sandboxing** | No OS-level sandboxing, no subprocess isolation. |
| **Credential management** | No secret storage, no vault integration. |
| **Web dashboard or API server** | No HTTP server, no exposed endpoints. Library-only. |
| **GUI components** | No visual components or windowed interfaces. |

### 2.2 Deferred to Post-MVP

| Feature | Planned For |
|---|---|
| Python predicate callbacks (safe, registered only) | v2.0 |
| Persistent approval store with expiration | v2.0 |
| Policy versioning and semantic diff | v2.0 |
| Advanced condition operators (`between`, etc.) | v2.0 |
| Multi-factor approval thresholds | v2.1 |
| Visual policy editor integration | v2.1 |
| Rate limiting and request throttling | v2.1 |
| Caching of evaluation results | v2.1 |
| OpenTelemetry instrumentation | v2.1 |
| Metrics and alerting | v2.1 |
| Multi-tenant policy isolation | v3.0 |
| Framework-specific integrations (LangChain, etc.) | v3.0 |
| HTTP/REST API gateway | v3.0 |

### 2.3 Explicit Out-of-Scope Constraints

- **No `eval` or arbitrary code execution** in policy evaluation (explicit constraint)
- **No framework coupling** - Mandate remains framework-agnostic (explicit constraint)
- **No built-in approval UI** - adapter implements the mechanism (explicit constraint)
- **No persistent approval storage** - MVP is in-memory only (explicit constraint)
- **No base policy set shipped** - Guard starts empty; user must load their own policies (explicit constraint)
- **Default-deny boundary is integration-defined** - Actions outside the integration boundary are not automatically protected (explicit design decision)

---

## 3. Scope Boundary Diagram

```
+-----------------------------------------------------------+
|                    MANDATE LIBRARY                        |
|  +----------------------+  +----------------------------+ |
|  |  Core Engine         |  |  Policy YAML/JSON Loading  | |
|  |  - evaluate()        |  |  - from_yaml()/from_json() | |
|  |  - enforce()         |  |  - Schema validation       | |
|  |  - request_approval()|  |  - Validation errors →     | |
|  |  - reload_policies() |  |    PolicyValidationError   | |
|  +----------------------+  +----------------------------+ |
|  +----------------------+  +----------------------------+ |
|  |  Approval Workflow   |  |  Audit Event Emission      | |
|  |  - request_approval()|  |  - Structured JSON events  | |
|  |  - approve/deny()    |  |  - Sanitized parameters    | |
|  |  - invalidate on     |  |  - Integration-point        | |
|  |    parameter change  |  |    adapter writes JSONL    | |
|  +----------------------+  +----------------------------+ |
+-----------------------------------------------------------+
         ^                                  ^
         |                                  |
         |   FRIDAY ADAPTER (integration)   |
         |   - translates FRIDAY context    |
         |   - proxies audit events to      |
         |     FRIDAY JSONL logger          |
         |   - implements approval UI       |
         |   - ensures all tool calls       |
         |     route through guard.evaluate() |
         +------------------------------------+
```

---

## 4. MVP Success Definition

The MVP is considered successful if it demonstrates:

1. [ ] **Policy evaluation**: Guard can load YAML policies and produce correct ALLOW/DENY/REQUIRE_APPROVAL decisions
2. [ ] **Default-deny**: Actions not covered by any ALLOW rule are denied
3. [ ] **Approval flow**: REQUIRE_APPROVAL actions require and validate human approval before execution
4. [ ] **Audit logging**: Every evaluation emits a structured event with sanitized parameters
5. [ ] **Error handling**: Policy evaluation failures and invalid policies are handled correctly (→ DENY)
6. [ ] **FRIDAY integration**: Thin adapter can route tool calls through the guard and log decisions
7. [ ] **No security regressions**: All security test matrix tests pass (see threat-model.md)