
# from config.settings import Setting
# settings = Setting()

# def chunking(content: str) -> list[str]:
#     chunks = []
#     max_char = settings.max_chunk_size * 4
#     overlap_words = settings.overlap_words
#     start = 0
#     while start < len(content):
#         end = start + max_char
#         chunk = content[start:end].strip()
#         chunks.append(chunk)

#         if end == len(content):
#             break

#         words = list(__import__("re").finditer(r"\S+", chunk))

#         if len(words) > overlap_words:
#             overlap_start = words[-overlap_words].start()
#             start = start + overlap_start
#         else:
#             start = end

#     return chunks


import re
from config.settings import Setting

settings = Setting()


def splitLongText(text:str, max_char:int):
    # youtube captions have almost no punctuation so one "sentence" can be huge
    pieces = []
    current = ""

    for word in text.split(" "):
        if current and len(current) + len(word) + 1 > max_char:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()

    if current:
        pieces.append(current)

    return pieces


def chunking(content:str):
    chunks = []
    max_char = settings.max_chunk_size * settings.chars_per_token

    content = re.sub(r"\s+", " ", content or "").strip()
    if not content:
        return chunks

    sentences = re.split(r"(?<=[.!?])\s+", content)

    # every piece is at most half of the chunk so that piece + overlap always fits
    pieces = []
    for sentence in sentences:
        if len(sentence) > max_char // 2:
            pieces.extend(splitLongText(sentence, max_char // 2))
        else:
            pieces.append(sentence)

    currentChunk = ""
    for piece in pieces:
        if currentChunk and len(currentChunk) + len(piece) + 1 > max_char:
            chunks.append(currentChunk.strip())

            # last few words of the old chunk are repeated at the start of the new one
            overlapText = " ".join(currentChunk.split(" ")[-settings.overlap_words:])
            currentChunk = f"{overlapText} {piece}"
        else:
            currentChunk = f"{currentChunk} {piece}".strip()

    if currentChunk.strip():
        chunks.append(currentChunk.strip())

    return chunks