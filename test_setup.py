"""Unit tests for Claude Code + OpenRouter setup tool.

Tests:
- API key masking and validation logic
- Environment configuration reading, setting, and cross-platform handling
- OpenRouter model parsing and catalog filtering
- Multi-model profiles and context presets (creation, switching, deletion)
- Token usage and credit tracking telemetry
- Terminal UI helpers and diagnostic rendering
- Idempotent configuration and repair routines
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import config
import openrouter
import installer
import profiles
import tracker
import tui


class TestConfigModule(unittest.TestCase):
    def test_mask_key_format(self):
        raw_key = "sk-or-v1-abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        masked = config.mask_key(raw_key)
        self.assertTrue(masked.startswith("sk-or-v1-a"))
        self.assertTrue(masked.endswith("bcdef (length: 79)"))
        self.assertNotIn("1234567890abcdef1234", masked)

        self.assertEqual(config.mask_key(None), "[Not Set]")
        self.assertEqual(config.mask_key(""), "[Not Set]")
        self.assertEqual(config.mask_key("short"), "***")

    def test_validate_key_format(self):
        valid_key = "sk-or-v1-1234567890abcdef1234567890abcdef"
        ok, msg = config.validate_key_format(valid_key)
        self.assertTrue(ok)

        bad_key = "invalid-key-format-1234567890"
        ok, msg = config.validate_key_format(bad_key)
        self.assertFalse(ok)
        self.assertIn("sk-or-", msg)

        ok, msg = config.validate_key_format("")
        self.assertFalse(ok)

    @patch("config.set_user_env_var")
    @patch("config.delete_user_env_var")
    @patch("config.broadcast_setting_change")
    def test_apply_openrouter_config(self, mock_broadcast, mock_delete, mock_set):
        api_key = "sk-or-v1-testkey12345678901234567890"
        model = "recursive/flint-v1.0:free"

        config.apply_openrouter_config(api_key, model, context_tokens=262144)

        mock_set.assert_any_call("OPENROUTER_API_KEY", api_key)
        mock_set.assert_any_call("ANTHROPIC_AUTH_TOKEN", api_key)
        mock_set.assert_any_call("ANTHROPIC_BASE_URL", "https://openrouter.ai/api")
        mock_set.assert_any_call("ANTHROPIC_MODEL", model)
        mock_set.assert_any_call("CLAUDE_CODE_MAX_CONTEXT_TOKENS", "262144")

        mock_delete.assert_called_with("ANTHROPIC_API_KEY")
        mock_broadcast.assert_called_once()

    @patch("config.get_current_configuration")
    @patch("config.set_user_env_var")
    @patch("config.delete_user_env_var")
    @patch("config.broadcast_setting_change")
    def test_repair_environment(self, mock_broadcast, mock_delete, mock_set, mock_get_cfg):
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

        mock_set.assert_any_call("ANTHROPIC_BASE_URL", "https://openrouter.ai/api")
        mock_set.assert_any_call("ANTHROPIC_AUTH_TOKEN", "sk-or-v1-mykey1234567890")
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


class TestProfilesModule(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mock_file = os.path.join(self.temp_dir.name, "test_profiles.json")
        self.orig_file = profiles.PROFILES_FILE
        profiles.PROFILES_FILE = self.mock_file

    def tearDown(self):
        profiles.PROFILES_FILE = self.orig_file
        self.temp_dir.cleanup()

    def test_profile_creation_and_switching(self):
        # 1. Load initial default presets
        data = profiles.load_profiles_data()
        self.assertIn("flint-free", data["profiles"])

        # 2. Create custom profile
        ok, msg = profiles.create_or_update_profile(
            name="test-sonnet",
            model="anthropic/claude-3.7-sonnet",
            context_tokens=200000,
            description="Test profile",
            activate=False,
        )
        self.assertTrue(ok)

        # 3. List profiles
        profs = profiles.list_profiles()
        names = [p["name"] for p in profs]
        self.assertIn("test-sonnet", names)

        # 4. Activate profile
        with patch("config.update_model") as mock_update_model:
            ok, msg = profiles.set_active_profile("test-sonnet")
            self.assertTrue(ok)
            active_name, active_prof = profiles.get_active_profile()
            self.assertEqual(active_name, "test-sonnet")
            self.assertEqual(active_prof["model"], "anthropic/claude-3.7-sonnet")
            mock_update_model.assert_called_with("anthropic/claude-3.7-sonnet", context_tokens=200000)

        # 5. Delete profile
        ok, msg = profiles.delete_profile("test-sonnet")
        self.assertTrue(ok)
        self.assertNotIn("test-sonnet", profiles.load_profiles_data()["profiles"])


class TestTrackerModule(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mock_file = os.path.join(self.temp_dir.name, "test_usage.json")
        self.orig_file = tracker.USAGE_FILE
        tracker.USAGE_FILE = self.mock_file

    def tearDown(self):
        tracker.USAGE_FILE = self.orig_file
        self.temp_dir.cleanup()

    def test_usage_logging_and_summary(self):
        tracker.clear_local_usage()
        tracker.record_usage_event(
            model="anthropic/claude-3.7-sonnet",
            prompt_tokens=150,
            completion_tokens=50,
            latency_ms=1200,
            success=True,
        )
        tracker.record_usage_event(
            model="recursive/flint-v1.0:free",
            prompt_tokens=80,
            completion_tokens=20,
            latency_ms=800,
            success=True,
        )

        summary = tracker.get_local_usage_summary()
        self.assertEqual(summary["total_requests"], 2)
        self.assertEqual(summary["total_prompt_tokens"], 230)
        self.assertEqual(summary["total_completion_tokens"], 70)
        self.assertEqual(summary["total_tokens"], 300)
        self.assertEqual(summary["model_breakdown"]["anthropic/claude-3.7-sonnet"], 1)

    @patch("tracker._make_request")
    def test_fetch_account_stats(self, mock_request):
        mock_request.return_value = (
            200,
            {
                "data": {
                    "label": "Balaji Key",
                    "usage": 1.254,
                    "limit": 10.0,
                    "is_free_tier": False,
                    "rate_limit": {"requests": 200, "interval": "10s"},
                }
            },
        )
        ok, stats, msg = tracker.fetch_openrouter_account_stats("sk-or-v1-testkey1234567890")
        self.assertTrue(ok)
        self.assertEqual(stats["label"], "Balaji Key")
        self.assertEqual(stats["usage"], 1.254)
        self.assertEqual(stats["limit"], 10.0)
        self.assertFalse(stats["is_free_tier"])
        self.assertEqual(stats["rate_limit_requests"], 200)


class TestInstallerModule(unittest.TestCase):
    def test_detect_python_version(self):
        ok, ver = installer.detect_python()
        self.assertTrue(ok)
        self.assertTrue(ver.startswith("3."))

    def test_system_info(self):
        info = installer.get_system_info()
        self.assertIn("system", info)
        self.assertIn("platform", info)


class TestFreeModelsSelection(unittest.TestCase):
    def test_top_free_models_all_free(self):
        import main
        self.assertTrue(len(main.TOP_FREE_MODELS) > 0)
        for m in main.TOP_FREE_MODELS:
            self.assertTrue(m["id"].endswith(":free"), f"Model {m['id']} is not free!")
            self.assertGreater(m.get("context_length", 0), 0)


if __name__ == "__main__":
    unittest.main()
