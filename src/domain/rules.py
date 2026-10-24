"""Rules Engine - Manages custom extension rules"""

from pathlib import Path

from ..domain.models import DEFAULT_RULES, AppConfig, FileRule
from ..infrastructure.logger import get_logger

logger = get_logger("rules")


class RulesEngine:
    """Manages classification rules including custom user rules"""

    def __init__(self, config: AppConfig):
        self.config = config

    def add_rule(self, rule: FileRule) -> None:
        """Add a new rule"""
        # Check for duplicate category
        existing = self.get_rule_by_category(rule.category)
        if existing:
            raise ValueError(f"Rule for category '{rule.category}' already exists")

        self.config.rules.append(rule)
        # Re-sort by priority
        self.config.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added rule: {rule.category} ({len(rule.extensions)} extensions)")

    def update_rule(self, category: str, **updates) -> bool:
        """Update an existing rule"""
        rule = self.get_rule_by_category(category)
        if not rule:
            return False

        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        # Re-sort if priority changed
        if "priority" in updates:
            self.config.rules.sort(key=lambda r: r.priority, reverse=True)

        logger.info(f"Updated rule: {category}")
        return True

    def remove_rule(self, category: str) -> bool:
        """Remove a rule by category"""
        rule = self.get_rule_by_category(category)
        if not rule:
            return False

        self.config.rules.remove(rule)
        logger.info(f"Removed rule: {category}")
        return True

    def get_rule_by_category(self, category: str) -> FileRule | None:
        """Get rule by category name"""
        for rule in self.config.rules:
            if rule.category.lower() == category.lower():
                return rule
        return None

    def get_all_rules(self) -> list[FileRule]:
        """Get all rules"""
        return self.config.rules.copy()

    def get_enabled_rules(self) -> list[FileRule]:
        """Get only enabled rules"""
        return [r for r in self.config.rules if r.enabled]

    def toggle_rule(self, category: str) -> bool:
        """Enable/disable a rule"""
        rule = self.get_rule_by_category(category)
        if not rule:
            return False

        rule.enabled = not rule.enabled
        logger.info(f"Rule '{category}' {'enabled' if rule.enabled else 'disabled'}")
        return True

    def reorder_rules(self, categories: list[str]) -> None:
        """Reorder rules by category priority (first = highest)"""
        category_to_rule = {r.category.lower(): r for r in self.config.rules}
        new_rules = []

        for cat in categories:
            rule = category_to_rule.get(cat.lower())
            if rule:
                new_rules.append(rule)

        # Add any remaining rules not in the list
        for rule in self.config.rules:
            if rule.category.lower() not in [c.lower() for c in categories]:
                new_rules.append(rule)

        self.config.rules = new_rules
        # Update priorities
        for i, rule in enumerate(self.config.rules):
            rule.priority = len(self.config.rules) - i
        logger.info("Reordered rules")

    def add_extension_to_rule(self, category: str, extension: str) -> bool:
        """Add extension to existing rule"""
        rule = self.get_rule_by_category(category)
        if not rule:
            return False

        ext = extension.strip().lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        if ext not in rule.extensions:
            rule.extensions.append(ext)
            logger.info(f"Added extension {ext} to {category}")
            return True
        return False

    def remove_extension_from_rule(self, category: str, extension: str) -> bool:
        """Remove extension from rule"""
        rule = self.get_rule_by_category(category)
        if not rule:
            return False

        ext = extension.strip().lower()
        if not ext.startswith("."):
            ext = f".{ext}"

        if ext in rule.extensions:
            rule.extensions.remove(ext)
            logger.info(f"Removed extension {ext} from {category}")
            return True
        return False

    def reset_to_defaults(self) -> None:
        """Reset rules to built-in defaults"""
        self.config.rules = DEFAULT_RULES.copy()
        logger.info("Reset rules to defaults")

    def validate_rule(self, rule: FileRule) -> list[str]:
        """Validate a rule and return list of errors"""
        errors = []

        if not rule.category or not rule.category.strip():
            errors.append("Category name is required")

        if not rule.extensions:
            errors.append("At least one extension is required")

        if not rule.destination:
            errors.append("Destination path is required")
        elif not Path(rule.destination).exists():
            errors.append(f"Destination path does not exist: {rule.destination}")

        # Check for duplicate extensions across rules
        all_extensions = {}
        for r in self.config.rules:
            if r.category == rule.category:
                continue
            for ext in r.extensions:
                if ext in all_extensions:
                    all_extensions[ext].append(r.category)
                else:
                    all_extensions[ext] = [r.category]

        for ext in rule.extensions:
            if ext in all_extensions:
                errors.append(
                    f"Extension {ext} already used by: {', '.join(all_extensions[ext])}"
                )

        return errors