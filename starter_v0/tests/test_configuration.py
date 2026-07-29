from __future__ import annotations

import unittest

from configuration import (
    configured_secret_names,
    provider_secret_name,
    resolve_secrets,
)


class ConfigurationTests(unittest.TestCase):
    def test_root_level_streamlit_secret_hydrates_exact_environment_name(self) -> None:
        environ: dict[str, str] = {}
        status = resolve_secrets(
            {"OPENROUTER_API_KEY": "new-key"},
            environ=environ,
        )

        self.assertTrue(status["OPENROUTER_API_KEY"])
        self.assertEqual(environ["OPENROUTER_API_KEY"], "new-key")

    def test_existing_environment_value_wins_over_streamlit_secret(self) -> None:
        environ = {"OPENROUTER_API_KEY": "local-key"}
        resolve_secrets(
            {"OPENROUTER_API_KEY": "cloud-key"},
            environ=environ,
        )

        self.assertEqual(environ["OPENROUTER_API_KEY"], "local-key")

    def test_lowercase_alias_is_not_accepted(self) -> None:
        environ: dict[str, str] = {}
        status = resolve_secrets(
            {"openrouter_api_key": "wrong-case"},
            environ=environ,
        )

        self.assertFalse(status["OPENROUTER_API_KEY"])
        self.assertNotIn("OPENROUTER_API_KEY", environ)

    def test_missing_secret_source_is_safe(self) -> None:
        status = resolve_secrets(None, environ={})

        self.assertFalse(status["OPENROUTER_API_KEY"])

    def test_unconfigured_streamlit_secret_store_is_safe(self) -> None:
        class MissingSecretStore(dict):
            def get(self, key: str, default=None):
                raise FileNotFoundError("No secrets file")

        status = resolve_secrets(MissingSecretStore(), environ={})

        self.assertFalse(status["OPENROUTER_API_KEY"])

    def test_status_never_contains_secret_values(self) -> None:
        status = resolve_secrets(
            {},
            environ={"OPENROUTER_API_KEY": "secret-value"},
        )

        self.assertTrue(status["OPENROUTER_API_KEY"])
        self.assertFalse(status["TAVILY_API_KEY"])
        self.assertFalse(status["FIRECRAWL_API_KEY"])
        self.assertNotIn("secret-value", repr(status))

    def test_provider_and_tool_names_are_stable(self) -> None:
        self.assertEqual(provider_secret_name("openrouter"), "OPENROUTER_API_KEY")
        self.assertEqual(
            configured_secret_names("openrouter"),
            ("OPENROUTER_API_KEY", "TAVILY_API_KEY", "FIRECRAWL_API_KEY"),
        )


if __name__ == "__main__":
    unittest.main()
