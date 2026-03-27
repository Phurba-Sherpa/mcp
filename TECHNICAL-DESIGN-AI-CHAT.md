# Technical Design: AI Chat for Internet Banking

Status: Draft
Related PRD: `PRD-AI-CHAT.md`
Last updated: 2026-03-26
Authors: Engineering / Product / Security / Data

## 1. Purpose

This document describes the technical design for the AI Chat MVP defined in `PRD-AI-CHAT.md`.

The design supports three banking-safe capabilities:

- explain account events using grounded customer context
- warn about limited near-term money risk or suspicious activity
- execute a small set of safe actions with deterministic controls and explicit confirmation

The core principle is strict separation of responsibilities:

- bank systems own facts
- rules own decisions and eligibility
- the LLM owns interpretation, language understanding, and customer-friendly explanation

## 2. Scope

### In scope

- authenticated AI Chat entrypoint in internet banking
- session-based conversation orchestration
- context aggregation for balances, transactions, pending items, scheduled payments, card state, alerts, and disputes
- intent classification and safety routing
- deterministic rule evaluation for explanation support, affordability checks, and action eligibility
- explanation generation using grounded facts only
- safe action execution for MVP flows
- handoff to human support with summary and evidence
- audit logging, observability, and offline evaluation hooks

### Out of scope

- fully autonomous banking agents
- direct model access to core banking write APIs
- unrestricted retrieval over all bank documents
- financial planning, investment advice, or underwriting decisions
- cross-customer memory or personalized learning across users

## 3. Design Goals

- high trust: every answer is grounded and reviewable
- narrow scope: ship a strong banking copilot, not a generic chatbot
- safe execution: no irreversible action without explicit confirmation and rule checks
- composability: build on existing banking APIs and support systems
- observability: every decision path is measurable and auditable
- graceful failure: uncertainty or unsupported cases route to clear fallback or human help

## 4. Architectural Principles

1. `Deterministic facts, probabilistic language`
   - balances, transactions, fees, eligibility, and action permissions come from deterministic services
   - the LLM explains; it does not invent or authorize

2. `Read before write`
   - read-only explanation paths ship first
   - write actions are added only when their data, eligibility, confirmation, and audit paths are complete

3. `Structured intermediate state`
   - the orchestrator moves through typed states such as `intent`, `context_snapshot`, `rule_result`, `candidate_actions`, and `final_response`
   - this keeps LLM usage inspectable and reduces hidden behavior

4. `Human fallback is a feature`
   - escalation is a first-class outcome, not an error path

5. `Least privilege across model boundaries`
   - prompts contain only the minimum necessary customer context
   - actions require server-side revalidation even after confirmation

## 5. High-Level Architecture

```text
Customer
  -> Internet Banking Web/Mobile UI
  -> AI Chat Gateway
  -> Chat Orchestrator
       -> Intent + Safety Classifier
       -> Context Aggregator
            -> Accounts API
            -> Transactions API
            -> Payments API
            -> Cards API
            -> Alerts API
            -> Disputes API
            -> Merchant Enrichment API
       -> Policy / Rules Engine
       -> LLM Explanation Service
       -> Response Composer
       -> Action Gateway
            -> Cards Write API
            -> Alerts Write API
            -> Dispute Case API
       -> Human Handoff Service
       -> Audit / Event Log / Metrics
```

## 6. Major Components

### 6.1 AI Chat Gateway

Responsibilities:

- receive authenticated requests from banking channels
- enforce request authentication, rate limiting, and session policy
- attach customer identity and channel metadata
- normalize channel payloads into internal request format

Notes:

- should not contain core conversation logic
- should support both web and mobile channels through a shared API contract

### 6.2 Chat Orchestrator

Responsibilities:

- own session state and turn-by-turn workflow
- call intent classifier and safety policy
- request context needed for the current turn only
- execute rule evaluation before any model explanation or action offer
- compose final response payload with text, sources, confidence, and next actions

