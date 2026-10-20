import logging
import threading
import numpy as np
from sentence_transformers import SentenceTransformer
from config.settings import Setting

settings = Setting()
logger = logging.getLogger("proofpick.embedding")

model = None
modelLock = threading.Lock()


def getModel():
    global model
    if model is None:
        with modelLock:
            if model is None:
                logger.info(f"Loading embedding model: {settings.embedding_model}...")
                model = SentenceTransformer(settings.embedding_model)
                logger.info("Embedding model loaded successfully.")
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
    return resultArray
