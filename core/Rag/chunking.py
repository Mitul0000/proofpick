

# This file takes the content and it first clean the content by replacing if there is any two more whitespace charecter together with one whitespace char.
# Then it spits the content to list of sentences and then chunked the content as per the settings. This function also looks after the overlapping of the chunking 
# so that the context is maintained.

import re
from config.settings import Setting

settings = Setting()


def chunking(content:str):
    chunks = []
    max_char = settings.max_chunk_size * settings.chars_per_token

    # This replaces the consecutive multiple whitespaces. Clean text is easy to proceess .
    content = re.sub(r"\s+", " ", content or "").strip()

    if not content:
        return chunks

    sentences = re.split(r"(?<=[.!?])\s+", content)
    
    for sentence in sentences:
        if currentChunk and len(currentChunk) + len(sentence) + 1 > max_char:
            chunks.append(currentChunk.strip())
            overlapText = " ".join(currentChunk.split(" ")[-settings.overlap_words:])
            currentChunk = f"{overlapText} {sentence}"
        else:
            currentChunk = f"{currentChunk} {sentence}".strip()

    if currentChunk.strip():
        chunks.append(currentChunk.strip())

    return chunks