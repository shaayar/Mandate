# Mandate: Positioning Strategy

**Status:** Proposal for review\
**Date:** 24 October 2026\
**Scope:** How Mandate should be described to the outside world, and what
has to be true before it says so. Nothing here changes an approved design
decision; where it touches one, it says so.

------------------------------------------------------------------------

## 1. Summary

- **The category is crowded.** A one-afternoon scan finds more than twenty
  projects that gate agent tool calls with allow/deny/ask policies, from
  Microsoft's Agent Governance Toolkit down to v0.1 YAML firewalls on PyPI.
  "Policy enforcement for AI agents" describes the category, not Mandate.
  It cannot be the headline.
- **Lead with approval integrity.** Most human-in-the-loop tooling treats
  approval as a yes/no prompt. Mandate's design treats an approval as
  authorization for *one exact call, used once*: bound to tool, parameters
  and context, consumed atomically, invalidated by any change, never
  carried over to a retry. This is concrete, easy to demo and easy to test.
  It is the sharpest thing in the design docs.
- **Back it with honest boundaries.** Mandate's documents already separate
  what the library guarantees from what the integration has to do and what
  needs OS or network controls. Put that table on the website. Security
  readers trust tools that say what they don't do.
- **Aim it at people who own the tool loop.** That means Python developers
  building their own agents, who call tools from code they write (FRIDAY is
  one). It does not mean users of Claude Code or Cursor, who already have
  permission hooks, or platform teams buying a governance product.
- **The claims aren't all true in code yet.** 0.1.0 fixed the imports, and
  the pull request that adds this document makes approvals single-use, with
  tests. Other gaps remain (§7). The site can go up now as an early-release
  page that points at the repository. It must not present a guarantee as
  shipped until the code and tests back it.

## 2. Where Mandate stands today

| Area | State on 24 Oct 2026 |
|---|---|
| Design | Phase 1 docs complete; 12 decisions approved (`docs/open-questions.md`). |
| Code | 0.1.0 on `beta`: the package imports and installs from source (`pyproject.toml`). The pull request that adds this document fixes the approval bugs in §7. With it, 68 tests pass; `tests/test_integration_adapter.py` needs FRIDAY's adapter and cannot run in this repository. |
| README | Says "no implementation code has been shipped", which is no longer accurate. |
| Distribution | Source release. `pyproject.toml` names the distribution `mandate`, which is already taken on PyPI (§3). |
| License | MIT. |
| Repository | Public: `shaayar/Mandate`, default branch `beta`. |

## 3. The market, October 2026

The following is a directional scan. It does not verify how mature any
project is. Projects fall into four groups:

