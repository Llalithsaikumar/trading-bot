import uuid
import pytest
from app.domain.models.memory import LongTermMemory
from app.services.embedding.embedding_service import EmbeddingService
from app.infrastructure.repositories.memory_repository import MemoryRepository


@pytest.mark.anyio
async def test_embedding_service():
    embed_service = EmbeddingService()
    vector = await embed_service.embed_query("BTC buy reasoning indicators")
    assert len(vector) == 1536
    assert isinstance(vector[0], float)


@pytest.mark.anyio
async def test_memory_repository_semantic_search(db_session):
    strategy_id = uuid.uuid4()
    run_id1 = str(uuid.uuid4())
    run_id2 = str(uuid.uuid4())

    embed_service = EmbeddingService()

    text1 = "Extremely bullish BTC indicators"
    text2 = "Very bearish BTC selling pressure"

    vec1 = await embed_service.embed_query(text1)
    vec2 = await embed_service.embed_query(text2)

    mem1 = LongTermMemory(
        strategy_id=strategy_id,
        run_id=run_id1,
        symbol="BTC/USDT",
        signal="buy",
        confidence=0.9,
        reasoning="bullish indicator",
        news_summary="bullish news",
        indicators_summary="RSI low",
        performance_summary="good",
        lessons_learned="buy dip",
        reflection="great trade",
        embedding_text=text1,
        embedding=vec1,
    )

    mem2 = LongTermMemory(
        strategy_id=strategy_id,
        run_id=run_id2,
        symbol="BTC/USDT",
        signal="sell",
        confidence=0.8,
        reasoning="bearish sell off",
        news_summary="bad news",
        indicators_summary="RSI high",
        performance_summary="good",
        lessons_learned="sell early",
        reflection="saved capital",
        embedding_text=text2,
        embedding=vec2,
    )

    repo = MemoryRepository(db_session)
    await repo.create(mem1)
    await repo.create(mem2)
    await db_session.commit()

    # Query matching text1
    query_vector1 = await embed_service.embed_query("BTC bullish indicators")
    results = await repo.search_semantic(strategy_id, query_vector1, limit=1)

    assert len(results) == 1
    assert results[0].run_id == run_id1
    assert results[0].signal == "buy"
