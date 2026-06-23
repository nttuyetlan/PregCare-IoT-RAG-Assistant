import json
from pathlib import Path

import chromadb
from sklearn.feature_extraction.text import HashingVectorizer
from tqdm import tqdm

BASE = Path(__file__).resolve().parents[1]
CHUNKS_PATH = BASE / 'data' / 'extracted' / 'chunks_for_chroma.jsonl'
CHROMA_DIR = BASE / 'data' / 'chroma_db'
COLLECTION_NAME = 'momcare_knowledge_hashing'


def batched(items, size=64):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def make_vectorizer():
    return HashingVectorizer(
        n_features=768,
        analyzer='word',
        ngram_range=(1, 2),
        lowercase=True,
        norm='l2',
        alternate_sign=False,
    )


def main():
    rows = [json.loads(line) for line in CHUNKS_PATH.read_text(encoding='utf-8').splitlines() if line.strip()]
    vectorizer = make_vectorizer()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            'description': 'MomCare RAG knowledge base, offline HashingVectorizer embeddings',
            'embedding_type': 'sklearn_hashing_vectorizer_768_word_1_2gram',
        },
    )

    for batch in tqdm(list(batched(rows)), desc='Indexing ChromaDB hashing'):
        ids = [x['id'] for x in batch]
        docs = [x['text'] for x in batch]
        metadatas = [x['metadata'] for x in batch]
        embeddings = vectorizer.transform(docs).toarray().astype('float32').tolist()
        collection.upsert(ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings)
    print(f'Indexed {len(rows)} chunks into {CHROMA_DIR}, collection={COLLECTION_NAME}')


if __name__ == '__main__':
    main()
