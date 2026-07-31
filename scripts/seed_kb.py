#!/usr/bin/env python3
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, SessionLocal
from models import KnowledgeBase
from rag.vector_store import upsert_kb_chunks, get_collection_count, clear_collection

ARTICLES_DIR = os.path.join(os.path.dirname(__file__), "articles")
CHUNK_SIZE = 600


def create_tables():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


def extract_sections(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")
    topic = lines[0].replace("# ", "").strip()

    sections = []
    current_title = None
    current_content = []

    for line in lines[1:]:
        if line.startswith("## "):
            if current_title is not None:
                section_text = "\n".join(current_content).strip()
                if section_text:
                    sections.append({
                        "title": current_title,
                        "content": section_text
                    })
            current_title = line.replace("## ", "").strip()
            current_content = []
        else:
            current_content.append(line)

    if current_title is not None:
        section_text = "\n".join(current_content).strip()
        if section_text:
            sections.append({
                "title": current_title,
                "content": section_text
            })

    return topic, sections


def chunk_section(section, chunk_size=CHUNK_SIZE):
    words = section["content"].split()
    chunks = []
    title = section["title"]

    if len(words) <= chunk_size:
        return [{
            "chunk_text": f"## {title}\n\n{section['content']}",
            "question": f"{title}"
        }]

    paragraphs = section["content"].split("\n\n")
    current_chunk = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > chunk_size and current_chunk:
            chunks.append({
                "chunk_text": f"## {title}\n\n" + "\n\n".join(current_chunk),
                "question": f"{title}"
            })
            current_chunk = []
            current_words = 0
        current_chunk.append(para)
        current_words += para_words

    if current_chunk:
        chunks.append({
            "chunk_text": f"## {title}\n\n" + "\n\n".join(current_chunk),
            "question": f"{title}"
        })

    return chunks


def seed_articles():
    md_files = [f for f in os.listdir(ARTICLES_DIR) if f.endswith(".md")]
    md_files.sort()

    print(f"Found {len(md_files)} article files.")

    db = SessionLocal()
    try:
        for filename in md_files:
            filepath = os.path.join(ARTICLES_DIR, filename)
            topic, sections = extract_sections(filepath)

            existing = db.query(KnowledgeBase).filter(
                KnowledgeBase.topic == topic
            ).first()

            if existing:
                print(f"  [{topic}] already in DB, updating ChromaDB only...")
                existing.answer = f"This article contains {len(sections)} sections."
                db.commit()
            else:
                kb_record = KnowledgeBase(
                    topic=topic,
                    question=f"PBX and Contact Center information about {topic}",
                    answer=f"Comprehensive article with {len(sections)} sections covering {topic}."
                )
                db.add(kb_record)
                db.commit()

            print(f"  [{topic}] -> {len(sections)} sections")

            all_chunks = []
            for idx, section in enumerate(sections):
                section_chunks = chunk_section(section)
                for chunk_idx, chunk in enumerate(section_chunks):
                    all_chunks.append({
                        "chunk_text": chunk["chunk_text"],
                        "question": chunk["question"],
                        "topic": topic,
                        "section": section["title"],
                        "chunk_index": idx * 100 + chunk_idx,
                        "article": filename
                    })

            upsert_kb_chunks(topic, all_chunks)
            print(f"    -> {len(all_chunks)} chunks stored in ChromaDB")

    finally:
        db.close()


def verify():
    db = SessionLocal()
    try:
        kb_count = db.query(KnowledgeBase).count()
        chroma_count = get_collection_count()
        print(f"\nVerification:")
        print(f"  MySQL KB articles: {kb_count}")
        print(f"  ChromaDB chunks: {chroma_count}")
    finally:
        db.close()


def test_retrieval():
    print("\nTesting semantic retrieval...")
    from rag.retriever import retrieve_kb_chunks

    test_queries = [
        "how does the phone tree work?",
        "what is a SIP trunk connection?",
        "how do I record calls in the contact center?",
        "what is DTMF and how does it work?"
    ]

    for q in test_queries:
        chunks = retrieve_kb_chunks(q, n_results=3)
        print(f"\n  Query: '{q}'")
        if chunks:
            for c in chunks:
                print(f"    -> [{c['topic']}] {c['section']} (distance: {c['distance']:.3f})")
        else:
            print(f"    -> No relevant chunks found (off-topic)")


if __name__ == "__main__":
    print("=" * 50)
    print("PBX Chatbot KB Seeder (with chunking)")
    print("=" * 50)

    create_tables()
    print()
    seed_articles()
    verify()
    test_retrieval()

    print("\nSeeding complete!")