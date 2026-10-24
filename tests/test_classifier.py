"""Tests for classifier"""

import pytest
from pathlib import Path
from src.domain.models import AppConfig, FileRule, FileInfo
from src.domain.classifier import FileClassifier


class TestFileClassifier:
    @pytest.fixture
    def config(self):
        rules = [
            FileRule(category="Images", extensions=[".jpg", ".png"], destination=Path("/tmp/images"), priority=100),
            FileRule(category="Documents", extensions=[".pdf", ".txt"], destination=Path("/tmp/docs"), priority=50),
        ]
        return AppConfig(rules=rules)

    @pytest.fixture
    def classifier(self, config):
        return FileClassifier(config)

    def test_classify_matching_extension(self, classifier):
        file_info = FileInfo(
            source_path=Path("/tmp/photo.jpg"),
            filename="photo.jpg",
            extension=".jpg",
            size=1024,
        )
        rule = classifier.classify(file_info)
        assert rule is not None
        assert rule.category == "Images"

    def test_classify_non_matching_extension(self, classifier):
        file_info = FileInfo(
            source_path=Path("/tmp/data.xyz"),
            filename="data.xyz",
            extension=".xyz",
            size=1024,
        )
        rule = classifier.classify(file_info)
        assert rule is None

    def test_classify_batch(self, classifier):
        files = [
            FileInfo(source_path=Path("/tmp/a.jpg"), filename="a.jpg", extension=".jpg", size=100),
            FileInfo(source_path=Path("/tmp/b.pdf"), filename="b.pdf", extension=".pdf", size=200),
            FileInfo(source_path=Path("/tmp/c.xyz"), filename="c.xyz", extension=".xyz", size=300),
        ]
        classified = classifier.classify_batch(files)
        assert classified[0].matched_rule is not None
        assert classified[0].matched_rule.category == "Images"
        assert classified[1].matched_rule is not None
        assert classified[1].matched_rule.category == "Documents"
        assert classified[2].matched_rule is None

    def test_get_categories(self, classifier):
        categories = classifier.get_categories()
        assert "Images" in categories
        assert "Documents" in categories
        assert len(categories) == 2

    def test_get_supported_extensions(self, classifier):
        exts = classifier.get_supported_extensions()
        assert ".jpg" in exts
        assert ".png" in exts
        assert ".pdf" in exts
        assert ".txt" in exts

    def test_refresh(self, classifier):
        new_config = AppConfig(rules=[
            FileRule(category="New", extensions=[".new"], destination=Path("/tmp/new"), priority=100)
        ])
        classifier.refresh(new_config)
        categories = classifier.get_categories()
        assert "New" in categories
        assert "Images" not in categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])