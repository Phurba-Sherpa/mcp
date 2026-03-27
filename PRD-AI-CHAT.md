# PRD: AI Chat for Internet Banking

Status: Draft
Owner: Product / Engineering / Design
Last updated: 2026-03-26

## 1. Overview

AI Chat is a banking copilot inside the internet banking application. It helps customers understand what happened in their accounts, decide what to do next, and complete a small set of safe banking actions.

This is not a generic FAQ bot. The product focuses on real customer pain: unexpected balance changes, suspicious charges, failed payments, short-term cash anxiety, and confusing banking flows that normally require support contact.

## 2. Problem Statement

Customers do not usually come to internet banking because they want a conversation. They come because something feels wrong, risky, urgent, or confusing.

Today, customers often struggle to:

- understand why their balance changed
- explain fees, pending items, or failed payments
- judge whether they can safely make a transfer or payment
- respond quickly to suspicious charges or card issues
- navigate support-heavy flows such as disputes, alerts, and card controls

Existing FAQ and help content does not solve these problems well because it is generic, detached from the customer's actual account state, and unable to guide the customer through resolution.

## 3. Product Goal

Help customers solve money-related issues faster and with more confidence by combining:

- grounded explanations based on real account context
- clear next-step recommendations
- a limited set of safe, auditable in-chat actions

## 4. Goals and Non-Goals

### Goals

- reduce customer effort on high-friction service journeys
- reduce support volume for explainable, repeatable banking issues
- improve customer trust by giving concise, grounded answers with evidence
- enable safe completion of a small number of high-value actions in chat

### Non-Goals

- open-ended personal financial advice
- investment or tax advice
- loan underwriting or credit decisioning
- unrestricted AI-driven action execution
- replacing human agents for complex, sensitive, or low-confidence cases

## 5. Target Users

Primary target users:

- digitally active retail banking customers using web or mobile banking
- customers experiencing a specific issue they want resolved now

High-priority pain moments:

- "Why is my balance lower than I expected?"
- "What is this charge?"
- "Why did my payment fail?"
- "Can I afford to send this money today?"
- "This looks fraudulent. What should I do?"

## 6. Core Value Proposition

AI Chat tells the customer:

- what happened
- what it means
- what they can do next
- whether the bank can help complete that action now

Proposed customer promise:

"Tell me what happened, what it means, and help me fix it."

## 7. MVP Scope

The MVP focuses on three problem areas.

### 7.1 Explain balances, fees, transactions, and failed payments

The customer can ask plain-language questions about:

- balance changes
- recent and pending transactions
- fees and charges
- failed or reversed payments
- due amounts and upcoming obligations

The system responds using real customer context and cites the relevant underlying facts.

### 7.2 Detect short-term money risk and unusual activity

The customer can ask if a payment or transfer is safe.

The system can:

- estimate near-term balance impact
- consider upcoming obligations in a limited forecast window
- flag unusual spending patterns or suspicious-looking transactions
- suggest safe next steps such as wait, move funds, freeze card, or contact support

### 7.3 Guide and complete safe actions

The system can guide and support a small set of safe actions:

- freeze card
- set alerts
- initiate suspicious charge dispute flow

All actions must be eligibility-checked, clearly summarized, and explicitly confirmed by the customer before execution.

## 8. Out of Scope for MVP

- cross-product financial coaching
- debt restructuring advice
- investment and wealth guidance
- large autonomous workflows across many banking products
- unsupervised transfer execution based on conversational intent alone
- complex complaints handling without human review

## 9. User Stories

### Explain

- As a customer, I want to ask why my balance changed so I can understand what happened without searching through multiple screens.
- As a customer, I want to ask about a fee so I can see what triggered it and when it applied.
- As a customer, I want to ask why a payment failed so I know what to do next.
- As a customer, I want help interpreting a merchant charge so I can decide whether it is legitimate.

### Warn

- As a customer, I want to ask whether I can afford a transfer so I do not cause an overdraft or miss another payment.
- As a customer, I want the system to highlight unusual spending so I can react earlier.
- As a customer, I want the system to warn me when upcoming obligations may exceed my available funds.

### Act

- As a customer, I want to freeze my card from chat if I suspect fraud.
- As a customer, I want to start a dispute flow from chat if I do not recognize a charge.
- As a customer, I want to set an alert from chat so I can monitor my account more closely.

### Escalate

- As a customer, I want to reach a human agent without repeating myself.
- As an agent, I want to see the chat summary, evidence, and attempted actions so I can resolve the issue faster.

## 10. Key User Journeys

### Journey 1: Why is my balance lower?

1. Customer opens AI Chat from authenticated banking.
2. Customer asks why the balance dropped.
3. System retrieves balances, recent debits, pending items, fees, and upcoming obligations.
4. Rules layer identifies the main contributors.
5. LLM explanation layer turns those facts into plain language.
6. Customer sees answer with cited sources and suggested next steps.

### Journey 2: I do not recognize this charge

1. Customer asks about a suspicious transaction.
2. System retrieves transaction details and any known merchant enrichment.
3. System explains what is known and what remains uncertain.
4. System offers safe next actions such as freeze card or dispute.
5. If the customer chooses an action, the system shows a confirmation summary.
6. The action is executed only after explicit confirmation.

### Journey 3: Can I afford this transfer?

1. Customer asks about sending a specific amount.
2. System retrieves current and available balances plus upcoming scheduled outflows.
3. Rules layer calculates a limited near-term projection.
4. System responds with a simple explanation of risk and options.
5. If the customer still wants to proceed, the chat can redirect to the existing transfer flow or, in later phases, support a safe in-chat transfer journey if approved.

## 11. Functional Requirements

