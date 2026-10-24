```mermaid
flowchart TD
    %% Styling
    classDef guard fill:#0B1F26,color:#14DBA6,stroke:#0E8F80,stroke-width:2px
    classDef approval fill:#1E293B,color:#F59E0B,stroke:#14DBA6,stroke-width:1px
    classDef decision fill:#FFFFFF,color:#0B1F26,stroke:#14DBA6,stroke-width:1px
    classDef outcome fill:#0E8F80,color:#FFFFFF,stroke:#14DBA6,stroke-width:1px
    classDef block fill,#EF4444,color:#FFFFFF,stroke:#F87171,stroke-width:1px

    subgraph GUARD["Guard Instance"]
        direction TB
        GL1[Guard() empty policy set] --> GL2[self._approvals = {}]
        GL2 --> GL3[self.policy_set = PolicySet()]
        GL3 --> GL4[self.approval_mechanism = None/ callback]
    end

    subgraph APPROVAL_LIFECYCLE["Approval Lifecycle"]
        direction TB
        A1[guard.request_approval(tool_name, parameters, context)] 
            --> A2[generate approval_id via hash((tool_name, frozenset(parameters), frozenset(context)))]
            --> A3[call approval_mechanism(callback)] 
            --> A4[store approval in self._approvals[approval_id]]
            --> A5[returns approval dict: id, tool_name, parameters, context, state: pending, created_at, approved]
        
        A5 --> B1[guard.approve(approval_id)]
        B1 --> B2[self._approvals[approval_id]["state"] = "approved"; self._approvals[approval_id]["approved"] = True]
        
        A5 --> C1[guard.deny(approval_id)]
        C1 --> C2[self._approvals[approval_id]["state"] = "denied"]
        
        A5 --> D1[guard.is_approval_valid(approval_id, tool_name, parameters)]
        D1 -->|approval_id not found| D2[returns False]
        D1 -->|tool_name mismatch| D3[returns False]
        D1 -->|parameters mismatch| D4[returns False]
        D1 -->|state != approved| D5[returns False]
        D1 -->|timeout exceeded (elapsed_ms > approval_timeout_ms)| D6[returns False]
        D1 -->|all checks pass| D7[returns True]
        
        D1 --> E1[guard.consume_approval(approval_id)]
        E1 -->|approval_id unknown| E2[raises ApprovalAlreadyConsumedError]
        E1 -->|already consumed (in _consumed_approvals)| E3[returns False, no exception]
        E1 -->|fresh consumption| E4[adds approval_id to _consumed_approvals; sets approval state to "consumed"; returns True]
        
        E4 --> F1[Single-use guarantee: consumed approval cannot authorize another execution]
        E4 -->|re-evaluate after consumption| F2[guard.evaluate() with same action → DENY (consumed approval invalidated)]
    end

    %% Expiry / timeout
    subgraph TIMEOUT["Expiry and Timeout"]
        direction TB
        T1[approval created with created_at timestamp]
        T2[guard.approval_timeout_ms set]
        T3[elapsed_ms = (time.time() - created) * 1000]
        T3 -->|elapsed_ms > approval_timeout_ms| T4[is_approval_valid returns False]
        T3 -->|elapsed_ms <= approval_timeout_ms| T5[is_approval_valid returns True]
    end

    %% Audit failure blocking
    subgraph AUDIT_BLOCK["Audit Emission Failure (fail-closed)"]
        direction TB
        U1[emit_audit_event() raises exception]
        U2[Guard._emit_audit_event() raises]
        U2 --> G1[protected action blocked: PermissionError]
        U2 -->|if audit fails during adapter| G2[adapter blocks action: PermissionError("Authorization decision could not be recorded; action blocked: {reason}")]
    end

    %% Connections
    G4 -->|calls| A1
    A5 -->|valid approval| B1
    A5 -->|valid approval| C1
    A5 -->|valid approval| D1
    B1 -->|approval state set to approved| D1
    C1 -->|approval state set to denied| D1
    D1 -->|validity result| E1
    E1 -->|consumption result| F1
    F2 -->|consumed| G1
    G1 -->|blocks execution| block[Block Execution]
    T1 --> T2
    T2 --> T3
    U1 --> U2

    %% Styling assignments
    class GL1,GL2,GL3,GL4 guard
    class A1,A2,A3,A4,A5,B1,C1,D1,D2,D3,D4,D5,D6,D7,E1,E2,E3,E4,F1,F2 guard
    class A1,A2,A3,A4,A5 decision
    class T1,T2,T3,T4,T5 outcome
    class G1,G2 block
```