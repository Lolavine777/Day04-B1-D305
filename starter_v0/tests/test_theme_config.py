from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "starter_v0"


class ThemeConfigTests(unittest.TestCase):
    def test_root_and_local_streamlit_themes_match(self) -> None:
        root_path = PROJECT_ROOT / ".streamlit/config.toml"
        local_path = APP_ROOT / ".streamlit/config.toml"
        self.assertTrue(root_path.is_file())
        self.assertTrue(local_path.is_file())
        root_theme = tomllib.loads(
            root_path.read_text(encoding="utf-8")
        )
        local_theme = tomllib.loads(
            local_path.read_text(encoding="utf-8")
        )

        self.assertEqual(root_theme, local_theme)

    def test_theme_uses_light_native_surfaces(self) -> None:
        local_path = APP_ROOT / ".streamlit/config.toml"
        self.assertTrue(local_path.is_file())
        config = tomllib.loads(
            local_path.read_text(encoding="utf-8")
        )
        theme = config["theme"]

        self.assertEqual(theme["base"], "light")
        self.assertEqual(theme["backgroundColor"], "#F7F9F8")
        self.assertEqual(theme["secondaryBackgroundColor"], "#EEF2F1")
        self.assertEqual(theme["codeBackgroundColor"], "#F1F5F4")
        self.assertEqual(theme["textColor"], "#17211F")
        self.assertTrue(theme["showWidgetBorder"])


if __name__ == "__main__":
    unittest.main()
