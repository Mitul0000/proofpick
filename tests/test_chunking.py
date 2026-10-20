import unittest
from core.Rag.chunking import chunking


class TestChunking(unittest.TestCase):
    def test_empty_content(self):
        self.assertEqual(chunking(""), [])
        self.assertEqual(chunking(None), [])

    def test_unpunctuated_long_transcript(self):
        # Transcripts often have zero punctuation; ensures no crash and proper chunking
        raw_transcript = "hello world " * 400
        chunks = chunking(raw_transcript)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertGreater(len(c), 0)

    def test_punctuated_content(self):
        content = "First sentence. Second sentence with details! Third sentence with questions? Fourth sentence."
        chunks = chunking(content)
        self.assertGreater(len(chunks), 0)


if __name__ == "__main__":
    unittest.main()
