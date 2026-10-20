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


if __name__ == "__main__":
    unittest.main()