Key internal states:

- `message_received`
- `intent_classified`
- `safety_checked`
- `context_loaded`
- `rules_evaluated`
- `llm_explanation_generated`
- `action_pending_confirmation`
- `action_completed`
- `escalated`

Recommendation:

- implement this as a deterministic workflow service, not as a free-form agent runtime

### 6.3 Intent and Safety Classifier

Responsibilities:

- classify user requests into categories such as `explain_balance`, `explain_fee`, `failed_payment`, `suspicious_charge`, `affordability_check`, `freeze_card`, `set_alert`, `start_dispute`, `unsupported`, `escalation`
- detect unsupported or regulated topics
- detect urgent risk indicators such as fraud claims or self-harm terms if required by bank policy

Implementation options:

- rules and keyword routing for known actions
- lightweight model classification for conversational ambiguity
- ensemble approach where rules override model results for high-risk categories

Output shape:

```json
{
  "intent": "suspicious_charge",
  "confidence": "high",
  "safetyFlags": ["fraud_related"],
  "requiresContext": ["transaction", "card_state"],
  "allowedActions": ["freeze_card", "start_dispute", "escalate"]
}
```

### 6.4 Context Aggregator

Responsibilities:

- fetch data from banking systems required for the current turn
- normalize source formats into a typed context snapshot
- apply freshness metadata and partial failure handling
- redact or minimize fields before the LLM boundary

Context domains for MVP:

- accounts and balances
- transactions and pending items
- scheduled payments and transfers
- card state and recent card activity
- alerts and dispute history
- merchant enrichment where available

Output example:

```json
{
  "snapshotId": "ctx_01",
  "generatedAt": "2026-03-26T10:15:00Z",
  "balances": {
    "current": 1250.25,
    "available": 1030.25,
    "currency": "USD"
  },
  "transactions": [
    {
      "id": "tx_1001",
      "amount": -850.00,
      "type": "debit",
      "merchantName": "Riverside Apartments",
      "postedAt": "2026-03-25T08:20:00Z",
      "category": "rent"
    }
  ],
  "scheduledPayments": [],
  "cards": [],
  "sourceStatus": {
    "transactions": "ok",
    "scheduledPayments": "ok",
    "cards": "partial"
  }
}
```

### 6.5 Policy and Rules Engine

Responsibilities:

- compute deterministic facts for explanation and action gating
- explain balance deltas using transaction and fee grouping logic
- map payment failure codes to customer-readable root causes
- calculate limited affordability projections
- determine whether a safe action may be offered and under what confirmation text
- enforce compliance restrictions and unsupported topic boundaries

Design choice:

- keep this service separate from prompts so policy logic stays versioned, testable, and explainable

Examples of rule outputs:

- top contributors to balance drop
- identified fee cause and policy reference
- projected balance if transfer occurs within defined forecast window
- suspicious charge flow eligibility
- freeze-card allowed status

Output example:

```json
{
  "ruleSetVersion": "2026.03.1",
  "decisionType": "affordability_check",
  "result": "warn",
  "confidence": "high",
  "facts": [
    "Available balance is 1030.25 USD",
    "Upcoming scheduled debit of 900.00 USD within 48 hours",
    "Requested transfer amount is 500.00 USD"
  ],
  "customerSafeSummary": {
    "riskLevel": "high",
    "projectedAvailableBalance": -369.75,
    "windowHours": 48
  },
  "allowedActions": ["set_alert", "escalate"],
  "blockedActions": ["in_chat_transfer"]
}
```

### 6.6 LLM Explanation Service

Responsibilities:

- convert structured facts into concise, plain-language responses
- interpret ambiguous customer phrasing into structured follow-up prompts where needed
- produce grounded explanations with uncertainty-aware wording

Strict constraints:

- receives only structured, minimum-necessary context
- must not receive raw tools or direct write access
- must not create new facts not present in the structured input
- output must be post-validated before delivery

