"""Regression coverage for local configuration and saved skill memory."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import DEFAULT_CONFIG, load_config
from skill_manager import SkillManager


class ConfigRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env_patch = patch.dict(os.environ, {}, clear=True)
        env_patch.start()
        self.addCleanup(env_patch.stop)

    def test_environment_override_does_not_contaminate_future_loads(self):
        missing = str(self.root / "not-created.yaml")
        original_model = DEFAULT_CONFIG["models"]["chat"]
        with patch.dict(os.environ, {"RAG_CHAT_MODEL": "synthetic-model"}):
            first = load_config(missing)
        first["retrieval"]["k"] = 999
        second = load_config(missing)
        self.assertEqual(second["models"]["chat"], original_model)
        self.assertEqual(second["retrieval"]["k"], 5)
        self.assertEqual(DEFAULT_CONFIG["retrieval"]["k"], 5)

    def test_yaml_merge_is_independent_and_environment_takes_priority(self):
        config = self.root / "settings.yaml"
        config.write_text("retrieval:\n  k: 12\nmodels:\n  chat: yaml-model\n", encoding="utf-8")
        with patch.dict(os.environ, {"RAG_CHAT_MODEL": "env-model", "RAG_RETRIEVAL_K": "7"}):
            result = load_config(str(config))
        self.assertEqual(result["models"]["chat"], "env-model")
        self.assertEqual(result["retrieval"]["k"], 7)
        self.assertEqual(result["retrieval"]["chunk_size"], 800)
        result["ollama"]["timeout"] = 1
        self.assertEqual(load_config(str(config))["ollama"]["timeout"], 120)

    def test_fractional_temperature_environment_override(self):
        target = self.root / "settings.yaml"
        target.write_text("models:\n  temperature: 0\n", encoding="utf-8")
        with patch.dict(os.environ, {"RAG_TEMPERATURE": "0.7"}):
            result = load_config(str(target))
        self.assertEqual(result["models"]["temperature"], 0.7)

    def test_non_mapping_yaml_is_rejected(self):
        for value in ("- item\n", "false\n", "42\n"):
            target = self.root / "invalid.yaml"
            target.write_text(value, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mapping"):
                load_config(str(target))


class SkillPersistenceTests(unittest.TestCase):
    def test_saved_skill_survives_reload_and_hit_count_is_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = SkillManager(folder)
            skill = manager.save_skill("How does Ollama work?", "A synthetic answer", sources=["note.md"])
            reloaded = SkillManager(folder)
            self.assertEqual(reloaded.search_skills("Ollama")[0]["skill_id"], skill["skill_id"])
            self.assertEqual(reloaded.get_skill_answer(skill["skill_id"])["hits"], 1)
            index = json.loads((Path(folder) / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(index["skills"][0]["hits"], 1)

    def test_low_rating_is_filtered_and_deleted_skill_does_not_return(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = SkillManager(folder)
            low = manager.save_skill("Ollama draft", "Unreviewed", rating=2)
            high = manager.save_skill("Ollama setup", "Reviewed", rating=5)
            self.assertEqual(len(manager.search_skills("Ollama", min_rating=4)), 1)
            self.assertTrue(manager.delete_skill(high["skill_id"]))
            self.assertEqual(SkillManager(folder).search_skills("Ollama", min_rating=4), [])
            self.assertEqual(len(manager.list_skills()), 1)
            self.assertEqual(manager.list_skills()[0]["skill_id"], low["skill_id"])


if __name__ == "__main__":
    unittest.main()
