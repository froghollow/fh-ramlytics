

## Agent Team

**Orchestrator** - Routes signals. Validates outputs against schemas. Branches on Go/Reduce/Stand Down. Atuhority: Escalates exceptions. Owns every memory write. Holds the schedule. Reads the kill-switch flag first, every cycle.

**Research Agent** - Reads market data, calendar, watchlist, episodic memory, and semantic memory. Writes the seven-field pre-trade brief. Authority: produce briefs only. Cannot size. Cannot execute.  

Pre-trade Brief Schema: 
-   Instrument — the symbol the brief is about. One value.  
-   Bias — long, short, or flat. One of three values. No prose.  
-   Key_levels — support, resistance, and invalidation. Three numeric values.  
-   Catalyst_risk — a list of scheduled events inside the decision window, each with a timestamp and an impact rating.  
-   Confidence — a float between 0.00 and 1.00. The agent’s calibrated probability that the bias is correct.
-   Reasoning_trace — a three-bullet summary of why the agent reached this bias. Not a paragraph. Three bullets. 
-   Timestamp — ISO 8601 with time zone. Set by the agent at write time, not by the scheduler.

**Sentiment Agent** - Reads news feed, social feed (after the manipulation filter), and the Research brief. Writes a two-field score (sentiment_score plus confidence) and a data_insufficient flag. Authority: score sentiment only. Cannot trade.  

Sentiment Score Schema:
-   Score - between -1.00 (bearish) and +1.00 (bullish)
-   Confidence - between 0.00 and +1.00
-   Data Insuffient - TRUE or FALSE

**Risk Agent** - Reads Research brief, Sentiment score, your rule set, and procedural memory. Writes Go / Reduce / Stand Down plus a size multiplier between 0.25 and 1.00. Authority: VETO. Can halt the pipeline. No other agent can.  

**Execution Agent** - Reads Risk decision, broker connection, and slippage log. Writes the order ticket and the fill

### Authorization Boundaries

Risk Agent can halt the pipeline. No other agent can.  

Orchestrator can escalate. Agents can request escalation; only the Orchestrator routes it.  

No agent can rewrite its own goal. The system prompt is set by the human, full stop.  

Authorities **never** delegated: 
- hard-rule changes, 
- ladder phase promotion, 
- watchlist additions, and 
- account size increases.

## Data Stores (Agent Memory)

DynamoDB with time series archive in S3.

**Episodic** - Every signal, every cycle, with full context. Eighteen fields per record.  

**Semantic** - Strategy rules, instrument profiles, market structure definitions. Doesn’t change from session to session. Updated on the quarterly review.  

**Procedural** - Per-setup outcomes, calibration scores, and slippage history. The Risk Agent reads this back at the start of every cycle.

**Accounts** - User's investment accounts (401k, IRA, etc.)

**Positions** - Holdings in each account

**Instruments** - ETFs, stocks, and funds with current prices and allocation data (shared reference data)

**Users** - Minimal user data (Clerk handles auth)

**Jobs** - Async job tracking of agent executions




## Signal Flow Sequence Diagram

```mermaid
sequenceDiagram
    participant Schedule as EventBridge Schedule
    participant Orch as Orchestrator
    participant Store as Database
    participant Research as Research Agent
    participant Sentiment as Sentiment Agent
    participant Risk as Risk Agent
    participant Execution as Execution Agent
    participant Human as Human
    participant Broker

    Schedule->>Orch: 1. Fire scheduled trigger
    Human->>Orch: 1a. On-demand execution
    
    Orch->>Store: 2. Read data store
    Store-->>Orch: Return stored data
    Orch->>Research: 3. Initiate research
    Research-->>Orch: 4. Produce research brief
    Orch->>Store: 5. Validate and store research brief
    Orch->>Sentiment: 6. Initiate sentiment analysis
    Sentiment-->>Orch: 7. Produce Sentiment Score
    Orch->>Store: 8. Validate and store Sentiment Score
    Orch->>Risk: 9. Initiate risk evaluation
    Store-->>Risk: 9a. Read Research Brief and Sentiment Score
    Risk-->>Orch: 10. Produce Risk Report from brief and sentiment

    Orch->>Store: 11. Validate and store Risk Report
    Orch->>Execution: 12. Evaluate report initiate for GO REDUCE or STAND_DOWN
    Execution-->>Orch: 13. Produce Order Ticket
    Orch->>Store: 14. Validate and store Order Ticket
    alt Human checkpoint implemented
        Orch->>Human: 15. Await human checkpoint
        Human-->>Orch: Return checkpoint decision
    else No human checkpoint
        Orch->>Execution: 15. Re-initiate Execution Agent
    end
    Orch->>Broker: 16. Submit order
    Broker-->>Execution: Return broker results
    Execution->>Orch: 17. Monitor results and send execution info
    Orch->>Store: 18. Validate and store Execution Info
    Orch->>Human: 19. Send user notification
```