Suggested prompt structure:

- system instructions defining allowed behavior and forbidden claims
- structured context snapshot
- structured rule results
- response schema requiring: `answer`, `reasoning_style`, `source_ids`, `confidence`, `next_action_labels`, `needs_human`

Validation requirements:

- every cited source ID must exist in the current snapshot
- confidence label must be one of allowed enum values
- next actions must be a subset of rule-approved actions
- no banned phrases or unsupported advice categories

### 6.7 Response Composer

Responsibilities:

- merge rule outputs, LLM text, source references, and UI action hints into channel-safe response format
- apply final fallback when source coverage or confidence is insufficient
- add disclosure or uncertainty copy required by legal/compliance

Customer response shape:

```json
{
  "message": "Your balance is lower mainly because your rent payment of $850 and a card purchase of $120 posted yesterday.",
  "type": "explanation",
  "confidence": "high",
  "sources": [
    {"type": "transaction", "id": "tx_1001"},
    {"type": "transaction", "id": "tx_1002"}
  ],
  "nextActions": [
    {"type": "set_alert", "label": "Set a low balance alert"},
    {"type": "escalate", "label": "Chat with support"}
  ],
  "disclosure": "Based on your current account activity and scheduled items available right now."
}
```

### 6.8 Action Gateway

Responsibilities:

- receive approved, confirmed action requests from the orchestrator
- revalidate customer identity, eligibility, and current system state
- call internal write APIs for supported action types
- return execution result plus audit metadata

MVP actions:

- `freeze_card`
- `set_alert`
- `start_dispute`

Required pattern:

1. AI suggests action
2. rules engine says the action is eligible
3. customer sees confirmation summary
4. customer explicitly confirms
5. action gateway revalidates and executes
6. result is returned and logged

### 6.9 Human Handoff Service

Responsibilities:

- build structured handoff packages for live support
- include intent, summary, sources, confidence, and attempted actions
- avoid requiring the customer to repeat the story

Handoff payload example:

```json
{
  "customerId": "cust_123",
  "sessionId": "sess_123",
  "intent": "suspicious_charge",
  "summary": "Customer does not recognize a card charge from ACME DIGITAL for 79.99 USD posted on 2026-03-25. Card freeze offered and accepted.",
  "sourceRefs": ["tx_888", "card_12"],
  "actionsTaken": ["freeze_card"],
  "openIssues": ["customer may want to dispute transaction"],
  "priority": "high"
}
```

### 6.10 Audit and Observability

Responsibilities:

- capture traceable event stream for every turn
- store prompt version, model version, rules version, sources used, actions offered, confirmations, and action results
- power dashboards, QA review, offline evaluation, and compliance audit

Minimum event types:

- session created
- user message received
- intent classified
- context snapshot generated
- rules evaluated
- llm response generated
- response delivered
- action offered
- confirmation accepted or declined
- action executed
- escalation created

## 7. Data Contracts

### 7.1 Core entities

- `ChatSession`
- `ChatMessage`
- `ContextSnapshot`
- `RuleDecision`
- `SourceReference`
- `CandidateAction`
- `ActionConfirmation`
- `ActionExecutionResult`
- `EscalationRecord`
- `AuditEvent`

### 7.2 Suggested schemas

#### ChatSession

```json
{
  "sessionId": "sess_123",
  "customerId": "cust_123",
  "channel": "web",
  "createdAt": "2026-03-26T10:00:00Z",
  "expiresAt": "2026-03-26T10:30:00Z",
  "status": "active"
}
```

#### CandidateAction

```json
{
  "type": "freeze_card",
  "eligible": true,
  "requiresConfirmation": true,
  "summary": "Freeze card ending in 1234 immediately.",
  "confirmationText": "Do you want to freeze this card now?",
  "ruleReason": "Fraud-related request and active card found"
}
```

## 8. Request and Response APIs

