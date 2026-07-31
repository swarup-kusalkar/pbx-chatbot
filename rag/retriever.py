from rag.vector_store import get_collection
from rag.embedder import embed_text

RELEVANCE_THRESHOLD = 0.8


def retrieve_kb_chunks(query: str, n_results: int = 3) -> list[dict]:
    collection = get_collection()
    query_embedding = embed_text(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        if dist < RELEVANCE_THRESHOLD:
            chunks.append({
                "content": doc,
                "topic": meta["topic"],
                "section": meta["section"],
                "question": meta["question"],
                "distance": dist
            })

    return chunks