# Agent Review: Multi-Agent Trading Architecture

This document provides a comprehensive review of the 10 trading agents within the platform, evaluating their classifications, correctness, edge-case behavior, and operational risks.

---

## Agent Taxonomy Summary

| Agent | Classification | Core Function | Decision Type |
|---|---|---|---|
| **MemoryAgent** | Hybrid | Loads short/long-term context at start | Deterministic / Semantic Search |
| **MarketAgent** | Deterministic | Fetches OHLCV, tickers, and order books | REST / WebSocket Feeds |
| **NewsAgent** | Deterministic | Fetches news headlines and computes sentiment | Math Averages (Mock Data) |
| **TechnicalAgent** | Deterministic | Calculates technical indicators via pandas-ta | Dataframe Calculations |
| **PortfolioAgent** | Deterministic | Compiles balance, positions, and open orders | SQL Queries / Formatting |
| **DecisionAgent** | LLM-Driven | Generates BUY/SELL/WAIT signals & TP/SL targets | Structured LLM Output |
| **RiskAgent** | Deterministic | Validates signals and calculates position sizes | Math Rules / Sizing Models |
| **ExecutionAgent** | Deterministic | Places orders on live/simulated exchanges | REST Order Operations |
| **ReflectionAgent** | LLM-Driven | Reviews execution cycle parameters | Structured LLM Output |
| **TradeReflectionAgent** | LLM-Driven | Conducts post-trade post-mortem review | Structured LLM Output |

---

## Detailed Agent Audits

### 1. MemoryAgent
*   **Classification**: Hybrid. Uses deterministic Redis/SQL context loading alongside hybrid semantic pgvector search.
*   **Correctness**: Correctly deserializes past signals and queries strategy executions.
*   **Edge Cases**:
    *   If Redis is down or database session is missing, it catches exceptions and proceeds cleanly (graceful degradation).
    *   If semantic search fails, it logs a warning and returns the deterministic context only.
*   **Missing Safeguards**: No context size limits. Highly verbose reflections or lessons could exceed the LLM's context window in subsequent nodes.
*   **Confidence Scoring**: N/A (retrieves saved metrics).
*   **Hallucination Risk**: Low. Strictly formats retrieved values.
*   **Error Handling**: High. Isolated try-except blocks protect Redis, SQL, and embedding lookups.

---

### 2. MarketAgent
*   **Classification**: Deterministic. Runs REST queries or WebSocket listeners.
*   **Correctness**: Correctly maps CCXT outputs to Pydantic/database models.
*   **Edge Cases**:
    *   If WebSocket streams fail or are unsupported, the agent automatically falls back to REST polling (`_run_rest_fallback_loop`).
*   **Missing Safeguards**:
    *   No rate limit protection in the REST polling loop. High frequency API queries can trigger rate-limit bans.
    *   No fallback exchanges configured if the primary exchange is unreachable.
*   **Confidence Scoring**: N/A.
*   **Hallucination Risk**: Zero.
*   **Error Handling**: High. Automatic WebSocket reconnect with sleep intervals, backed by a REST fallback thread.

---

### 3. NewsAgent
*   **Classification**: Deterministic. Average sentiment is mathematically calculated.
*   **Correctness**: Average logic is correct, but relies entirely on hardcoded mock headlines.
*   **Edge Cases**: Returns a safe `neutral` label if the news headline feed is empty.
*   **Missing Safeguards**: Weights all news sources equally. Does not differentiate between high-impact headlines and minor blogs.
*   **Confidence Scoring**: N/A.
*   **Hallucination Risk**: Zero (mock data is static).
*   **Error Handling**: Standard try-except wrapper.

---

### 4. TechnicalAgent
*   **Classification**: Deterministic. Powered by `pandas-ta`.
*   **Correctness**: High. Correctly calculates indicators. Checks for existing database entries first to prevent unique constraint failures.
*   **Edge Cases**: Individual indicator calculation errors (e.g., VWAP failing on insufficient data) are caught to prevent breaking the calculation loop.
*   **Missing Safeguards**: If the input OHLCV dataset is too small (e.g., <50 rows), indicators like MACD or EMA can return NaN, which may cause parsing errors downstream.
*   **Confidence Scoring**: N/A.
*   **Hallucination Risk**: Zero.
*   **Error Handling**: Standard node exception handling wrapper.

---

