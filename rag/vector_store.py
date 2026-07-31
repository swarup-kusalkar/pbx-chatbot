import chromadb
from chromadb.config import Settings
from config import config
from rag.embedder import embed_text

_chroma_client = None
_collection = None

COLLECTION_NAME = "pbx_knowledge_base"


def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path=config.CHROMA_PERSIST_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client


def get_collection():
    global _collection
    if _collection is None:
        client = get_chroma_client()
        try:
            _collection = client.get_collection(name=COLLECTION_NAME)
        except Exception:
            _collection = client.create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "PBX Knowledge Base chunks"}
            )
    return _collection


def upsert_kb_chunks(topic: str, chunks: list[dict]):
    collection = get_collection()

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for chunk in chunks:
        chunk_id = f"{topic.lower().replace(' ', '_')}_{chunk['chunk_index']}"
        ids.append(chunk_id)
        documents.append(chunk["chunk_text"])
        embeddings.append(embed_text(chunk["chunk_text"]))
        metadatas.append({
            "topic": chunk["topic"],
            "section": chunk["section"],
            "question": chunk["question"],
            "article": chunk["article"],
            "chunk_index": chunk["chunk_index"]
        })

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )


def upsert_kb_article(mysql_id: int, topic: str, question: str, answer: str):
    collection = get_collection()
    chroma_id = f"kb_{mysql_id}"

    collection.upsert(
        ids=[chroma_id],
        documents=[answer],
        embeddings=[embed_text(answer)],
        metadatas=[{
            "mysql_id": mysql_id,
            "topic": topic,
            "question": question
        }]
    )
    return chroma_id


def delete_kb_article(chroma_id: str):
    collection = get_collection()
    collection.delete(ids=[chroma_id])


def clear_collection():
    collection = get_collection()
    try:
        collection.delete(where={})
    except Exception:
        pass


def get_collection_count() -> int:
    collection = get_collection()
    return collection.count()