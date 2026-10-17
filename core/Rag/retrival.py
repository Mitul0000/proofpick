# It takes chunksvector and perform cosine similerity search. Then it sorts the results and extracts the sorted index. And finally returns topK lists of dicts
# containg indexs and the scores


import numpy as np
from numpy.linalg import norm


def retrieval(chunksVectors, queryVector, top_k=5, min_score=0.0):
    chunks = np.asarray(chunksVectors)
    if chunks.ndim != 2 or chunks.shape[0] == 0:
        return []

    q = np.asarray(queryVector).reshape(-1)
    qNorm = norm(q)
    if qNorm == 0:
        return []

    chunksNorms = norm(chunks, axis=1)
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
