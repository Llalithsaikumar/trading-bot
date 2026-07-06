# Performance Audit

This document presents a performance audit of the trading platform, identifying key performance bottlenecks, synchronization constraints, database locking issues, and opportunities for speedups.

---

## 1. Summary of Identified Bottlenecks

| # | Category | Bottleneck | Severity | Impact | Recommendation |
|---|---|---|:-----:|---|---|
| 1 | **Unnecessary API Calls** | MemoryAgent double-queries pricing and news before the main nodes run | 🔴 High | Adds 0.5s–1.5s latency per strategy execution cycle | Pass ticker/news references or remove the pre-fetch query |
| 2 | **Database Bottlenecks** | Missing DB indices on time-series tables (`equity_history`, `long_term_memories`) | 🔴 High | Slow range queries; semantic searches perform full table scans | Add composite indexes and HNSW/IVFFlat index for vector columns |
| 3 | **WebSocket Scaling** | In-memory WS manager lacks Pub/Sub synchronization | 🔴 High | WS broadcasts are lost across multi-instance API deployments | Integrate Redis Pub/Sub into the FastAPI WebSocket layer |
| 4 | **Async / Celery** | Creating new event loops per Celery worker task (`asyncio.new_event_loop`) | 🟡 Medium | Heavy startup overhead and thread resource leaks | Switch Celery pool to `gevent` or use `asgiref.sync.async_to_sync` |
| 5 | **API Connection Hold** | DB connections are held open for the duration of route handlers | 🟡 Medium | Rapidly exhausts connection pool under high traffic | Flush and commit early; reduce scope of async database sessions |
| 6 | **Unnecessary LLM Calls** | Reflection node invokes LLM even when RiskAgent rejects the trade | 🟡 Medium | Increases LLM costs and adds unnecessary latency | Short-circuit reflection when `risk_approved = False` and `order_placed = False` |

---

## 2. In-Depth Bottleneck Analysis

### 1. The MemoryAgent Double-Query Pattern (Unnecessary API Calls)
*   **Problem**: In `memory_node.py` ([load_context](file:///c:/Users/Lalith%20Sai%20Kumar/Desktop/mirofish/crypto-trading-platform/backend/app/agents/nodes/memory_node.py#L50)), the agent queries the market data service for the current price and invokes `NewsAgent` to fetch news. This is done purely to construct a semantic query text for the embedding lookup. Immediately afterward, the `MarketAgent` and `NewsAgent` run in the graph and fetch the exact same data again.
*   **Impact**: Adds redundant REST API requests and slows down graph startup.
*   **Fix**: Modify the DAG structure so `MarketAgent` and `NewsAgent` run first. Their output can then be passed to the `MemoryAgent` to run the semantic query, removing the need for duplicate lookups.

### 2. Missing Indexes on High-Frequency Tables (Database Bottlenecks)
*   **Problem**:
    *   `equity_history` has no composite index on `(portfolio_id, timestamp)`. Range queries for charting perform full table scans.
    *   `long_term_memories` table stores pgvector embeddings but lacks a vector index (e.g., HNSW). As trading history grows, semantic searches slow down.
*   **Impact**: Query performance degrades over time.
*   **Fix**: Add the following indexes in the database schema:
    ```sql
    CREATE INDEX ix_equity_history_portfolio_timestamp ON equity_history (portfolio_id, timestamp DESC);
    CREATE INDEX ix_long_term_memories_embedding ON long_term_memories USING hnsw (embedding vector_cosine_ops);
    ```

### 3. In-Memory WebSocket Manager Limitation (WebSocket Bottlenecks)
*   **Problem**: The `ws_manager` maintains a subscription map in python memory. If the backend scales horizontally (e.g., 3 backend containers behind an Nginx load balancer), clients connected to backend instance A will not receive ticker updates broadcast by Celery workers connected to backend instance B.
*   **Impact**: Live dashboard updates fail to propagate to users in scaled production environments.
*   **Fix**: Refactor `ws_manager` to use a Redis-backed Pub/Sub mechanism:
    ```
    Celery Task ──> Redis Pub/Sub ──> FastAPI Nodes ──> WebSockets ──> Clients
    ```

### 4. Async Execution in Sync Celery Workers (Async Problems)
*   **Problem**: In `trading_tasks.py` ([_run](file:///c:/Users/Lalith%20Sai%20Kumar/Desktop/mirofish/crypto-trading-platform/backend/app/workers/tasks/trading_tasks.py#L17)), sync Celery tasks run async coroutines by creating a new event loop per invocation. This thread-management pattern is inefficient under high load.
*   **Impact**: High thread overhead and potential resource leaks.
*   **Fix**: Use `asgiref.sync.async_to_sync` to run coroutines in Celery, or migrate the worker pool to a natively async pool like `celery-pool-asyncio`.

### 5. Unnecessary LLM Calls on Rejections
*   **Problem**: If the `RiskAgent` rejects a signal, no order is placed. However, the graph still routes execution to the `ReflectionAgent` which invokes the LLM to review the cycle.
*   **Impact**: Unnecessary token costs and latency for aborted signals.
*   **Fix**: Use the deterministic reflection stub `_stub_reflection` when no trade has occurred, bypassing the LLM call entirely.
