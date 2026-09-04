import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "backend" / "app.py").read_text(encoding="utf-8")
CONFIG = json.loads((ROOT / "config" / "config.json").read_text(encoding="utf-8"))
GITIGNORE = (ROOT / ".gitignore").read_text(encoding="utf-8")


class PublicReleaseContractTests(unittest.TestCase):
    def test_committed_dashboard_defaults_are_loopback_and_debug_off(self):
        self.assertIn(CONFIG["dashboard"]["host"], {"127.0.0.1", "localhost", "::1"})
        self.assertFalse(CONFIG["dashboard"]["debug"])
        self.assertEqual(CONFIG["piper"]["binary_path"], "")
        self.assertEqual(CONFIG["piper"]["model_path"], "")
        self.assertTrue(CONFIG["ollama"]["host"].startswith("http://127.0.0.1:"))

    def test_backend_has_no_committed_secret_or_wildcard_cors(self):
        self.assertNotIn("youtube-ai-lab-secret", APP)
        self.assertNotIn('cors_allowed_origins="*"', APP)
        self.assertNotRegex(APP, r"CORS\(app\)\s*$")
        self.assertIn("YOUTUBE_AI_LAB_SECRET_KEY", APP)
        self.assertIn("YOUTUBE_AI_LAB_ALLOWED_ORIGINS", APP)

    def test_backend_requires_explicit_remote_bind_opt_in(self):
        self.assertIn("YOUTUBE_AI_LAB_ALLOW_REMOTE", APP)
        self.assertIn("Refusing non-loopback dashboard bind", APP)
        self.assertNotRegex(APP, r"192\.168\.\d{1,3}\.\d{1,3}")
        self.assertNotIn("debug=True", APP)

    def test_local_tool_paths_are_environment_driven(self):
        for name in ("OLLAMA_HOST", "PIPER_BIN", "PIPER_MODEL", "YOUTUBE_AI_LAB_DB_PATH"):
            self.assertIn(name, APP)
        self.assertNotIn("/home/chris/", APP)
        for test_path in (ROOT / "tests").glob("test_*.py"):
            self.assertNotIn("/home/chris/", test_path.read_text(encoding="utf-8"))

    def test_generated_media_and_credentials_are_ignored(self):
        for pattern in (
            "data/videos/",
            "*.mp4",
            "*.wav",
            "*.mp3",
            "config/youtube_secrets.json",
            "token.pickle",
            ".env",
        ):
            self.assertIn(pattern, GITIGNORE)

    def test_optional_hardware_tests_are_opt_in(self):
        ollama = (ROOT / "tests" / "test_ollama.py").read_text(encoding="utf-8")
        piper = (ROOT / "tests" / "test_piper.py").read_text(encoding="utf-8")
        self.assertIn("YOUTUBE_AI_LAB_RUN_LOCAL_AI_TESTS", ollama)
        self.assertIn("YOUTUBE_AI_LAB_RUN_LOCAL_TTS_TESTS", piper)
        self.assertIn("pytest.mark.skipif", ollama)
        self.assertIn("pytest.mark.skipif", piper)


if __name__ == "__main__":
    unittest.main()
