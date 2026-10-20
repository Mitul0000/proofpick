import unittest
from pipeline.report import _tokenOverlapMatch, buildReport
from models.intent import UserIntent, Budget
from models.evidence import EvidencePack, ResearchStats, SourceSummary
from models.search_result import GoogleSearchResult, YoutubeSearchResult


class TestReport(unittest.TestCase):
    def test_token_overlap_matching_models(self):
        # Pixel 8 should not match Pixel 7
        self.assertFalse(_tokenOverlapMatch("Google Pixel 8", "google pixel 7 is a solid smartphone"))
        # Pixel 8 should match Pixel 8 Pro or Pixel 8
        self.assertTrue(_tokenOverlapMatch("Google Pixel 8", "google pixel 8 offers great cameras"))

        # Galaxy S24 Ultra should not match Galaxy S24 base
        self.assertFalse(_tokenOverlapMatch("Galaxy S24 Ultra", "the galaxy s24 has a compact display"))
        self.assertTrue(_tokenOverlapMatch("Galaxy S24 Ultra", "samsung galaxy s24 ultra with s-pen"))

        # Poco X6 Pro vs Poco X6
        self.assertFalse(_tokenOverlapMatch("Poco X6 Pro", "poco x6 standard edition review"))
        self.assertTrue(_tokenOverlapMatch("Poco X6 Pro", "poco x6 pro benchmark testing"))

        # 5G should be optional
        self.assertTrue(_tokenOverlapMatch("Poco X6 5G", "reviewing the poco x6 in 2026"))

    def test_build_report_smoke(self):
        intent = UserIntent(
            raw_query="best laptop under 40000",
            product_category="laptop",
            budget=Budget(max=40000, currency="INR"),
            use_case="office work and freelancing",
        )

        sources = [
            SourceSummary(
                source_id="S1",
                platform="Google",
                url="https://example.com/laptop1",
                title="Top Budget Laptops 2026",
                author="TechReviewer",
                views=15000,
                chunks_used=1,
                matched_queries=["laptop under 40000"],
                best_score=0.88,
            )
        ]

        chunks = [
            GoogleSearchResult(
                url="https://example.com/laptop1",
                title="Top Budget Laptops 2026",
                description="Lenovo IdeaPad Slim 3 is best for office work.",
                match_query="laptop under 40000",
                chunk_query="office work",
                chunk_text="The Lenovo IdeaPad Slim 3 15-inch with Ryzen 5 offers great multitasking for freelancers.",
                chunk_index=0,
                chunk_match_score=0.88,
                domain="example.com",
            )
        ]

        pack = EvidencePack(
            master_query="Best laptop under 40000 INR for office work and freelancing",
            stats=ResearchStats(
                videos_found=0,
                videos_read=0,
                articles_found=1,
                articles_read=1,
                transcripts_from_captions=0,
                transcripts_from_whisper=0,
                chunks_before_master=1,
                chunks_final=1,
                query_stats=[],
            ),
            sources=sources,
            chunks=chunks,
        )

        # Mock askText by intercepting samplingContextVar
        from unittest.mock import MagicMock
        from core.llm import samplingContextVar

        fake_session = MagicMock()
        mock_result = MagicMock()
        mock_content = MagicMock()
        mock_content.text = (
            "# Recommendation Report\n\n"
            "## 1. Best Product\nLenovo IdeaPad Slim 3 is the top choice [S1].\n\n"
            "## 2. Alternatives\nNone.\n\n"
            "## 3. Comparison\nN/A\n\n"
            "## 4. Conflicts\nNone.\n\n"
            "## 5. Final Advice\nBuy during sale.\n\n"
            "PRODUCTS: Lenovo IdeaPad Slim 3"
        )
        mock_result.content = mock_content

        async def _fake_create_message(*args, **kwargs):
            return mock_result

        fake_session.create_message = _fake_create_message
        fake_ctx = MagicMock()
        fake_ctx.session = fake_session

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        samplingContextVar.set((fake_ctx, loop))

        try:
            report = buildReport(intent, pack)
            self.assertIn("Recommendation Report", report)
            self.assertIn("Lenovo IdeaPad Slim 3", report)
            self.assertIn("Research coverage", report)
            self.assertIn("## Sources", report)
        finally:
            samplingContextVar.set(None)
            loop.close()


if __name__ == "__main__":
    unittest.main()
