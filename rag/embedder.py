from sentence_transformers import SentenceTransformer

_model = None


def get_embedder():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_text(text: str) -> list[float]:
    embedder = get_embedder()
    embedding = embedder.encode(text, normalize_embeddings=True)
    return embedding.tolist()