### 8.1 Create or resume session

`POST /ai-chat/sessions`

Response:

```json
{
  "sessionId": "sess_123",
  "expiresAt": "2026-03-26T10:30:00Z",
  "suggestedPrompts": [
    "Why is my balance lower than expected?",
    "What is this charge?",
    "Why did my payment fail?"
  ]
}
```

### 8.2 Send message

`POST /ai-chat/messages`

Request:

```json
{
  "sessionId": "sess_123",
  "message": "Can I afford to send $500 today?",
  "selectedContext": {
    "accountId": "acc_123"
  }
}
```

Response:

```json
{
  "messageId": "msg_123",
  "type": "warning",
  "confidence": "high",
  "message": "Sending $500 today could leave you short for a scheduled debit due within 48 hours.",
  "sources": [
    {"type": "balance", "id": "bal_1"},
    {"type": "scheduled_payment", "id": "sp_22"}
  ],
  "nextActions": [
    {"type": "set_alert", "label": "Set a balance alert"},
    {"type": "escalate", "label": "Talk to support"}
  ],
  "requiresConfirmation": false
}
```

### 8.3 Confirm action

`POST /ai-chat/actions/confirm`

Request:

```json
{
  "sessionId": "sess_123",
  "actionType": "freeze_card",
  "actionToken": "acttok_123",
  "confirmed": true
}
```

### 8.4 Escalate

`POST /ai-chat/escalations`

### 8.5 Feedback

`POST /ai-chat/feedback`

## 9. Orchestration Flow by Journey

### 9.1 Balance explanation flow

```text
1. Receive user message
2. Classify intent as explain_balance
3. Load balances, recent transactions, pending items, fees, scheduled payments
4. Run balance delta rules to identify main contributors
5. Generate grounded explanation via LLM
6. Validate source references and allowed next actions
7. Return response or fallback to escalation if confidence/source quality is low
```

### 9.2 Suspicious charge flow

```text
1. Receive suspicious charge question
2. Classify as suspicious_charge
3. Load transaction, merchant enrichment, card state, dispute history
4. Run fraud-support rules and determine allowed actions
5. Generate explanation of what is known and unknown
6. Offer freeze card / start dispute if eligible
7. On confirmation, execute through action gateway
8. Return result and optionally prepare human handoff
```

### 9.3 Affordability check flow

```text
1. Receive amount and transfer intent
2. Extract requested amount and source account
3. Load balances and near-term scheduled obligations
4. Run forecast rules for approved time window
5. Produce risk result: safe / caution / warn
6. Generate customer-friendly explanation
7. Offer only safe next actions allowed by rules
```

## 10. Prompting Strategy

### 10.1 Prompt inputs

- user message
- prior relevant session turns only
- normalized context snapshot
- rule results and approved actions
- response schema and compliance constraints

### 10.2 Prompt safeguards

- never ask the model to decide eligibility
- never ask the model to invent policy interpretation outside provided rule outputs
- require uncertainty wording when source coverage is partial
- require citation using provided source IDs only

### 10.3 Example response schema

```json
{
  "answer": "string",
  "confidence": "high | medium | low",
  "sourceIds": ["string"],
  "nextActions": ["string"],
  "needsHuman": true,
  "tone": "calm"
}
```

## 11. Safety and Security Controls

### 11.1 Model boundary controls

- send minimum necessary customer context
- redact hidden internal notes and sensitive backend-only fields
- isolate prompts and responses in audited service boundary
- encrypt data in transit and at rest

### 11.2 Action controls

- action tokens are short-lived and bound to session, customer, and action type
- server-side revalidation happens at execution time
- duplicate submission protection for repeat confirmations
- irreversible or unsupported actions blocked by default

### 11.3 Abuse and operational controls

- request rate limiting
- prompt injection protection through strict structured prompting and allow-lists
- anomaly detection for rapid repeated action attempts
- kill switch to disable model output or action execution independently

