import sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from config.settings import Setting
from core.Rag.embedding import embeddings
from core.Rag.pipeline import buildDocument, getRelevantChunks, rankWithSourceCap
from models.evidence import EvidencePack, QueryStats, ResearchStats, SourceSummary
from models.search import SearchQuery, SourceSearch
from models.search_result import GoogleSearchResult, YoutubeSearchResult
from services.web_service import WebExtractor
from services.youtube_service import YoutubeSearch
from numpy.linalg import norm

settings = Setting()


def youtubeBranch(source:SourceSearch):
    yt = YoutubeSearch(source.query)
    rawVideos = yt.search_youtube()
    videosWithTranscript = yt.get_transcript(rawVideos)

    uniqueVideos = {}
    captionsCount = 0
    whisperCount = 0

    for v in videosWithTranscript:
        url = v.get("link")
        if not url:
            continue
        if url not in uniqueVideos:
            uniqueVideos[url] = v
        src = v.get("transcript_source")
        if src == "youtube_captions":
            captionsCount += 1
        elif src == "whisper":
            whisperCount += 1

    documents = {}
    for url, video in uniqueVideos.items():
        transcript = (video.get("transcript") or "").strip()
        if not transcript:
            continue
        documents[url] = buildDocument(transcript)

    results = []
    statsList = []

    for query, chunkQuery in source.pairs():
        videosForQuery = [v for v in videosWithTranscript if v.get("search_query") == query]
        docsRead = 0
        chunksKept = 0

        queryVector = embeddings(chunkQuery)[0]

        for video in videosForQuery:
            url = video.get("link")
            if not url or url not in documents:
                continue

            doc = documents[url]
            docsRead += 1

            relevant = getRelevantChunks(doc, queryVector)
            for rel in relevant:
                chunksKept += 1
                results.append(YoutubeSearchResult(
                    url=url,
                    channel_name=video.get("channel_name") or "",
                    channel_url=video.get("channel_link") or "",
                    title=video.get("title") or "",
                    description=video.get("description") or "",
                    match_query=query,
                    chunk_query=chunkQuery,
                    chunk_text=rel["chunk_text"],
                    chunk_index=rel["chunk_index"],
                    chunk_match_score=rel["score"],
                    view_count=video.get("views") or 0,
                    duration=video.get("duration") or 0,
                    transcript_source=video.get("transcript_source") or "",
                ))

        statsList.append(QueryStats(
            platform="Youtube",
            query=query,
            chunk_query=chunkQuery,
            documents_found=len(videosForQuery),
            documents_read=docsRead,
            chunks_kept=chunksKept,
        ))

    meta = {
        "videos_found": len(uniqueVideos),
        "videos_read": len(documents),
        "transcripts_from_captions": captionsCount,
        "transcripts_from_whisper": whisperCount,
    }
    return results, statsList, meta


def webBranch(source:SourceSearch):
    web = WebExtractor(source.query)
    rawResults = web.search_on_web()
    filteredResults = web.webcontent_filter(rawResults)
    contentResults = web.get_web_content(filteredResults)

    uniquePages = {}
    articlesFound = set()

    for queryGroup in contentResults:
        for item in queryGroup.get("result", []):
            url = item.get("href")
            if url:
                articlesFound.add(url)
                if url not in uniquePages and item.get("web content"):
                    uniquePages[url] = item

    documents = {}
    for url, page in uniquePages.items():
        content = (page.get("web content") or "").strip()
        if not content:
            continue
        documents[url] = buildDocument(content)

    results = []
    statsList = []

    for query, chunkQuery in source.pairs():
        matchingGroup = next((g for g in contentResults if g.get("query") == query), None)
        pagesForQuery = matchingGroup.get("result", []) if matchingGroup else []
        docsRead = 0
        chunksKept = 0

        queryVector = embeddings(chunkQuery)[0]

        for page in pagesForQuery:
            url = page.get("href")
            if not url or url not in documents:
                continue

            doc = documents[url]
            docsRead += 1

            relevant = getRelevantChunks(doc, queryVector)
            for rel in relevant:
                chunksKept += 1
                results.append(GoogleSearchResult(
                    url=url,
                    title=page.get("title") or "",
                    description=page.get("body") or "",
                    match_query=query,
                    chunk_query=chunkQuery,
                    chunk_text=rel["chunk_text"],
                    chunk_index=rel["chunk_index"],
                    chunk_match_score=rel["score"],
                    domain=page.get("domain") or "",
                ))

        statsList.append(QueryStats(
            platform="Google",
            query=query,
            chunk_query=chunkQuery,
            documents_found=len(pagesForQuery),
            documents_read=docsRead,
            chunks_kept=chunksKept,
        ))

    meta = {
        "articles_found": len(articlesFound),
        "articles_read": len(documents),
        "documents": documents,
    }
    return results, statsList, meta


