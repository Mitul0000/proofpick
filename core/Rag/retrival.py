import numpy as np
from numpy.linalg import norm


def cosineSimilarity(vectorA, vectorB):
    A = np.asarray(vectorA)
    B = np.asarray(vectorB)
    denominator = norm(A) * norm(B)
    if denominator == 0:
        return 0.0

    return float(np.dot(A, B) / denominator)


def retrieval(chunksVectors, queryVector, top_k=5, min_score=0.0):
    chunks = np.asarray(chunksVectors)
    if chunks.ndim != 2 or chunks.shape[0] == 0:
        return []

    q = np.asarray(queryVector).reshape(-1)
    qNorm = norm(q)
    if qNorm == 0:
        return []

    chunksNorms = norm(chunks, axis=1)
    # avoid divide by zero for any zero vectors
    validNorms = np.where(chunksNorms == 0, 1.0, chunksNorms)
    scores = np.dot(chunks, q) / (validNorms * qNorm)
    scores = np.where(chunksNorms == 0, 0.0, scores)

    rankedIndices = np.argsort(-scores)
    vectorScoreList = []
    for idx in rankedIndices:
        score = float(scores[idx])
        if score < min_score:
            break
        vectorScoreList.append({
            "index": int(idx),
            "score": score,
        })
        if len(vectorScoreList) >= top_k:
            break

    return vectorScoreList
