from typing import List
import chromadb
from chromadb.config import Settings


def create_client():
    # simple persistent chroma client in local directory
    client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma_db"))
    from typing import List, Optional
    import os
    import sqlite3
    import json
    import numpy as np
    from sentence_transformers import SentenceTransformer


    BASE_DIR = os.path.dirname(__file__)
    DB_PATH = os.path.join(BASE_DIR, "data.db")


    def _get_conn():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn


    def create_client():
        # For compatibility with previous code, return True after ensuring table exists
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                collection TEXT,
                metadata TEXT,
                document TEXT,
                embedding TEXT
            )
            """
        )
        conn.commit()
        conn.close()
        return True


    def get_or_create_collection(client, name: str):
        # collections are logical; return the name
        return name


    def add_documents(collection: str, ids: List[str], metadatas: List[dict], documents: List[str], embeddings: Optional[List[List[float]]] = None):
        conn = _get_conn()
        cur = conn.cursor()
        for i, _id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            doc = documents[i] if i < len(documents) else ""
            emb = embeddings[i] if embeddings is not None and i < len(embeddings) else None
            emb_json = json.dumps(emb) if emb is not None else None
            cur.execute(
                "REPLACE INTO embeddings (id, collection, metadata, document, embedding) VALUES (?, ?, ?, ?, ?)",
                (_id, collection, json.dumps(meta), doc, emb_json),
            )
        conn.commit()
        conn.close()


    def _load_embeddings(collection: str):
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, metadata, document, embedding FROM embeddings WHERE collection = ?", (collection,))
        rows = cur.fetchall()
        conn.close()
        items = []
        for r in rows:
            emb = json.loads(r[3]) if r[3] else None
            items.append({"id": r[0], "metadata": json.loads(r[1]) if r[1] else {}, "document": r[2], "embedding": emb})
        return items


    def query(collection: str, query_text: str, n_results: int = 5):
        # embed the query
        model = SentenceTransformer("all-MiniLM-L6-v2")
        q_emb = model.encode([query_text])[0]

        items = _load_embeddings(collection)
        results = []
        embeddings = []
        ids = []
        metas = []
        docs = []
        for it in items:
            if it["embedding"] is None:
                continue
            embeddings.append(np.array(it["embedding"], dtype=float))
            ids.append(it["id"])
            metas.append(it["metadata"])
            docs.append(it["document"])

        if not embeddings:
            return {"ids": [], "metadatas": [], "documents": []}

        mat = np.vstack(embeddings)
        q = np.array(q_emb, dtype=float)
        # cosine similarity
        mat_norm = mat / np.linalg.norm(mat, axis=1, keepdims=True)
        q_norm = q / np.linalg.norm(q)
        sims = mat_norm.dot(q_norm)
        top_idx = np.argsort(-sims)[:n_results]

        out_ids = [ids[i] for i in top_idx]
        out_metas = [metas[i] for i in top_idx]
        out_docs = [docs[i] for i in top_idx]
        return {"ids": out_ids, "metadatas": out_metas, "documents": out_docs}
