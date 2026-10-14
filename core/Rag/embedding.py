import numpy as np
from sentence_transformers import SentenceTransformer
from config.settings import Setting

settings = Setting()
model = None


def getModel():
    global model
    if model is None:
        model = SentenceTransformer(settings.embedding_model)
    return model


def embeddings(texts:str | list[str])->np.ndarray:
    m = getModel()
    inputTexts = [texts] if isinstance(texts, str) else texts
    if not inputTexts:
        return np.empty((0, 384), dtype=np.float32)

    result = m.encode(
        inputTexts,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=True,
    )
    resultArray = np.asarray(result, dtype=np.float32)
    if resultArray.ndim == 1:
        resultArray = np.expand_dims(resultArray, axis=0)
    return resultArray
