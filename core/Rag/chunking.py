import re
from config.settings import Setting

settings = Setting()


def _splitLong(s:str, maxChar:int)->list[str]:
    parts, cur = [], ""
    for w in s.split(" "):
        if not w:
            continue
        if cur and len(cur) + len(w) + 1 > maxChar:
            parts.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        parts.append(cur)
    return parts


def chunking(content:str)->list[str]:
    chunks = []
    max_char = settings.max_chunk_size * settings.chars_per_token

    # replace consecutive whitespace
    content = re.sub(r"\s+", " ", content or "").strip()
    if not content:
        return chunks

    rawSentences = re.split(r"(?<=[.!?])\s+", content)
    sentences = [
        p for s in rawSentences
        for p in (_splitLong(s, max_char) if len(s) > max_char else [s])
        if p.strip()
    ]

    currentChunk = ""
    for sentence in sentences:
        if currentChunk and len(currentChunk) + len(sentence) + 1 > max_char:
            chunks.append(currentChunk.strip())
            overlapWords = currentChunk.split(" ")[-settings.overlap_words:]
            overlapText = " ".join(overlapWords)
            currentChunk = f"{overlapText} {sentence}"
        else:
            currentChunk = f"{currentChunk} {sentence}".strip()

    if currentChunk.strip():
        chunks.append(currentChunk.strip())

    return chunks