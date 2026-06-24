"""One-shot script: generate 384-dim embeddings for all products and store in pgvector."""
import asyncio
import uuid
from datetime import UTC, datetime

from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text


async def main():
    print("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    print("Model loaded.")

    engine = create_async_engine(
        "postgresql+asyncpg://snaptrip:snaptrip_dev_pass@postgres:5432/snaptrip_dev"
    )

    async with AsyncSession(engine) as session:
        result = await session.execute(
            text("SELECT id, name, sub_title, keywords FROM pms_products")
        )
        products = result.fetchall()
        print(f"Got {len(products)} products")

        texts = [
            f"{p.name or ''} {p.sub_title or ''} {p.keywords or ''}".strip()
            for p in products
        ]
        print(f"Generating {len(texts)} embeddings...")
        embeddings = model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        print(f"Embeddings shape: {embeddings.shape}")

        for p, emb in zip(products, embeddings):
            pid = str(p.id)
            emb_str = f"[{','.join(map(str, emb.tolist()))}]"
            rid = str(uuid.uuid4())
            await session.execute(
                text(
                    """
                    INSERT INTO pms_product_embeddings (id, product_id, embedding, model_name, updated_at)
                    VALUES (CAST(:rid AS uuid), CAST(:pid AS uuid), CAST(:embedding AS vector(384)), 'all-MiniLM-L6-v2', NOW())
                    ON CONFLICT (product_id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        model_name = EXCLUDED.model_name,
                        updated_at = NOW()
                    """
                ),
                {"rid": rid, "pid": pid, "embedding": emb_str},
            )

        await session.commit()
        print(f"Inserted {len(products)} embeddings")

        result = await session.execute(
            text("SELECT COUNT(*) FROM pms_product_embeddings")
        )
        total = result.scalar()
        print(f"Total embeddings in DB: {total}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
