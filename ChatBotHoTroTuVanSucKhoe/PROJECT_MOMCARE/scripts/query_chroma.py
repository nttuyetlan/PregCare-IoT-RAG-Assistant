import argparse
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE / 'data' / 'chroma_db'
COLLECTION_NAME = 'momcare_knowledge'
EMBED_MODEL_NAME = 'intfloat/multilingual-e5-base'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('question')
    parser.add_argument('--topic', default=None)
    parser.add_argument('--n', type=int, default=5)
    args = parser.parse_args()

    model = SentenceTransformer(EMBED_MODEL_NAME)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)
    q_emb = model.encode([f'query: {args.question}'], normalize_embeddings=True).tolist()
    where = {'topic': args.topic} if args.topic else None
    res = collection.query(query_embeddings=q_emb, n_results=args.n, where=where,
                           include=['documents', 'metadatas', 'distances'])
    for i, (doc, meta, dist) in enumerate(zip(res['documents'][0], res['metadatas'][0], res['distances'][0]), start=1):
        print('=' * 80)
        print(f'TOP {i} | distance={dist:.4f} | source={meta.get("source_id")} | topic={meta.get("topic")} | page={meta.get("pdf_page_start")}')
        print(doc[:1200])


if __name__ == '__main__':
    main()
