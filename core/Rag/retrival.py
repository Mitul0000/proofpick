
import numpy as np
from numpy.linalg import norm


def cosineSimilarity(vectorA, vectorB):
    A = np.asarray(vectorA)
    B = np.asarray(vectorB)
    denominator = norm(A) * norm(B)
    if denominator == 0:
        return 0.0

    return float(np.dot(A, B) / denominator)

def retrieval(chunksVectors: list, queryVector, top_k=5):
    vectorScoreList = []

    for chunkVector in chunksVectors:
        score = cosineSimilarity(chunkVector, queryVector)
        vectorScoreList.append({
            "vector": chunkVector,
            "score": score
        })

    vectorScoreList.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return vectorScoreList[:top_k]
