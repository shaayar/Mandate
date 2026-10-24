```mermaid
flowchart TD
    %% Styling
    classDef mandate fill:#0B1F26,color:#14DBA6,stroke:#0E8F80,stroke-width:2px
    classDef friday fill:#10252B,color:#FFFFFF,stroke:#5F747B,stroke-width:2px
    classDef decision fill:#FFFFFF,color:#0B1F26,stroke:#14DBA6,stroke-width:1px
    classDef ok fill:#0E8F80,color:#FFFFFF,stroke:#14DBA6,stroke-width:1px
    classDef block fill:#EF4444,color:#FFFFFF,stroke:#F87171,stroke-width:1px

    %% FRIDAY integration
    subgraph FRIDAY["FRIDAY Integration"]
        direction TB
        F1[MCP Tool Call] --> F2[before_tool_execute Hook]
        F2 --> F3[mandate_guard.evaluate()]
        F3 --> F4[emit_audit_event()]
        F4 --> F5[Handle Decision]
    end

    %% Mandate core
    subgraph MANDATE_CORE["Mandate Core"]
        direction TB
        G1[Guard Instance] --> G2[policy_set.evaluate()]
        G2 -->|Phase 1: DENY| G3[winning_deny check]
        G2 -->|Phase 2: REQUIRE_APPROVAL| G4[winning_reqapp check]
        G2 -->|Phase 3: ALLOW| G5[winning_allow check]
        G2 -->|Phase 4: Default-Deny| G6[Decision.DENY]
        G3 -->|DENY found| G6
        G4 -->|REQ APPP found| G7[REQUIRE_APPROVAL]
        G5 -->|ALLOW found| G8[ALLOW]
        G6 --> block((Block Execution))
        G7 --> G7
        G8 --> G8
    end

    %% Approval flow
    subgraph APPROVAL["Approval Lifecycle"]
        direction TB
        A1[guard.request_approval()] --> A2[approval_id generated via hash]
        A2 --> A3[approval_mechanism callback]
        A3 --> A4[state: pending/approved]
        A4 --> A5[guard.consume_approval()]
        A5 -->|First consumption| A6[approval marked consumed]
        A5 -->|Re-consumption| A7[returns False]
        A6 --> A8[single-use guarantee enforced]
    end

    %% Connections between subgraphs
    G1 -->|calls| A1
    G8 -->|proceeds| C[Proceed with execution]
    G6 -->|blocks| block
    G7 -->|raises| ApprovalUnavailableError
    F5 -->|ALLOW| C
    F5 -->|DENY| block
    F5 -->|REQUIRE_APPROVAL| D[Request human approval]
    D -->|Approved| A4
    D -->|Denied| block

    %% Styling assignments
    class G1,Guard,Mandate_CORE mandate
    class F1,F2,F3,F4,F5,FRIDAY friday
    class G2,G3,G4,G5,G6,G7,G8 decision
    class A1,A2,A3,A4,A5,A6,A7,A8 ok
    class C block
```

```