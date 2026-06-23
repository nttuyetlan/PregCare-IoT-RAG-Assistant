import argparse
from pathlib import Path

import chromadb
from sklearn.feature_extraction.text import HashingVectorizer

BASE = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE / 'data' / 'chroma_db'
COLLECTION_NAME = 'momcare_knowledge_hashing'


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
    parser = argparse.ArgumentParser()
    parser.add_argument('question')
    parser.add_argument('--topic', default=None)
    parser.add_argument('--n', type=int, default=5)
    args = parser.parse_args()

    vectorizer = make_vectorizer()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    q_emb = vectorizer.transform([args.question]).toarray().astype('float32').tolist()
    where = {'topic': args.topic} if args.topic else None
    res = collection.query(query_embeddings=q_emb, n_results=args.n, where=where,
                           include=['documents', 'metadatas', 'distances'])
    for i, (doc, meta, dist) in enumerate(zip(res['documents'][0], res['metadatas'][0], res['distances'][0]), start=1):
        print('=' * 80)
        print(f'TOP {i} | distance={dist:.4f} | source={meta.get("source_id")} | topic={meta.get("topic")} | page={meta.get("pdf_page_start")}')
        print(doc[:1200])


if __name__ == '__main__':
    main()
