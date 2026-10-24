```mermaid
flowchart TD
    %% Styling
    classDef policy fill:#0B1F26,color:#14DBA6,stroke:#0E8F80,stroke-width:2px
    classDef rule fill:#1E293B,color:#F59E0B,stroke:#14DBA6,stroke-width:1px
    classDef decision fill:#FFFFFF,color:#0B1F26,stroke:#14DBA6,stroke-width:1px
    classDef outcome fill:#0E8F80,color:#FFFFFF,stroke:#14DBA6,stroke-width:1px

    subgraph POLICY_FILES["Policy Files (loaded in order)"]
        direction LR
        P1[Policy File 1 (lower precedence)] --> P2[Policy File 2] --> P3[Policy File 3 (higher precedence)]
    end

    %% Matching rules within a file (first-match wins)
    subgraph WITHIN_FILE["Within a Single File: First-Match Wins"]
        direction TB
        R1[Rule 1 (top)] --> R2[Rule 2] --> R3[Rule 3 (bottom)]
        rule1_match{Condition Matches?}
        rule1_match -->|Yes| R1_action[Return Rule 1 Action]
        rule1_match -->|No| R2[Rule 2]
        rule1_match -.->|No| R2_match{Condition Matches?}
        R2_match -->|Yes| R2_action[Return Rule 2 Action]
        R2_match -->|No| R3[Rule 3]
        R3_match{Condition Matches?}
        R3_match -->|Yes| R3_action[Return Rule 3 Action]
        R3_match -->|No| Default_Deny[Return DENY]
    end

    %% Cross-file precedence: DENY > REQUIRE_APPROVAL > ALLOW
    subgraph CROSS_FILE["Cross-File Precedence: DENY > REQUIRE_APPROVAL > ALLOW"]
        direction TB
        C1[Phase 1: Find latest file with matching DENY] 
        C2[Phase 2: Find latest file with matching REQUIRE_APPROVAL]
        C3[Phase 3: Find latest file with matching ALLOW]
        C4[Phase 4: Default-Deny if no rule matches]

        C1 -->|DENY found in any file| Outcome1[DENY -- Absolute Precedence]
        C2 -->|No DENY; REQUIRE_APPROVAL found| Outcome2[REQUIRE_APPROVAL -- Beats ALLOW]
        C3 -->|No DENY/REQ APPP; ALLOW found| Outcome3[ALLOW]
        C4 -->|No rule matches anywhere| Outcome4[DENY -- Default-Deny]
    end

    %% Concrete example connections
    EX1[Example: Policy File 1 allows file_read] -->|Rule 1 matches| R1_action[ALLOW]
    EX2[Example: Policy File 2 denies file_read] -->|Phase 1 finds DENY| Outcome1[DENY -- File 2 overrides]
    EX3[Example: No matching rules] -->|Phase 4| Outcome4[DENY -- Default-Deny]

    %% Styling assignments
    class POLICY_FILES policy
    class R1,R2,R3 rule
    class rule1_match,R2_match,R3_match,R3_match decision
    class Outcome1,Outcome2,Outcome3,Outcome4 outcome
```