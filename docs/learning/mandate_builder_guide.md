# Mandate: Builder's Guide to Authorization, Data Flow, and Approval Integrity

> A learning document for the builder of Mandate. This guide explains the concepts behind the library and the request flow using a beginner-friendly mental model. The diagrams are conceptual; verify exact call ordering and component behavior against the current source.

## 1. What is Mandate?

Mandate is an authorization layer for AI agents and other software that can invoke tools. It helps decide whether an action may proceed, must be blocked, or requires human approval.


It is not the tool executor. It should not itself delete files, send emails, or execute shell commands. It evaluates authorization and returns a decision. The caller/execution layer must honor that decision.

The architectural separation is:

- **Caller / FRIDAY:** requests an action.
- **Mandate:** evaluates whether the action is authorized.
- **Execution layer:** performs the action only when allowed by the integration's enforcement logic.

> The component requesting an action and the component authorizing it should not be the same component.

## 2. A request's basic shape

An action can be represented by its tool name, parameters, and context:


```python
tool_name = "delete_file"
parameters = {
    "path": "/home/user/documents/old_report.pdf"
}
context = {}
```

| Field | Meaning |
|---|---|
| `tool_name` | Which action/tool is requested? |
| `parameters` | What arguments will the tool operate on? |
| `context` | Additional information surrounding the request |
| `policy` | Rules that determine which actions are permitted |
| `approval` | Authorization record, when human approval is required |

Think of a request as a parcel arriving at a security checkpoint: the tool name is its label, parameters are its contents, and context is surrounding information.

## 3. Conceptual request flow

```text
FRIDAY / Caller
    |
    | tool + parameters + context
    v
Mandate Guard
    |
    v
Policy evaluation
    |
    +---- ALLOW ------------> Caller may proceed to execution
    |
    +---- DENY ------------> Caller must block execution
    |
    +---- REQUIRE_APPROVAL -> Approval workflow
                                |
                                v
                         Approved / Denied
                                |
                     Validate / consume approval
                                |
                                v
                      Caller enforces outcome
```

This is a conceptual overview. Exact internal ordering and the participation of each component vary by code path and must be confirmed from the source.

## 4. Policies and decisions

Policies are the rules that describe what is permitted. A conceptual example:


```yaml
rules:
  - tool: delete_file
    decision: DENY

  - tool: read_file
    decision: ALLOW

  - tool: send_email
    decision: REQUIRE_APPROVAL
```

This example is illustrative, not a guarantee that these exact keys or syntax match Mandate's current policy schema.

Mandate's decision model includes:
- `ALLOW`
- `DENY`
- `REQUIRE_APPROVAL`

The documented precedence is:

1. `DENY`
2. `REQUIRE_APPROVAL`
3. `ALLOW`

Conflict resolution must be deterministic. If two applicable rules disagree, the outcome should be governed by a defined precedence rule, not accidental file ordering.

### What the decisions mean

**ALLOW:** The action is authorized by policy. It is not the same as executing the action. The caller/execution layer still performs the operation.

**DENY:** The action is prohibited. The integration must block execution.

**REQUIRE_APPROVAL:** The action cannot proceed without an appropriate approval process.

## 5. Why the approval path is important

Suppose a tool is about to send an email:


```python
tool_name = "send_email"
parameters = {
    "to": "client@example.com",
    "subject": "Project update",
    "body": "The project has been completed."
}
```

If policy requires approval, the approval must bind to the specific action—not merely the general idea of sending an email.

A meaningful approval is closer to:

> I approve sending this email to this recipient, with this subject and this body.

This is the idea behind **parameter binding**.

## 6. Approval records and lifecycle

An approval record conceptually stores details such as:


```python
approval = {
    "id": "unique_approval_id",
    "tool_name": "send_email",
    "parameters": {
        "to": "client@example.com",
        "subject": "Project update",
        "body": "The project has been completed."
    },
    "state": "pending",
    "created_at": 1234567890,
    "approved": False
}
```

This is a teaching example, not an exact schema guarantee.


An approval has a lifecycle rather than being a reusable Boolean permission. Conceptually:


```text
PENDING
   |
   +----> APPROVED ----> CONSUMED
   |
   +----> DENIED
```

The actual state names and transitions must be checked in the current implementation.

Two distinct protections are needed:

| Protection | Purpose |
|---|---|
| Parameter binding | Prevent an approval from authorizing a changed action |
| Single-use consumption | Prevent reuse/replay of an approval |

Binding without consumption can permit replay of the same approved action. Consumption without binding can allow an approval to be used for altered arguments. Both concerns matter.

## 7. Python references, mutability, and aliasing

