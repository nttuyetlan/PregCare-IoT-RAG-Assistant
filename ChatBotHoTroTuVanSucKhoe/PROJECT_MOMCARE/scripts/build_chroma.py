import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

BASE = Path(__file__).resolve().parents[1]
CHUNKS_PATH = BASE / 'data' / 'extracted' / 'chunks_for_chroma.jsonl'
CHROMA_DIR = BASE / 'data' / 'chroma_db'
COLLECTION_NAME = 'momcare_knowledge'
EMBED_MODEL_NAME = 'intfloat/multilingual-e5-base'


def batched(items, size=32):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def main():
    rows = [json.loads(line) for line in CHUNKS_PATH.read_text(encoding='utf-8').splitlines() if line.strip()]
    model = SentenceTransformer(EMBED_MODEL_NAME)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={'description': 'MomCare maternal health RAG knowledge base'}
    )

    for batch in tqdm(list(batched(rows)), desc='Indexing ChromaDB'):
        ids = [x['id'] for x in batch]
        docs = [x['text'] for x in batch]
        metadatas = [x['metadata'] for x in batch]
        embeddings = model.encode([f'passage: {d}' for d in docs], normalize_embeddings=True).tolist()
        collection.upsert(ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings)

    print(f'Indexed {len(rows)} chunks into {CHROMA_DIR}')


if __name__ == '__main__':
    main()
