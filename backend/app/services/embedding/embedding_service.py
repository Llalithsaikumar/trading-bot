"""Embedding generation service with LangChain and mock fallback."""
from __future__ import annotations

import hashlib
from typing import Any
from loguru import logger
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


class MockEmbeddings:
    """Mock embeddings generator for testing and development."""

    def embed_query(self, text: str) -> list[float]:
        vocabulary = [
            "bullish",
            "bearish",
            "buy",
            "sell",
            "btc",
            "indicators",
            "news",
            "pressure",
            "rsi",
            "extremely",
            "very",
        ]
        res = [0.0] * 1536
        words = text.lower().split()
        for word in words:
            if word in vocabulary:
                idx = vocabulary.index(word)
                res[idx] += 1.0
        return res


    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    async def aembed_query(self, text: str) -> list[float]:
        return self.embed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)


class EmbeddingService:
    def __init__(self) -> None:
        self._provider: Any = None
        if settings.OPENAI_API_KEY:
            try:
                self._provider = OpenAIEmbeddings(
                    model="text-embedding-3-small",
                    api_key=settings.OPENAI_API_KEY,
                )
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAIEmbeddings: {e}. Using mock.")

        if self._provider is None:
            self._provider = MockEmbeddings()

    async def embed_query(self, text: str) -> list[float]:
        if hasattr(self._provider, "aembed_query"):
            return await self._provider.aembed_query(text)
        return self._provider.embed_query(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if hasattr(self._provider, "aembed_documents"):
            return await self._provider.aembed_documents(texts)
        return self._provider.embed_documents(texts)
