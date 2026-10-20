import asyncio
import json
import unittest
from unittest.mock import MagicMock
from models.intent import UserIntent
from models.search import SearchQuery, SourceSearch
from core.llm import samplingContextVar, _extractJsonBlock


class FakeSession:
    def __init__(self):
        pass

    async def create_message(self, messages, system_prompt, max_tokens):
        mock_result = MagicMock()
        mock_content = MagicMock()

        # Check prompt to provide appropriate mock responses
        user_text = messages[0].content.text
        if "User Intent JSON" in user_text:
            data = {
                "google_search": {
                    "query": ["poco x6 review", "poco x6 heating", "poco x6 vs iqoo z9"],
                    "chunk_query": ["battery and gaming", "thermals", "comparison"],
                },
                "youtube_search": {
                    "query": ["poco x6 gaming test", "poco x6 honest review", "poco x6 long term"],
                    "chunk_query": ["gaming fps", "pros and cons", "durability"],
                },
                "master_query": "Best gaming phone under 20000 INR with good battery and thermals.",
            }
            mock_content.text = json.dumps(data)
        elif "product_category" in user_text:
            data = {
                "raw_query": "gaming phone under 20000 rupees",
                "product_category": "smartphone",
                "budget": {"min": None, "max": 20000, "currency": "INR"},
                "use_case": "gaming",
                "priority_attributes": {"performance": 0.9, "battery": 0.8},
                "dealbreakers": None,
                "brand_preference": None,
                "free_text_notes": None,
                "ai_inferred_attributes": None,
                "clarification": {"is_ambiguous": False, "missing_info": []},
            }
            mock_content.text = json.dumps(data)
        else:
            mock_content.text = (
                "# Product Recommendation Report\n\n## 1. Best Product for Your Intent\nPoco X6 5G is best [S1].\n\n"
                "## 2. Alternatives\nAlternative 1 is great [S2].\n\n"
                "## 3. Comparison Table\n| Model | Price |\n|---|---|\n| Poco X6 | 19999 |\n\n"
                "## 4. Conflicts & Uncertainty\nMinor heating reported.\n\n"
                "## 5. Final Advice\nCheck discounts.\n\n"
                "PRODUCTS: Poco X6 5G | iQOO Z9 | Realme Narzo 70"
            )

        mock_result.content = mock_content
        return mock_result


class TestFakeSamplingSmoke(unittest.TestCase):
    def test_json_extraction(self):
        raw = "```json\n{\"test\": 123}\n```"
        self.assertEqual(_extractJsonBlock(raw), "{\"test\": 123}")

        raw_embedded = "Here is the response: {\"test\": 456} Hope this helps!"
        self.assertEqual(_extractJsonBlock(raw_embedded), "{\"test\": 456}")

    def test_sampling_smoke_intent(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        fake_ctx = MagicMock()
        fake_ctx.session = FakeSession()

        samplingContextVar.set((fake_ctx, loop))
        try:
            from pipeline.planner import analyzeIntent, buildSearchPlan

            intent = analyzeIntent("gaming phone under 20000 rupees")
            self.assertEqual(intent.product_category, "smartphone")
            self.assertEqual(intent.budget.max, 20000)

            plan = buildSearchPlan(intent)
            self.assertGreaterEqual(len(plan.google_search.query), 1)
            self.assertGreaterEqual(len(plan.youtube_search.query), 1)
        finally:
            samplingContextVar.set(None)
            loop.close()


if __name__ == "__main__":
    unittest.main()
