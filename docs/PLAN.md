# PLAN — Police Peer

Diagrams below are intentionally text-based (Mermaid), kept even after the live GUI and
replay viewer were implemented (Batch 4A) because Mermaid renders in most Markdown
viewers (including GitHub) without extra tooling; real screenshots of the live GUI and
replay viewer live in `screenshots/` (see `screenshots/README.md`).

## C4 context diagram

```mermaid
graph LR
    P[Police Peer<br/>this repo] <-->|FastMCP HTTP<br/>signed wire protocol| O[Thief Peer<br/>sibling repo]
    P -->|dry-run/draft/send| G[Gmail API]
    U[Edward / Donia] -->|local GUI| P
```

## Container diagram

```mermaid
graph TB
    subgraph "Police Peer process"
        SRV[FastMCP Server<br/>exposes tools]
        CLI[FastMCP Client<br/>calls opponent]
        RT[PeerRuntime / state machine]
        DOM[Domain: board, rules, scent, belief, scoring]
        STRAT[Strategy: BaselinePoliceBrain, BeliefCutoffPoliceBrain]
        GUI[Live GUI + Replay Viewer]
        SDK[SDK facade]
    end
    SRV --> RT
    CLI --> RT
    RT --> DOM
    RT --> STRAT
    SDK --> RT
    GUI --> SDK
```

## Component diagram (this repo's `src/police_peer/`)

```mermaid
graph LR
    sdk --> domain
    sdk --> protocol
    sdk --> strategy
    sdk --> services
    services --> infrastructure
    gui --> sdk
    shared -.-> domain
    shared -.-> protocol
    shared -.-> infrastructure
```

## Deployment diagram

```mermaid
graph LR
    subgraph "localhost (dev)"
        PP["Police peer :8901"]
    end
    subgraph "localhost (dev, sibling process)"
        OP["Thief peer :8902"]
    end
    PP <-->|http://127.0.0.1| OP
    PP -.->|future: authenticated tunnel, Manual Gate A| PUB[Public internet]
```

## State machine (per book Ch.8, names to be reconciled with the book's exact labels)

```mermaid
stateDiagram-v2
    [*] --> INITIALIZING
    INITIALIZING --> SERVER_READY
    SERVER_READY --> NEGOTIATING
    NEGOTIATING --> SIGNED
    SIGNED --> WAITING
    WAITING --> THINKING
    THINKING --> SENDING
    SENDING --> VERIFYING
    VERIFYING --> WAITING
    VERIFYING --> GAME_OVER
    GAME_OVER --> AUDITING
    AUDITING --> SERIES_COMPLETE
    AUDITING --> ERROR
    WAITING --> ERROR
    THINKING --> ERROR
    ERROR --> QUIT
    SERIES_COMPLETE --> QUIT
    QUIT --> [*]
```

## Sequence diagram — one move

```mermaid
sequenceDiagram
    participant Me as Police (me)
    participant Opp as Thief (opponent)
    Me->>Opp: receive_turn(commit: H_commit only)
    Opp-->>Me: ack
    Me->>Opp: receive_turn(reveal: move + hint, nonce hidden)
    Opp-->>Me: ack
```

## Sequence diagram — commit-reveal audit (end of series)

```mermaid
sequenceDiagram
    participant Me as Police (me)
    participant Opp as Thief (opponent)
    Me->>Opp: submit_audit(records + all nonces)
    Opp->>Opp: recompute every H_commit, compare
    Opp-->>Me: submit_audit(records + all nonces)
    Me->>Me: recompute every H_commit, compare
    Note over Me,Opp: Any mismatch = tamper_forfeit, both sides report VERIFIED/TAMPERED
```

## Threat model

See `docs/SECURITY.md` and `_post4b_supplementary_evidence/audit/risk_register.md`.

## Failure/recovery model

DeadlineTracker + Watchdog (book Ch.8.4); see `docs/ARCHITECTURE.md`.
Implemented and tested (Batch 2: `domain/deadline.py`, `domain/watchdog.py`).
Production server shutdown (a related but distinct concern -- releasing the
HTTP listening socket cleanly) was hardened in session recovery step B; see
`infrastructure/server_lifecycle.py` and the CHANGELOG.

## Data schemas

See `_post4b_supplementary_evidence/audit/protocol_contract.md` Section 5 and `PRD_commit_reveal.md`.