A Python assignment does not necessarily copy an object.

```python
original = {"path": "/data/report.txt"}
approval_parameters = original

original["path"] = "/data/other.txt"

print(approval_parameters)
```

Output:

```python
{'path': '/data/other.txt'}
```

Both variables point to the same dictionary. This is called **aliasing**. A dictionary is mutable, so changing it through one reference changes what is seen through the other reference.

In the original A1 implementation, Mandate stored caller-owned parameters by reference. A caller could mutate those parameters after approval issuance, changing the effective stored approval binding.

## 8. A1: Approval Parameter Binding vulnerability

### Root cause

The approval record stored the caller's parameter dictionary directly:

```python
"parameters": parameters
```

No independent snapshot was created. Since the object was shared, top-level and nested mutations affected the stored approval.

### Security invariant

> An approval must remain bound to the parameter snapshot established at approval issuance. Mutations to caller-owned data must not change the stored binding.

### Remediation candidate implemented

The reported remediation uses `copy.deepcopy()`:

```python
import copy

stored_params = copy.deepcopy(parameters)
```

A deep copy recursively copies nested data structures where supported, creating an independent snapshot from caller-owned mutable structures.

| Operation | Behavior |
|---|---|
| Assignment (`=`) | Another reference to the same object |
| `copy.copy()` | Shallow copy; nested objects may still be shared |
| `copy.deepcopy()` | Recursively copies nested objects where supported |

Deep copying is not the same as making an object immutable. Any exposed reference to the copied snapshot could still mutate it. The reported A1 patch shares `stored_params` between the callback-facing approval request and the internal approval record; callback/returned-request mutation therefore remains a verification item before A1 can be formally closed.

Snapshot failure must fail closed. The code must not silently fall back to storing the original mutable reference.

## 9. Why tests matter

A regression test captures a behavior that must remain true. For security fixes, tests should prove the invariant through observable behavior rather than merely checking that a particular function (such as `deepcopy`) was called.

For A1, useful test cases include:
- Mutate the top-level caller dictionary after issuance.
- Mutate a nested dictionary.
- Mutate a nested list.
- Mutate parameters through the approval request returned to the caller.
- Mutate parameters through the approval callback's request.
- Verify original parameters remain valid.
- Verify altered parameters are rejected.
- Verify structurally equal parameters still validate.
- Verify consumption behavior remains unchanged.
- Verify snapshot creation failure fails closed.

A passing test suite is evidence, but test coverage must be inspected to ensure the tests actually exercise the intended security property.

## 10. Fail-closed design

Fail-closed behavior means that when a security-critical operation cannot safely determine whether an action is authorized, the system does not grant permission by default.

For example, if Mandate cannot create a reliable parameter snapshot, it should not continue with an approval bound to the original mutable object. Failure should prevent the protected action from proceeding.

## 11. How to review agent-generated changes

When a coding agent proposes a patch, ask:

1. What problem are we solving?
2. What security invariant must always remain true?
3. Where does the data enter the system?
4. Where is it stored?
5. Who can access or mutate it?
6. Where is it checked?
7. What happens if a critical operation fails?
8. How do we prove the fix works?

For an authorization bug, trace data from input to storage to validation to consumption. Review references and object ownership, not just variable names.

## 12. Builder's mental model

Keep this model in mind:

- **Guard:** coordinates authorization flow.
- **Policy evaluation:** applies rules and returns a decision.
- **Approval system:** manages approvals when required.
- **Audit:** records security-relevant events (where implemented and configured).
- **Caller/integration:** enforces Mandate's result and executes the action only when authorized.

These are conceptual roles. Confirm exact implementation boundaries in the source before relying on the diagram.

## 13. Lessons from A1

A1 was not merely a Python copying bug. It exposed several engineering concepts:

- Authorization: deciding whether an action is permitted.
- Separation of concerns: authorization and execution are distinct responsibilities.
- Policy evaluation: rules produce a decision.
- Conflict resolution: policies need deterministic precedence.
- State machines: approvals have lifecycle transitions.
- Parameter binding: approval applies to the exact action.
- Replay protection: consumed approvals cannot be reused.
- Mutability and aliasing: multiple references can point to one mutable object.
- Deep copying: creates independent nested structures, subject to object behavior.
- Fail-closed design: critical failure must not accidentally grant permission.
- Regression testing: protects security invariants against future changes.

## 14. Important caution

This guide is intended to teach the concepts and summarize the A1 work discussed so far. It is not a substitute for source-code review, test evidence, API documentation, or a formal security specification. Some diagrams and code snippets are conceptual and may not exactly match the current Mandate implementation.