### 11.1 Channel and session

- AI Chat is available inside authenticated internet banking.
- The user does not re-authenticate inside chat.
- Chat sessions can be resumed for a limited period.
- Session timeout and device security policies follow existing banking standards.

### 11.2 Context retrieval

- Retrieve current and available balances with timestamp.
- Retrieve recent, pending, and reversed transactions.
- Retrieve scheduled payments, direct debits, standing orders, and transfers where available.
- Retrieve card status, existing disputes, and configured alerts.
- Normalize source data enough to support explanation and citation.

### 11.3 Conversation handling

- Classify messages into explanation, warning, action, unsupported, or escalation intents.
- Support short follow-up questions within the same session.
- Preserve enough session context to avoid asking the customer to repeat details.

### 11.4 Explanation behavior

- Every explanation must be grounded in account data, policy logic, or both.
- The response must distinguish observed facts from suggested next steps.
- Low-confidence answers must say so clearly and offer escalation.

### 11.5 Action execution

- Only approved actions may be offered.
- Every action must pass deterministic eligibility checks.
- Every action must show a clear summary before confirmation.
- No action is executed without explicit confirmation.
- Action result must be returned in chat and stored in audit logs.

### 11.6 Human handoff

- Customers can escalate to human support from any state.
- Handoff includes issue summary, cited sources, detected intent, and attempted actions.

## 12. Safety, Trust, and Compliance Requirements

- The system must never invent balances, fees, transaction details, eligibility, or policy outcomes.
- Facts and action permissions come from deterministic bank systems, not the LLM alone.
- The LLM may explain and summarize, but it is not the source of truth.
- Unsupported or regulated topics must be blocked or escalated.
- Irreversible or high-risk actions require explicit confirmation and auditable logging.
- The system must preserve a machine-readable record of sources used in each answer.
- Customer-visible answers should indicate uncertainty where appropriate.
- PII handling, retention, and model-boundary controls must follow bank policy and local regulation.

## 13. UX Principles

- start from customer intent, not a help-center taxonomy
- keep answers short, direct, and specific
- show why the system said something by citing underlying events or rules
- always end with a useful next step
- keep human support easy to reach
- avoid false confidence and avoid pretending to know more than the system can verify

## 14. Success Metrics

### Customer outcomes

- reduced time to resolution for scoped service journeys
- increased customer-reported helpfulness and trust
- higher completion rate for supported in-chat actions

### Business outcomes

- reduced support contact volume for fee, payment, balance, and suspicious-charge inquiries
- improved containment for high-confidence scoped journeys
- improved agent efficiency when chats are escalated

### Quality and safety

- grounded-answer rate
- low-confidence fallback rate
- unsupported intent rate
- action confirmation to completion rate
- audit completeness rate
- QA-reviewed hallucination rate

## 15. MVP Release Plan

### Phase 1: Read-only explanations

- chat entrypoint
- session management
- balance, fee, transaction, and failed-payment explanations
- source citations
- escalation to human support

### Phase 2: Warnings and risk guidance

- near-term affordability checks
- unusual spending detection
- suspicious charge guidance

### Phase 3: Safe actions

- freeze card
- set alerts
- initiate dispute flow
- confirmation and action audit trail

## 16. Proposed High-Level Architecture

- `Chat UI`: authenticated web/mobile banking interface
- `Chat Orchestrator`: session, intent routing, prompt assembly, response composition
- `Context Aggregator`: balances, transactions, scheduled items, card state, alerts, dispute context
- `Policy Engine`: deterministic rules for explainability, affordability, eligibility, and compliance
- `LLM Explanation Layer`: plain-language explanation and summarization only
- `Action Gateway`: approved write actions with confirmation and audit
- `Escalation Service`: handoff package for support agents
- `Audit and Observability`: logs, metrics, versioning, evaluation

Architectural principle: keep facts and actions deterministic; use the model for understanding and explanation.

## 17. Dependencies

- authenticated chat entrypoint in existing banking channels
- access to account, transaction, payment, card, alert, and dispute APIs
- merchant enrichment or transaction normalization where available
- policy and compliance review for supported answer and action types
- observability and audit logging infrastructure
- human-support integration for handoff

## 18. Risks

### Product risks

- too-broad scope turns the product into a weak generic chatbot
- customer trust drops quickly if explanations are vague or wrong
- high-value action flows may require more legacy integration effort than expected

### Technical risks

- fragmented banking APIs produce incomplete context
- poor transaction labeling limits explanation quality
- model outputs may sound confident even when source data is ambiguous

### Compliance risks

- accidental drift into regulated advice
- incomplete auditability of outputs or actions
- improper handling of sensitive customer data at the model boundary

## 19. Open Questions

- Which banking APIs are currently available for transactions, scheduled payments, card state, alerts, and disputes?
- What forecast window is acceptable for MVP affordability checks?
- Should transfer execution remain outside chat for MVP, with chat only providing guidance?
- Which channels ship first: web banking, mobile banking, or both?
- Which human-support platform will receive escalations and transcript summaries?
- What answer styles or disclosures are required by legal and compliance teams?

## 20. Recommendation

Ship AI Chat first as a narrow, high-trust banking copilot focused on `Explain -> Warn -> Act`.

Do not launch it as a broad assistant. The fastest path to customer value and bank-safe adoption is:

1. explain real account events clearly
2. warn about immediate money risk in limited scenarios
3. enable a very small set of safe actions with explicit confirmation

## 21. Appendix: Example Prompt Starters

- Why is my balance lower than expected?
- What is this charge?
- Why did my payment fail?
- Can I safely send $2,500 today?
- This transaction looks suspicious.
- Help me freeze my card.