| Group | Examples | How they work | What it means for Mandate |
|---|---|---|---|
| **Policy platforms** | Open Policy Agent (Rego), Cedar (including the Strands Agents integration), Cerbos, Microsoft Agent Governance Toolkit (MIT, seven packages, `ToolCallInterceptor`) | A general policy engine, a separate service, or a multi-package governance stack | Strong for organisations that already run policy infrastructure. Heavy for one developer with one agent. |
| **Host hooks and MCP gateways** | Claude Code `PreToolUse` hooks, Agentic Control Plane, Enforcer Governor, Helio, mcp-airlock, Eunomia (FastMCP middleware) | Sit in front of a host application or an MCP server | Cover agents that someone else built. Mandate covers agents you build. |
| **Embedded libraries** (Mandate's real peers) | parlok (YAML runtime firewall, v0.1), agent-airlock, SteerPlane, solvi, CapForge, neti, Kepil, ai-tool-guard (TypeScript) | In-process wrappers and decorators around tool calls | Same shape as Mandate. Most add rate limits, budgets or signed receipts. Few say much about how an approval is scoped. |
| **Approval inboxes** | HumanLayer, Impri, Penholder, n8n's human-in-the-loop tools | A product for routing approve/deny to a person | Complementary. A Mandate adapter could hand approvals to one of these. |

**Takeaways:**

1. YAML allow/deny/approve, default-deny and an audit log are now table
   stakes. They are worth listing as features. They are not a reason to
   choose Mandate.
2. Most peers market *breadth* (budgets, rate limits, identity, receipts).
   Mandate's MVP is deliberately narrow (`docs/mvp-scope.md` §2). Turn that into
   a virtue: it does one thing and is explicit about the edges.
3. Approval semantics, meaning what exactly a "yes" authorizes, are rarely
   spelled out. That is the open ground.
4. "Guardrails" in this space usually means filtering model inputs and
   outputs (Guardrails AI, NeMo Guardrails). Avoid the word, or people will
   put Mandate in the wrong category.

Sources: [Microsoft Agent Governance Toolkit announcement](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/),
[awesome-ai-agent-governance](https://github.com/systempromptio/awesome-ai-agent-governance),
[Open Policy Agent](https://www.openpolicyagent.org/),
[Cedar authorization in Strands](https://strandsagents.com/docs/user-guide/concepts/agents/interventions/cedar-authorization/index.md),
[parlok](https://pypi.org/project/parlok/),
[CapForge](https://pypi.org/project/capforge/),
[ai-tool-guard](https://ai-tool-guard.readthedocs.io/),
[WorkOS: authorization platforms for AI agents, 2026](https://workos.com/blog/best-authorization-platforms-ai-agent-permissions-2026).

### Name collisions to manage (the name stays)

The name Mandate is settled (`docs/MANDATE_CONTEXT.md` §1). These collisions
affect how it is presented, not whether it is kept:

- **PyPI `mandate` is taken.** It is an async AWS Cognito wrapper (v2.0.1)
  that uses the same import name, and `pyproject.toml` uses the same
  distribution name. That works for installs from git, but `pip install
  mandate` gets the other package, and publishing under that name is
  impossible. Rename the distribution before any PyPI release;
  `agent-mandate` and `mandate-authz` were free on 24 Oct 2026. The site
  shows the git install line and warns about the PyPI package.
- **PyPI `mandate-guard` is taken**, by a gate that checks *agent payment
  requests* against a user-defined mandate. That is the same space and an
  almost identical idea.
- **"Mandate" already means something in agent payments.** Google's Agent
  Payments Protocol (AP2) calls its signed authorizations "mandates". Kepil
  checks actions against a "per-job mandate".

**Consequence:** never use "Mandate" alone. Always pair it with the
descriptor ("Mandate, authorization for agent tool calls"). Keep payments
out of the examples so the AP2 association doesn't take over. Domain and
trademark checks are still outstanding (`docs/MANDATE_CONTEXT.md` §1).

## 4. Positioning

### Who it's for

**Primary: Python developers who own their agent's tool-dispatch loop.**
Solo builders and small teams with a personal assistant, an internal
operations agent, or an agentic feature in their own product. They wrote
the tool registry and the tool-calling loop, and they are about to give
the agent write, delete, export or network access.

Moments that send them looking:

- the first time an agent touches something it shouldn't have;
- the decision to grant write or delete access to a real filesystem, bucket
  or API;
- a customer security questionnaire asking "how do you control what your
  agent can do?";
- discovering that an approval given for one action quietly covered another.

**Secondary: the security-minded reviewer on that team.** They will read
the guarantees table before the code samples.

**Not now:**

- end users of coding agents, who already have host hooks;
- platform teams that want organisation-wide governance (OPA, Cedar, AGT);
- MCP server operators, who use gateways.

Each of these could later be reached through an adapter. None is the
launch audience.

### Positioning statement

> For **Python developers who build their own agents**, Mandate is an
> **embedded authorization library** that decides, before a tool runs,
> whether the call is **allowed, denied, or needs a person**, and makes
> each human approval count for **exactly one call**. Unlike policy
> platforms, it needs no server, no policy language and no new
> infrastructure. Unlike a yes/no approval prompt, a Mandate approval is
> bound to the exact call, used once, and void if anything changes.

The last sentence is a hypothesis about what buyers value. Test it in
interviews (§8) before building the campaign around it.

### Alternatives a buyer will weigh, and our answer

| They're considering | Our answer |
|---|---|
| "I'll write an `if` in my dispatcher." | That works until there are a dozen tools and approvals. Then you need precedence rules, default-deny, single-use approvals and a redacted audit log, and Mandate is that code, already tested adversarially. |
| OPA / Cedar | Use them if you already run them. Mandate is a `pip install` with one dependency (PyYAML), and policies are plain YAML. |
| Microsoft Agent Governance Toolkit | Broader, multi-package, aimed at organisations. Mandate is one small library for one boundary. |
| Host hooks (Claude Code, Cursor) | Right for agents someone else built. Mandate is for agents you build. |
| Another embedded library | Compare approval semantics and stated limits. Ask them what a "yes" authorizes. |

## 5. Messaging

### Tagline

**"Authority for AI agents, not unrestricted power."** This adapts the
project's founding line ("give AI agents the authority they need, not
unrestricted power"). The current tagline, "Policy enforcement for AI
agents", becomes the descriptor in package metadata and page titles, where
being plain helps search.

### One-liner

> Mandate is a small Python library that sits between your agent and its
> tools. Before a tool runs, it decides: allow, deny, or ask a human.
> Approvals are bound to the exact call and work once.

### Three pillars

| Pillar | Message | Proof needed before claiming it |
|---|---|---|
| **1. Decide before it runs** | Three outcomes, checked in your dispatcher before the tool executes. An explicit deny always wins, then approval, then allow; if nothing matches, the answer is deny. Evaluation errors never produce an allow. | Table-driven precedence tests. A fake tool with an execution counter showing zero side effects on DENY, on a pending approval, and on error (`docs/MANDATE_GAP_ASSESSMENT_DECISIONS.md` §4.1). |
| **2. A yes means this call, once** *(lead)* | An approval is bound to tool, parameters and context. It is consumed atomically and expires. Change a parameter and it's a new request. A retry after a failure needs a fresh yes. | Replay, mismatch, expiry and concurrent-consume tests passing (gap assessment §4.2). The site demo should *show* a replayed approval being rejected. |
| **3. Know exactly what's covered** | A published table: what Mandate guarantees, what your integration must do, and what needs other layers. A conformance suite that a deliberately broken guard fails. | The conformance test set (implementation plan I14). |

**Supporting points:** pure Python, one runtime dependency, no server, no
policy DSL, no `eval`, framework-agnostic, audit events with secret
redaction (described as best effort).

### Words

| Use | Avoid | Why |
|---|---|---|
| authorize, decide, boundary, approval, default-deny | secure your agent, sandbox, zero-trust | Mandate is an authorization layer, not isolation (`README.md`, security boundaries). |
| "limits what an injected instruction can make a tool do" | "prevents prompt injection" | Mandate doesn't detect injection. It constrains the effect. |
| redaction, "best-effort secret redaction" | "secrets are never logged" | Pattern-based redaction can't promise that (gap assessment §4.4). `docs/threat-model.md` §1.2 currently does, and should be corrected. |
| early release, 0.1.0, source release | production-ready, enterprise-grade, battle-tested | Not true yet. |
| a library you embed | platform, gateway, guardrails | Each of those puts Mandate in someone else's category. |
| "one of several ways to…" | first, only, unique, best | `docs/MANDATE_CONTEXT.md` §5 forbids these without evidence. |

## 6. Proof strategy

In order of credibility:

1. **The guarantees table.** It is on the site from day one, worded as
   design guarantees until 0.1 ships.
2. **The conformance suite.** It is public once the repository is public.
   The broken-guard check is the proof that the suite tests something.
3. **The FRIDAY case study:** "Mandate guards FRIDAY's filesystem and web
   tools", with real audit events. Publish it only after the staged
   integration lands.
4. **A replay demo:** a 30-second clip or an inline code sample in which an
   approved export is consumed once, the replay is rejected, and a changed
   destination triggers a new request.

No testimonials until real users exist. Placeholder social proof would
contradict pillar 3.

## 7. Claims gate: what must be true before the site says it

Claims came from reading the code on `beta` (`2c5772c`). Rows marked
**fixed** are addressed by the pull request that adds this document, with
a test for each. The rest need a decision before they change.

| Site claim | Today | What makes it true |
|---|---|---|
| "You can try it" | **Fixed in 0.1.0.** The package imports and installs from source. There is no CI yet; a workflow would need to leave out or provide the FRIDAY adapter that `tests/test_integration_adapter.py` imports. | Tests run in CI on every pull request. |
| "Approvals work once" | **Fixed.** `Guard.consume_approval` returned `True` for pending or denied approvals and took no lock. It now succeeds only for an approved, unexpired approval, under a lock. Still open: `docs/public-api.md` §5.5 contradicts itself on whether re-consuming returns `False` or raises. | One re-consume contract in the docs. |
| "Every request gets a fresh approval" | **Fixed.** Approval IDs came from `hash()`, so identical requests shared one ID and nested parameters raised `TypeError`. IDs are now random. Approvals without a timestamp now expire too. | n/a |
| "Invalid policies are rejected" | `Guard.load_policy` catches `PolicyValidationError` and returns `None`. A malformed deny file is skipped silently, which can turn a deny into an allow from another file. | Raise `PolicyValidationError` on load, as AC-032, AC-037 and PCF-003 specify. |
| "Every decision is audited" | Events are built and kept in `last_audit_event`, but `logger` is never called for them. (`evaluation_time_ms` reported the timeout setting; **fixed**.) | Events are delivered to a sink. The ALL-005 audit-failure behaviour is implemented. |
| "Open source" | **Done.** MIT. | n/a |
| "Install it" | From source: `pip install git+https://github.com/shaayar/Mandate@beta`. The distribution name collides on PyPI (§3). | A distribution name that is free on PyPI, before any PyPI release. |

## 8. Validation before scaling the message

Talk to 8–10 Python agent builders before 0.1. Ask them:

1. How does your agent decide whether a tool call may run today?
2. Have you added human approval? What exactly does a "yes" cover?
3. Has an approval ever covered more than you meant it to?
4. What would you have to see to trust an authorization library? (Look for
   whether the guarantees table shows up unprompted.)
5. Which framework and tool-calling loop do you use? (This sets the order
   of adapters, which `docs/mvp-scope.md` defers to v3.)

**Signal that the wedge is right:** at least three people describe an
approval-scope problem in their own words without prompting. If nobody
does, lead with pillar 1 (small, deny-first, embedded) and keep approval
integrity as a feature.

## 9. Launch sequence

| Stage | Trigger | Site state | Call to action |
|---|---|---|---|
| **0. Make it true** | Now | n/a | n/a. Fix the remaining §7 items, rename the distribution, sync the README, add CI. |
| **1. Early-release page** | Now (0.1.0 installs from source) | Single landing page with the git install line and an early-release notice | "Follow on GitHub" (custom watch: releases) |
| **2. Hardened release** | §7 claims hold; conformance suite green | Add docs (quickstart, policy reference, guarantees); drop the early-release notice | Install line, "View on GitHub" |
| **3. Proof** | FRIDAY integration validated | Case study, replay demo | Same, plus "Read the FRIDAY write-up" |
| **4. Reach** | Interview signal on frameworks | Adapter pages, one per framework | Framework-specific quickstarts |

## 10. Website: recommended setup

**Recommendation: one page in `site/`, built on Once UI's MIT parts
only.** That means `@once-ui-system/core` (MIT) and the MIT-licensed shell
from Once UI Stack: the root layout, providers and theme config. Every section of the page is written for Mandate. No
Stack surface beyond the MIT shell is included, because the Mandate
repository is public and Stack's other surfaces are not licensed for
public source. `site/LICENSE` lists the MIT files.

It uses the repository's own brand (`assets/`): the Authority Gate mark,
favicon and social preview banner, the teal palette, and Space Grotesk
and Inter. There is no email capture, so no privacy notice and no
third-party service. The repository is public, so the call to action is
to watch it for releases, with the git install line beside it.

### Page structure

| # | Section | Job |
|---|---|---|
| 1 | Early-release notice | Set expectations before anything else. |
| 2 | Hero: tagline, one-liner, policy + dispatcher code | Say what it is in five seconds and show that it is small. |
| 3 | How it works: three outcomes, precedence rule | Pillar 1. |
| 4 | Approvals: "A yes means this call, once", with replay sample | Pillar 2, the wedge. |
| 5 | Guarantees: three columns (Mandate / your integration / other layers) | Pillar 3. |
| 6 | Where it fits: when to use something else | Build trust by naming the alternatives. |
| 7 | FAQ | Sandbox? Prompt injection? Frameworks? License? |
| 8 | Follow along: watch the repository, read the design | The stage 1 call to action. |

### Before it goes live

- **Domain.** `baseURL` and canonicals are set to the reserved placeholder
  `https://mandate.example`. Run a domain check (§3) first.
- **Claims.** Keep the early-release notice until the §7 rows hold.

------------------------------------------------------------------------

**Decision summary:** Keep the name, scope and design. Change the
headline from the category ("policy enforcement") to the wedge ("a yes
means this call, once"). Publish the guarantees table as proof. Aim at
developers who own their tool loop. Ship a one-page early-release site
now, built on MIT parts only. Make every guarantee true in code before the
site drops its early-release notice.
