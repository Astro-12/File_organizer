"""Tests for rules engine"""

import pytest
from pathlib import Path
from src.domain.models import AppConfig, FileRule
from src.domain.rules import RulesEngine


class TestRulesEngine:
    @pytest.fixture
    def config(self):
        rules = [
            FileRule(category="Images", extensions=[".jpg", ".png"], destination=Path("/tmp/images"), priority=100),
            FileRule(category="Documents", extensions=[".pdf", ".txt"], destination=Path("/tmp/docs"), priority=50),
        ]
        return AppConfig(rules=rules)

    @pytest.fixture
    def engine(self, config):
        return RulesEngine(config)

    def test_get_all_rules(self, engine):
        rules = engine.get_all_rules()
        assert len(rules) == 2

    def test_get_enabled_rules(self, engine):
        rules = engine.get_enabled_rules()
        assert len(rules) == 2

    def test_get_rule_by_category(self, engine):
        rule = engine.get_rule_by_category("Images")
        assert rule is not None
        assert rule.category == "Images"

    def test_get_rule_by_category_case_insensitive(self, engine):
        rule = engine.get_rule_by_category("images")
        assert rule is not None

    def test_add_rule(self, engine):
        new_rule = FileRule(category="Audio", extensions=[".mp3"], destination=Path("/tmp/audio"))
        engine.add_rule(new_rule)
        rules = engine.get_all_rules()
        assert len(rules) == 3
        assert engine.get_rule_by_category("Audio") is not None

    def test_add_duplicate_category_raises(self, engine):
        new_rule = FileRule(category="Images", extensions=[".gif"], destination=Path("/tmp/images2"))
        with pytest.raises(ValueError):
            engine.add_rule(new_rule)

    def test_remove_rule(self, engine):
        result = engine.remove_rule("Images")
        assert result is True
        assert engine.get_rule_by_category("Images") is None
        assert len(engine.get_all_rules()) == 1

    def test_remove_nonexistent_rule(self, engine):
        result = engine.remove_rule("NonExistent")
        assert result is False

    def test_toggle_rule(self, engine):
        engine.toggle_rule("Images")
        assert engine.get_rule_by_category("Images").enabled is False
        engine.toggle_rule("Images")
        assert engine.get_rule_by_category("Images").enabled is True

    def test_update_rule(self, engine):
        engine.update_rule("Images", destination=Path("/tmp/new_images"))
        assert engine.get_rule_by_category("Images").destination == Path("/tmp/new_images")

    def test_add_extension_to_rule(self, engine):
        engine.add_extension_to_rule("Images", ".gif")
        assert ".gif" in engine.get_rule_by_category("Images").extensions

    def test_remove_extension_from_rule(self, engine):
        engine.remove_extension_from_rule("Images", ".jpg")
        assert ".jpg" not in engine.get_rule_by_category("Images").extensions

    def test_reorder_rules(self, engine):
        engine.reorder_rules(["Documents", "Images"])
        rules = engine.get_all_rules()
        assert rules[0].category == "Documents"
        assert rules[1].category == "Images"

    def test_reset_to_defaults(self, engine):
        engine.reset_to_defaults()
        rules = engine.get_all_rules()
        assert len(rules) == 7

    def test_validate_rule_valid(self, engine):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = FileRule(category="NewCat", extensions=[".new"], destination=Path(tmpdir))
            errors = engine.validate_rule(rule)
            assert len(errors) == 0

    def test_validate_rule_missing_category(self, engine):
        # Pydantic validates this at model creation, so we test the engine validation differently
        errors = engine.validate_rule(type('Rule', (), {
            'category': '',
            'extensions': ['.new'],
            'destination': Path("/tmp/new")
        })())
        assert "Category name is required" in errors

    def test_validate_rule_missing_extensions(self, engine):
        errors = engine.validate_rule(type('Rule', (), {
            'category': 'NewCat',
            'extensions': [],
            'destination': Path("/tmp/new")
        })())
        assert "At least one extension is required" in errors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])