def runResearch(plan:SearchQuery)->EvidencePack:
    with ThreadPoolExecutor(max_workers=2) as executor:
        futureYt = executor.submit(youtubeBranch, plan.youtube_search)
        futureWeb = executor.submit(webBranch, plan.google_search)

        ytResults, ytStats, ytMeta = futureYt.result()
        webResults, webStats, webMeta = futureWeb.result()

    mergedMap = {}
    for item in ytResults + webResults:
        key = (item.url, item.chunk_index)
        if key not in mergedMap or item.chunk_match_score > mergedMap[key].chunk_match_score:
            mergedMap[key] = item

    pool = list(mergedMap.values())


    if pool:
        masterVector = embeddings(plan.master_query)[0]
        chunkTexts = [item.chunk_text for item in pool]
        chunkVectors = embeddings(chunkTexts)
        mNorm = norm(masterVector)
        cVNorms = norm(chunkVectors, axis=1)
        validNorms = np.where(cVNorms == 0, 1.0, cVNorms)
        scores = np.dot(chunkVectors, masterVector) / (validNorms * (mNorm if mNorm != 0 else 1.0))
        scores = np.where(cVNorms == 0, 0.0, scores)
        validPool = []
        for i, item in enumerate(pool):
            s = float(scores[i])
            item.master_match_score = s
            if s >= settings.min_similarity:
                validPool.append(item)

        finalChunks = rankWithSourceCap(
            items=validPool,
            sourceKey="url",
            scoreKey="master_match_score",
            top_k=settings.top_k_master,
            maxPerSource=settings.max_chunks_per_source_in_master,
        )
    else:
        print("Continues to work without the final chunks")
        finalChunks = []

    sourceMap = {}
    for chunk in finalChunks:
        url = chunk.url
        if url not in sourceMap:
            author = getattr(chunk, "channel_name", "") or getattr(chunk, "domain", "")
            views = getattr(chunk, "view_count", 0)
            sourceMap[url] = {
                "platform": chunk.platform,
                "url": url,
                "title": chunk.title,
                "author": author,
                "views": views,
                "chunks_used": 0,
                "matched_queries": set(),
                "best_score": chunk.master_match_score,
            }

        sourceMap[url]["chunks_used"] += 1
        sourceMap[url]["matched_queries"].add(chunk.match_query)
        if chunk.master_match_score > sourceMap[url]["best_score"]:
            sourceMap[url]["best_score"] = chunk.master_match_score

    sortedSources = sorted(sourceMap.values(), key=lambda s: s["best_score"], reverse=True)
    sourcesList = []
    for i, s in enumerate(sortedSources, start=1):
        sourcesList.append(SourceSummary(
            source_id=f"S{i}",
            platform=s["platform"],
            url=s["url"],
            title=s["title"],
            author=s["author"],
            views=s["views"],
            chunks_used=s["chunks_used"],
            matched_queries=list(s["matched_queries"]),
            best_score=s["best_score"],
        ))

    stats = ResearchStats(
        videos_found=ytMeta.get("videos_found", 0),
        videos_read=ytMeta.get("videos_read", 0),
        articles_found=webMeta.get("articles_found", 0),
        articles_read=webMeta.get("articles_read", 0),
        transcripts_from_captions=ytMeta.get("transcripts_from_captions", 0),
        transcripts_from_whisper=ytMeta.get("transcripts_from_whisper", 0),
        chunks_before_master=len(pool),
        chunks_final=len(finalChunks),
        query_stats=ytStats + webStats,
    )

    return EvidencePack(
        master_query=plan.master_query,
        stats=stats,
        sources=sourcesList,
        chunks=finalChunks,
        pool=pool,
    )
