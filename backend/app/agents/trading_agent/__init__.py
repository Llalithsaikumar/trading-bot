"""
Main trading agent — orchestrates the full analysis → decision → execution pipeline.
Uses LangGraph to compose:
  1. MarketDataNode   – fetch OHLCV + order book
  2. AnalysisNode     – compute technical indicators
  3. LLMDecisionNode  – LLM reasoning over market state
  4. RiskNode         – enforce risk limits
  5. ExecutionNode    – place order via exchange
"""
