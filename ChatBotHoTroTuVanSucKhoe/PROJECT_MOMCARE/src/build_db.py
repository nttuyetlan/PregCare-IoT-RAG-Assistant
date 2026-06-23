"""
src/build_db.py — ChromaDB Ingestion Pipeline for Mầm Nhỏ

PURPOSE:
    Reads curated medical JSONL data (47 chunks from the official
    "Cẩm Nang Thai Kỳ" handbook), validates schema, embeds text
    using vietnamese-sbert, and stores into ChromaDB.
    This is a ONE-TIME build script (run during deployment setup).

ARCHITECTURE DECISIONS:
    - No chunking: Each JSONL record is a complete Q&A pair,
      preserving medical context integrity.
    - Metadata preserved: trimester, topic, red_flag stored as
      ChromaDB metadata for filtered retrieval.
    - vietnamese-sbert: Chosen for Vietnamese semantic similarity.
      Runs locally, no API calls.

USAGE:
    python -m src.build_db           # Build from default path
    python -m src.build_db --reset   # Wipe and rebuild
"""

import argparse
import shutil
import sys
from pathlib import Path

from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_settings, setup_logging, PROJECT_ROOT
from src.utils import load_jsonl, validate_jsonl_schema, Timer


def get_embedding_function(model_path: str):
    """
    Create a SentenceTransformer embedding function for ChromaDB.

    Uses vietnamese-sbert for high-quality Vietnamese embeddings.
    Falls back to a default multilingual model if local model
    is not found (for development/testing).

    Args:
        model_path: Path to local sentence-transformer model

    Returns:
        ChromaDB-compatible embedding function
    """
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    abs_path = PROJECT_ROOT / model_path
    if abs_path.exists():
        logger.info(f"Loading local embedding model: {abs_path}")
        return SentenceTransformerEmbeddingFunction(
            model_name=str(abs_path),
            device="cpu",  # ARM64 CPU on Orange Pi 5
        )
    else:
        logger.warning(
            f"Local model not found at {abs_path}. "
            f"Falling back to 'keepitreal/vietnamese-sbert' (requires internet)."
        )
        return SentenceTransformerEmbeddingFunction(
            model_name="keepitreal/vietnamese-sbert",
            device="cpu",
        )


def build_database(reset: bool = False) -> None:
    """
    Main ingestion pipeline: JSONL → Validate → Embed → ChromaDB.

    Args:
        reset: If True, delete existing vector_db and rebuild from scratch.
    """
    settings = get_settings()
    setup_logging(settings)

    jsonl_path = settings.abs_data_jsonl_path
    db_path = settings.abs_vector_db_path
    collection_name = settings.chroma_collection_name

    logger.info("=" * 60)
    logger.info("🌱 Mầm Nhỏ — ChromaDB Build Pipeline")
    logger.info("=" * 60)
    logger.info(f"JSONL source: {jsonl_path}")
    logger.info(f"Vector DB target: {db_path}")
    logger.info(f"Collection: {collection_name}")

    # ── Step 1: Reset if requested ──
    if reset and db_path.exists():
        logger.warning(f"Resetting: deleting existing DB at {db_path}")
        shutil.rmtree(db_path)

    # ── Step 2: Load and validate JSONL ──
    with Timer("JSONL loading", log_level="INFO"):
        records = load_jsonl(jsonl_path)

    if not records:
        logger.error("No records loaded. Aborting.")
        sys.exit(1)

    # Validate each record
    valid_records = []
    for i, record in enumerate(records):
        is_valid, error = validate_jsonl_schema(record)
        if is_valid:
            valid_records.append(record)
        else:
            logger.warning(f"Record {i} failed validation: {error}")

    logger.info(
        f"Validation: {len(valid_records)}/{len(records)} records passed"
    )

    if not valid_records:
        logger.error("No valid records. Aborting.")
        sys.exit(1)

    # ── Step 3: Initialize ChromaDB ──
    import chromadb

    db_path.mkdir(parents=True, exist_ok=True)

    with Timer("ChromaDB initialization", log_level="INFO"):
        client = chromadb.PersistentClient(path=str(db_path))
        embed_fn = get_embedding_function(settings.sbert_model_path)

        # Get or create collection
        collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"},  # Cosine similarity
        )

    # ── Step 4: Check for existing data ──
    existing_count = collection.count()
    if existing_count > 0 and not reset:
        logger.info(
            f"Collection already has {existing_count} documents. "
            f"Use --reset to rebuild."
        )
        return

    # ── Step 5: Prepare documents for ingestion ──
    ids = []
    documents = []
    metadatas = []

    for record in valid_records:
        # Use chunk_id if available, else generate from index
        doc_id = record.get("chunk_id", f"doc-{len(ids)}")
        ids.append(doc_id)
        documents.append(record["text"])

        # Flatten metadata for ChromaDB (no nested dicts)
        meta = {
            "trimester": record["metadata"]["trimester"],
            "topic": record["metadata"]["topic"],
            "red_flag": record["metadata"]["red_flag"],
        }
        # Add optional fields for traceability
        if "page_start" in record:
            meta["page_start"] = record["page_start"]
        if "page_end" in record:
            meta["page_end"] = record["page_end"]
        if "chunk_index" in record:
            meta["chunk_index"] = record["chunk_index"]

        metadatas.append(meta)

    # ── Step 6: Batch insert into ChromaDB ──
    BATCH_SIZE = 50  # ChromaDB recommends batches for large datasets

    with Timer("Embedding + Ingestion", log_level="INFO"):
        for start in range(0, len(ids), BATCH_SIZE):
            end = min(start + BATCH_SIZE, len(ids))
            collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )
            logger.debug(f"Ingested batch {start}-{end}")

    # ── Step 7: Verify ──
    final_count = collection.count()
    logger.info(f"✅ Build complete: {final_count} documents in ChromaDB")

    # Quick sanity check — query with a test phrase from the dataset
    test_query = "mang thai nên ăn gì để bổ sung dinh dưỡng"
    with Timer("Sanity check query", log_level="INFO"):
        results = collection.query(
            query_texts=[test_query],
            n_results=min(2, final_count),
        )

    if results and results["documents"]:
        logger.info(f"Sanity check passed. Top result preview:")
        for doc in results["documents"][0]:
            logger.info(f"  → {doc[:100]}...")
    else:
        logger.warning("Sanity check returned no results!")

    logger.info("=" * 60)
    logger.info("🌱 Build pipeline complete!")
    logger.info("=" * 60)


# ── CLI Entry Point ──────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build ChromaDB from medical JSONL data"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing DB and rebuild from scratch",
    )
    args = parser.parse_args()
    build_database(reset=args.reset)
