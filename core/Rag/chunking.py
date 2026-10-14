
import math
from config.settings import Setting

settings = Setting()

def chunking(content:str):
    chunks = []
    max_char = settings.max_chunk_size*4

    for start in range(0,len(content),max_char):

        startingPoint = start - 10
        if startingPoint < 0:
            startingPoint = 0
        chunk = content[startingPoint:start + max_char]
        chunks.append(chunk.strip())

    return chunks

