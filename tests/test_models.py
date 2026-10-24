"""Tests for domain models"""

import pytest
from pathlib import Path
from src.domain.models import (
    FileRule, OrganizerOptions, WatchConfig, AppConfig,
    FileInfo, OrganizeResult, DuplicateHandling,
    DEFAULT_RULES
)


class TestFileRule:
    def test_create_rule(self):
        rule = FileRule(
            category="Test",
            extensions=[".txt", ".md"],
            destination=Path("/tmp/test"),
        )
        assert rule.category == "Test"
        assert rule.extensions == [".txt", ".md"]
        assert rule.enabled is True
        assert rule.priority == 0

    def test_normalize_extensions(self):
        rule = FileRule(
            category="Test",
            extensions=["txt", ".MD", "Py"],
            destination=Path("/tmp/test"),
        )
        assert rule.extensions == [".txt", ".md", ".py"]

    def test_ensure_path_string(self):
        rule = FileRule(
            category="Test",
            extensions=[".txt"],
            destination="/tmp/test",
        )
        assert isinstance(rule.destination, Path)


class TestOrganizerOptions:
    def test_defaults(self):
        opts = OrganizerOptions()
        assert opts.create_subfolders_by_date is True
        assert opts.date_format == "%Y-%m"
        assert opts.handle_duplicates == DuplicateHandling.RENAME
        assert opts.dry_run is False
        assert opts.recursive is True
        assert opts.min_file_size == 0
        assert opts.max_file_size is None


class TestAppConfig:
    def test_default_config(self):
        config = AppConfig()
        assert config.source_paths == []
        assert config.rules == []
        assert isinstance(config.options, OrganizerOptions)
        assert isinstance(config.watch, WatchConfig)

    def test_sort_rules_by_priority(self):
        rule1 = FileRule(category="A", extensions=[".a"], destination=Path("/tmp"), priority=10)
        rule2 = FileRule(category="B", extensions=[".b"], destination=Path("/tmp"), priority=20)
        rule3 = FileRule(category="C", extensions=[".c"], destination=Path("/tmp"), priority=5)

        config = AppConfig(rules=[rule1, rule2, rule3])
        priorities = [r.priority for r in config.rules]
        assert priorities == [20, 10, 5]


class TestFileInfo:
    def test_create_file_info(self):
        info = FileInfo(
            source_path=Path("/tmp/test.txt"),
            filename="test.txt",
            extension=".txt",
            size=1024,
        )
        assert info.status == "pending"
        assert info.matched_rule is None
        assert info.destination_path is None


class TestOrganizeResult:
    def test_default_result(self):
        result = OrganizeResult()
        assert result.total_files == 0
        assert result.moved_files == 0
        assert result.skipped_files == 0
        assert result.error_files == 0
        assert result.errors == []
        assert result.dry_run is False


class TestDefaultRules:
    def test_default_rules_exist(self):
        assert len(DEFAULT_RULES) == 7
        categories = [r.category for r in DEFAULT_RULES]
        assert "Images" in categories
        assert "Videos" in categories
        assert "Documents" in categories
        assert "Audio" in categories
        assert "Archives" in categories
        assert "Code" in categories
        assert "Executables" in categories

    def test_default_rules_have_extensions(self):
        for rule in DEFAULT_RULES:
            assert len(rule.extensions) > 0
            for ext in rule.extensions:
                assert ext.startswith(".")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])