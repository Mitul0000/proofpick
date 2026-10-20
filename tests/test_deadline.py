import time
import unittest
from unittest.mock import MagicMock, patch
from models.search import SearchQuery, SourceSearch
from pipeline.research import runResearch


class TestDeadline(unittest.TestCase):
    @patch("pipeline.research.YoutubeSearch")
    @patch("pipeline.research.WebExtractor")
    def test_deadline_halts_research_immediately_when_expired(self, mock_web_cls, mock_yt_cls):
        # Setup mocks
        mock_yt = MagicMock()
        mock_yt.search_youtube.return_value = []
        mock_yt.get_transcript.return_value = []
        mock_yt_cls.return_value = mock_yt

        mock_web = MagicMock()
        mock_web.search_on_web.return_value = []
        mock_web.webcontent_filter.return_value = []
        mock_web.get_web_content.return_value = []
        mock_web_cls.return_value = mock_web

        plan = SearchQuery(
            google_search=SourceSearch(
                query=["laptop under 40000"],
                chunk_query=["office work"],
            ),
            youtube_search=SourceSearch(
                query=["laptop under 40000"],
                chunk_query=["office work"],
            ),
            master_query="Best laptop under 40000",
        )

        # Deadline already expired
        expired_deadline = time.monotonic() - 10.0
        evidence = runResearch(plan, deadline=expired_deadline)

        # When expired, branches should skip and return empty/partial results immediately
        self.assertEqual(evidence.stats.videos_found, 0)
        self.assertEqual(evidence.stats.articles_found, 0)
        self.assertEqual(len(evidence.chunks), 0)

    @patch("pipeline.research.YoutubeSearch")
    @patch("pipeline.research.WebExtractor")
    def test_deadline_partial_results_when_fetch_sleeps_past_deadline(self, mock_web_cls, mock_yt_cls):
        # YouTube returns fast results
        mock_yt = MagicMock()
        mock_yt.search_youtube.return_value = [
            {"link": "https://youtube.com/watch?v=fast1", "search_query": "laptop under 40000", "title": "Fast Video", "channel_name": "Reviewer"}
        ]
        # get_transcript returns immediate result for fast video
        def fake_yt_transcripts(videos, deadline=None):
            for v in videos:
                v["transcript"] = "Performance and battery life for office work, multitasking, and freelancing on Lenovo IdeaPad laptop under 40000."
                v["transcript_source"] = "youtube_captions"
            return videos
        mock_yt.get_transcript.side_effect = fake_yt_transcripts
        mock_yt_cls.return_value = mock_yt

        # Web branch simulates a slow fetch that sleeps past the deadline
        mock_web = MagicMock()
        mock_web.search_on_web.return_value = [{"query": "laptop under 40000", "result": [{"href": "https://slow.com"}]}]
        mock_web.webcontent_filter.return_value = [{"query": "laptop under 40000", "result": [{"href": "https://slow.com"}]}]
        def fake_get_web_content(search_results, deadline=None):
            # Sleep past the deadline
            if deadline:
                time.sleep(max(0.2, (deadline - time.monotonic()) + 0.3))
            return search_results
        mock_web.get_web_content.side_effect = fake_get_web_content
        mock_web_cls.return_value = mock_web

        plan = SearchQuery(
            google_search=SourceSearch(
                query=["laptop under 40000"],
                chunk_query=["office work multitasking and freelancing on Lenovo IdeaPad laptop under 40000"],
            ),
            youtube_search=SourceSearch(
                query=["laptop under 40000"],
                chunk_query=["office work multitasking and freelancing on Lenovo IdeaPad laptop under 40000"],
            ),
            master_query="Best laptop under 40000",
        )

        # Warm up embeddings model before starting the clock so model load does not eat the test deadline
        from core.Rag.embedding import embeddings
        embeddings(["warm up model"])

        # Set deadline of 0.8 seconds; web branch will sleep past it
        short_deadline = time.monotonic() + 0.8
        evidence = runResearch(plan, deadline=short_deadline)

        # Finished items from YouTube branch MUST still be returned in partial results
        self.assertGreaterEqual(evidence.stats.videos_read, 1)
        self.assertGreaterEqual(len(evidence.chunks), 1)
        self.assertEqual(evidence.chunks[0].url, "https://youtube.com/watch?v=fast1")


if __name__ == "__main__":
    unittest.main()