### 5. PortfolioAgent
*   **Classification**: Deterministic. Reads database models.
*   **Correctness**: Correctly calculates win rates, open position count, and daily/total PnL metrics.
*   **Edge Cases**: Missing portfolio UUIDs or database sessions degrade to empty lists safely.
*   **Missing Safeguards**:
    *   Exposure math assumes spot trading. It does not calculate margin/leverage multipliers correctly.
    *   Win rate division by zero is handled, but no win rate is calculated if total trades = 0.
*   **Confidence Scoring**: N/A.
*   **Hallucination Risk**: Zero.
*   **Error Handling**: Isolated node try-except block.

---

### 6. DecisionAgent
*   **Classification**: LLM-driven.
*   **Correctness**: Correctly routes decisions to `TradingSignal` enums.
*   **Edge Cases**:
    *   If structured output fails, falls back to raw JSON parsing.
    *   If raw parsing fails, defaults to a neutral `WAIT` signal with 0.0 confidence.
*   **Missing Safeguards**:
    *   The LLM can suggest entry, stop-loss, and take-profit prices outside the current price bounds.
    *   Relies entirely on the downstream `RiskAgent` to catch bad SL/TP levels.
*   **Confidence Scoring**: Generated by the LLM (0.0 to 1.0). Subject to LLM confidence bias (typically overconfident).
*   **Hallucination Risk**: High. The LLM could hallucinate price levels or patterns from the context data.
*   **Prompt Quality**: High. The template includes detailed structured inputs (tickers, news, positions, indicators, and past reflections).
*   **Error Handling**: Fallback chain handles structured failure $\rightarrow$ raw parsing failure $\rightarrow$ safe stub.

---

### 7. RiskAgent
*   **Classification**: Deterministic. Runs mathematical rule functions.
*   **Correctness**: Correctly calculates position sizing (1% risk limit vs. Kelly Criterion).
*   **Edge Cases**: Handles missing session values or portfolio references by skipping database-dependent rules (e.g., drawdown, consecutive losses).
*   **Missing Safeguards**:
    *   Kelly Criterion doesn't cap sizing on high-volatility events.
    *   Positions sizing formulas assume spot equivalent calculation.
*   **Confidence Scoring**: Computes a `risk_score` (0.0 to 1.0). Each violation subtracts 0.2, and critical violations subtract 0.4.
*   **Hallucination Risk**: Zero.
*   **Error Handling**: High. Each rule is executed in an isolated try-except block, preventing a single rule exception from crashing the entire risk evaluation cycle.

---

### 8. ExecutionAgent
*   **Classification**: Deterministic. Selects adapters and places orders.
*   **Correctness**: Pre-flight validation blocks execution if the signal is NEUTRAL or available balance is zero.
*   **Edge Cases**: Performs a database rollback on execution failures.
*   **Missing Safeguards**:
    *   Slippage parameters are not validated during order submission.
    *   No price deviation limits relative to the current spot price.
*   **Confidence Scoring**: N/A.
*   **Hallucination Risk**: Zero.
*   **Error Handling**: High. Cleans up transactions with rollbacks and updates the node state on exceptions.

---

### 9. ReflectionAgent
*   **Classification**: LLM-driven. Analyzes the execution cycle.
*   **Correctness**: Correctly structures signal and process quality scores.
*   **Edge Cases**: Falls back to `_stub_reflection` when LLM invocation or JSON parsing fails.
*   **Missing Safeguards**: Stub reflection uses hardcoded placeholding parameters.
*   **Confidence Scoring**: Calculates signal quality score based on indicators and data presence.
*   **Hallucination Risk**: Medium. LLM could hallucinate process issues.
*   **Prompt Quality**: Good. Details signal quality, news, indicators, and node execution errors.
*   **Error Handling**: Graceful degradation to stub on LLM or parsing errors.

---

### 10. TradeReflectionAgent
*   **Classification**: LLM-driven.
*   **Correctness**: Reviews trade outcomes against original context parameters.
*   **Edge Cases**: Safe fallback stub on failure. Increments or decrements strategy confidence by 0.05.
*   **Missing Safeguards**: Incremental confidence changes do not check for custom strategy bounds or constraints.
*   **Confidence Scoring**: Recommends adjustment direction ("increase" \| "decrease" \| "no_change").
*   **Hallucination Risk**: Medium. LLM could suggest lessons learned unrelated to the trade's quantitative outcome.
*   **Prompt Quality**: High. Formats strategy context, execution performance, and original decision context.
*   **Error Handling**: Fallback chain protects LLM invocation and database persistence.
