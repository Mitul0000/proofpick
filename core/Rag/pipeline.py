import numpy as np
from config.settings import Setting
from core.Rag.chunking import chunking
from core.Rag.embedding import embeddings
from core.Rag.retrival import retrieval

settings = Setting()


def buildDocument(text:str):
    cleaned = (text or "").strip()
    if not cleaned:
        return {
            "chunks": [],
            "vectors": np.empty((0, 384), dtype=np.float32),
        }

    chunks = chunking(cleaned)
    if not chunks:
        return {
            "chunks": [],
            "vectors": np.empty((0, 384), dtype=np.float32),
        }

    vectors = embeddings(chunks)
    return {
        "chunks": chunks,
        "vectors": vectors,
    }


def getRelevantChunks(document, queryVector, top_k=None, min_score=None):
    if top_k is None:
        top_k = settings.top_k_per_document
    if min_score is None:
        min_score = settings.min_similarity

    chunks = document.get("chunks", [])
    vectors = document.get("vectors")
    if not chunks or vectors is None or len(vectors) == 0:
        return []

    ranked = retrieval(vectors, queryVector, top_k=top_k, min_score=min_score)
    results = []
    for item in ranked:
        idx = item["index"]
        results.append({
            "chunk_index": idx,
            "chunk_text": chunks[idx],
            "score": item["score"],
        })
    return results


def rankWithSourceCap(items:list[dict], sourceKey:str, scoreKey:str, top_k:int, maxPerSource:int)->list:
    sortedItems = sorted(items, key=lambda x: (x.get(scoreKey) if isinstance(x, dict) else getattr(x, scoreKey, 0.0)), reverse=True)
    sourceCounts = {}
    selected = []

    for item in sortedItems:
        source = item.get(sourceKey) if isinstance(item, dict) else getattr(item, sourceKey, "")
        count = sourceCounts.get(source, 0)
        if count >= maxPerSource:
            continue
        sourceCounts[source] = count + 1
        selected.append(item)
        if len(selected) >= top_k:
            break

    return selected
