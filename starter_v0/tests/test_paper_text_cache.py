from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools._shared import ROOT
from tools.paper_text.tool import _arxiv_cache_dir


class PaperTextCacheTests(unittest.TestCase):
    def test_custom_cache_directory_has_priority(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ARXIV_CACHE_DIR": "D:/cache/arxiv",
                "VERCEL": "1",
            },
            clear=True,
        ):
            self.assertEqual(
                _arxiv_cache_dir(),
                Path("D:/cache/arxiv"),
            )

    def test_vercel_uses_writable_temp_directory(self) -> None:
        with patch.dict(
            os.environ,
            {"VERCEL": "1"},
            clear=True,
        ), patch(
            "tools.paper_text.tool.tempfile.gettempdir",
            return_value="D:/tmp",
        ):
            self.assertEqual(
                _arxiv_cache_dir(),
                Path("D:/tmp/research-agent-arxiv"),
            )

    def test_local_fallback_preserves_existing_directory(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                _arxiv_cache_dir(),
                ROOT / "arxiv_papers",
            )


if __name__ == "__main__":
    unittest.main()
