"""Unit tests for Claude Code + OpenRouter setup tool.

Tests:
- API key masking and validation logic
- Environment configuration reading and setting
- OpenRouter model parsing and catalog filtering
- Idempotent configuration and repair routines
- Mocked error handling
"""

import os
import unittest
from unittest.mock import patch, MagicMock

import config
import openrouter
import installer


class TestConfigModule(unittest.TestCase):
    def test_mask_key_format(self):
        # Synthetic test key
        raw_key = "sk-or-v1-abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        masked = config.mask_key(raw_key)
        self.assertTrue(masked.startswith("sk-or-v1-a"))
        self.assertTrue(masked.endswith("bcdef (length: 79)"))
        self.assertNotIn("1234567890abcdef1234", masked)

        # None or short keys
        self.assertEqual(config.mask_key(None), "[Not Set]")
        self.assertEqual(config.mask_key(""), "[Not Set]")
        self.assertEqual(config.mask_key("short"), "***")

    def test_validate_key_format(self):
        valid_key = "sk-or-v1-1234567890abcdef1234567890abcdef"
        ok, msg = config.validate_key_format(valid_key)
        self.assertTrue(ok)

        # Invalid prefixes
        bad_key = "invalid-key-format-1234567890"
        ok, msg = config.validate_key_format(bad_key)
        self.assertFalse(ok)
        self.assertIn("sk-or-", msg)

        # Empty
        ok, msg = config.validate_key_format("")
        self.assertFalse(ok)

    @patch("config.set_user_env_var")
    @patch("config.delete_user_env_var")
    @patch("config.broadcast_setting_change")
    def test_apply_openrouter_config(self, mock_broadcast, mock_delete, mock_set):
        api_key = "sk-or-v1-testkey12345678901234567890"
        model = "recursive/flint-v1.0:free"

        config.apply_openrouter_config(api_key, model, context_tokens=262144)

        # Verify essential variables were set
        mock_set.assert_any_call("OPENROUTER_API_KEY", api_key)
        mock_set.assert_any_call("ANTHROPIC_AUTH_TOKEN", api_key)
        mock_set.assert_any_call("ANTHROPIC_BASE_URL", "https://openrouter.ai/api")
        mock_set.assert_any_call("ANTHROPIC_MODEL", model)
        mock_set.assert_any_call("CLAUDE_CODE_MAX_CONTEXT_TOKENS", "262144")

        # Verify conflicting variable removed
        mock_delete.assert_called_with("ANTHROPIC_API_KEY")
        mock_broadcast.assert_called_once()

    @patch("config.get_current_configuration")
    @patch("config.set_user_env_var")
    @patch("config.delete_user_env_var")
    @patch("config.broadcast_setting_change")
    def test_repair_environment(self, mock_broadcast, mock_delete, mock_set, mock_get_cfg):
        # Simulate inconsistent environment
        mock_get_cfg.return_value = {
            "OPENROUTER_API_KEY": "sk-or-v1-mykey1234567890",
            "ANTHROPIC_AUTH_TOKEN": "wrong-token",
            "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
            "OPENROUTER_MODEL": "recursive/flint-v1.0:free",
            "ANTHROPIC_MODEL": "different-model",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": None,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": None,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": None,
            "CLAUDE_CODE_MAX_CONTEXT_TOKENS": None,
            "ANTHROPIC_API_KEY": "stale-direct-key",
        }

        repaired, actions = config.repair_environment()
        self.assertTrue(repaired)
        self.assertGreater(len(actions), 0)

        # Base URL must be repaired
        mock_set.assert_any_call("ANTHROPIC_BASE_URL", "https://openrouter.ai/api")
        # Token must be synchronized
        mock_set.assert_any_call("ANTHROPIC_AUTH_TOKEN", "sk-or-v1-mykey1234567890")
        # Stale key deleted
        mock_delete.assert_called_with("ANTHROPIC_API_KEY")


class TestOpenRouterClient(unittest.TestCase):
    @patch("openrouter._make_request")
    def test_validate_api_key_success(self, mock_request):
        mock_request.return_value = (
            200,
            {
                "data": {
                    "label": "sk-or-v1-test...123",
                    "free_model_daily_requests": {"used": 5, "limit": 1000, "remaining": 995},
                }
            },
        )
        ok, data, msg = openrouter.validate_api_key("sk-or-v1-testkey1234567890")
        self.assertTrue(ok)
        self.assertEqual(data["free_model_daily_requests"]["remaining"], 995)

    @patch("openrouter._make_request")
    def test_validate_api_key_failure(self, mock_request):
        mock_request.return_value = (401, {"error": {"message": "Invalid API key"}})
        ok, data, msg = openrouter.validate_api_key("sk-or-v1-invalidkey1234567890")
        self.assertFalse(ok)
        self.assertIn("Authentication failed", msg)

    @patch("openrouter._make_request")
    def test_fetch_models_free_filtering(self, mock_request):
        mock_request.return_value = (
            200,
            {
                "data": [
                    {"id": "recursive/flint-v1.0:free", "context_length": 262144},
                    {"id": "anthropic/claude-3.5-sonnet", "context_length": 200000},
                    {"id": "google/gemma-4-26b-a4b-it:free", "context_length": 131072},
                ]
            },
        )
        ok, models, msg = openrouter.fetch_models(free_only=True)
        self.assertTrue(ok)
        self.assertEqual(len(models), 2)
        model_ids = [m["id"] for m in models]
        self.assertIn("recursive/flint-v1.0:free", model_ids)
        self.assertNotIn("anthropic/claude-3.5-sonnet", model_ids)


class TestInstallerModule(unittest.TestCase):
    def test_detect_python_version(self):
        ok, ver = installer.detect_python()
        self.assertTrue(ok)
        self.assertTrue(ver.startswith("3."))

    def test_is_windows_runtime(self):
        # On Windows host, is_windows() must return True
        self.assertTrue(installer.is_windows())


if __name__ == "__main__":
    unittest.main()