### 11.4 Compliance controls

- version every prompt template, rule set, and model release
- retain auditable source-to-answer chain
- support legal disclosure injection per market/channel

## 12. Failure Modes and Fallbacks

| Failure | Example | System behavior |
|---|---|---|
| Missing context | card API timeout | answer with partial context if safe, or escalate |
| Low confidence | ambiguous payment failure | state uncertainty and offer support |
| Unsupported intent | investment advice request | refuse and redirect to supported channel |
| Action mismatch | card already frozen | return current state and updated options |
| Model/schema failure | invalid source ids | discard output and use fallback template |
| Rules unavailable | eligibility engine timeout | do not offer write action |

## 13. Storage Design

### 13.1 Session store

Stores:

- active session metadata
- recent turns
- action tokens
- minimal cached context references where allowed

Suggested properties:

- short TTL
- encrypted
- optimized for low-latency read/write

### 13.2 Audit store

Stores:

- immutable event log
- structured source references
- prompt and response metadata
- action confirmation and execution history

Suggested properties:

- append-only
- encrypted
- retention governed by policy

## 14. Observability and Evaluation

### 14.1 Operational metrics

- request latency by stage
- context source error rate
- model response validation failure rate
- action execution success rate
- escalation rate

### 14.2 Product metrics

- explain journey completion rate
- suspicious charge self-service completion rate
- alert creation rate
- trust/helpfulness score
- support deflection for scoped intents

### 14.3 Quality evaluation

- grounded answer coverage
- hallucination review rate
- correct action eligibility rate
- false refusal and false allow rate
- handoff package completeness

Recommendation:

- create offline replay datasets from anonymized or approved historical cases before widening production scope

## 15. Rollout Plan

### Phase 1: Read-only explain

- enable chat shell and session service
- support explain_balance, explain_fee, failed_payment, and merchant charge explanation
- no in-chat write actions
- all unsupported/low-confidence flows escalate

### Phase 2: Warn

- add affordability checks for approved forecast window
- add unusual spending and suspicious charge guidance
- continue redirecting transfer execution outside chat

### Phase 3: Act

- enable freeze card, set alert, and dispute initiation
- turn on confirmation flow, action gateway, and stronger audit controls

### Rollout controls

- internal dogfood
- employee beta
- limited customer cohort
- monitored ramp by intent and action type

## 16. Testing Strategy

### Unit tests

- rule calculations
- intent routing logic
- response validation
- action token handling

### Integration tests

- orchestrator with mocked banking APIs
- partial context failures
- action execution and revalidation
- escalation payload generation

### Safety tests

- unsupported advice prompts
- prompt injection attempts
- source citation corruption cases
- confirmation bypass attempts

### UAT scenarios

- balance lower than expected
- unknown card charge
- failed direct debit
- affordability warning before transfer
- freeze card success and already-frozen edge case

## 17. Open Technical Questions

- Which existing API gateway or BFF should host AI Chat endpoints?
- Are transaction labels and merchant enrichment good enough for explanation MVP, or is normalization work required first?
- What forecast horizon is acceptable and explainable for affordability checks?
- Should handoff integrate with current CRM, contact-center tooling, or secure case management?
- Which model provider and hosting pattern satisfy security, latency, and residency requirements?
- What level of prompt/response retention is permitted in each target market?

## 18. Recommended Build Sequence

1. ship orchestrator, sessioning, and read-only explanation flows
2. add rules-driven affordability and suspicious charge warning flows
3. add one write path at a time, starting with `freeze_card`
4. instrument and evaluate before widening scope

## 19. Summary

This design intentionally avoids a broad autonomous agent architecture. The MVP should be implemented as a deterministic banking workflow system with a constrained LLM explanation layer.

That gives the product the best chance of being:

- trustworthy for customers
- auditable for compliance
- maintainable for engineering
- expandable over time without losing control of risk
