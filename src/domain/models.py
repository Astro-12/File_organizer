"""Domain Models - Pydantic configuration and data models"""

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DuplicateHandling(str, Enum):
    SKIP = "skip"
    RENAME = "rename"
    OVERWRITE = "overwrite"


class WatchMode(str, Enum):
    OFF = "off"
    ON = "on"


class FileRule(BaseModel):
    """A single classification rule mapping extensions to a category and destination"""
    category: str = Field(..., min_length=1, description="Category name (e.g., Images, Videos)")
    extensions: list[str] = Field(..., min_length=1, description="List of file extensions (e.g., ['.jpg', '.png'])")
    destination: Path = Field(..., description="Destination directory path")
    enabled: bool = Field(default=True, description="Whether this rule is active")
    priority: int = Field(default=0, description="Rule priority (higher = processed first)")

    @field_validator("extensions", mode="before")
    @classmethod
    def normalize_extensions(cls, v: list[str]) -> list[str]:
        """Ensure extensions start with dot and are lowercase"""
        normalized = []
        for ext in v:
            ext = ext.strip().lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            normalized.append(ext)
        return normalized

    @field_validator("destination", mode="before")
    @classmethod
    def ensure_path(cls, v: str | Path) -> Path:
        """Convert to Path object"""
        return Path(v) if isinstance(v, str) else v


class OrganizerOptions(BaseModel):
    """Global organizer options"""
    create_subfolders_by_date: bool = Field(default=True, description="Create YYYY-MM subfolders")
    date_format: str = Field(default="%Y-%m", description="strftime format for date subfolders")
    handle_duplicates: DuplicateHandling = Field(default=DuplicateHandling.RENAME, description="How to handle duplicate filenames")
    dry_run: bool = Field(default=False, description="Preview mode - don't actually move files")
    recursive: bool = Field(default=True, description="Scan subdirectories recursively")
    min_file_size: int = Field(default=0, ge=0, description="Minimum file size in bytes (0 = no limit)")
    max_file_size: int | None = Field(default=None, ge=0, description="Maximum file size in bytes (null = no limit)")


class WatchConfig(BaseModel):
    """File watcher configuration"""
    enabled: bool = Field(default=False, description="Enable continuous watching")
    debounce_seconds: float = Field(default=2.0, ge=0.1, le=60.0, description="Debounce time for file events")


class AppConfig(BaseModel):
    """Main application configuration"""
    source_paths: list[Path] = Field(default_factory=list, description="Paths to scan for files")
    rules: list[FileRule] = Field(default_factory=list, description="Classification rules")
    options: OrganizerOptions = Field(default_factory=OrganizerOptions, description="Global options")
    watch: WatchConfig = Field(default_factory=WatchConfig, description="Watch mode configuration")

    @field_validator("source_paths", mode="before")
    @classmethod
    def ensure_source_paths(cls, v: list[str | Path]) -> list[Path]:
        """Convert to Path objects"""
        return [Path(p) if isinstance(p, str) else p for p in v]

    @field_validator("rules", mode="before")
    @classmethod
    def sort_rules_by_priority(cls, v: list[dict | FileRule]) -> list[dict | FileRule]:
        """Sort rules by priority descending"""
        def get_priority(r):
            if isinstance(r, dict):
                return r.get("priority", 0)
            return getattr(r, "priority", 0)
        return sorted(v, key=get_priority, reverse=True)


class FileInfo(BaseModel):
    """Information about a file to be organized"""
    source_path: Path
    filename: str
    extension: str
    size: int
    matched_rule: FileRule | None = None
    destination_path: Path | None = None
    status: Literal["pending", "moved", "skipped", "error"] = "pending"
    error_message: str | None = None


class OrganizeResult(BaseModel):
    """Result of an organize operation"""
    total_files: int = 0
    moved_files: int = 0
    skipped_files: int = 0
    error_files: int = 0
    errors: list[str] = Field(default_factory=list)
    dry_run: bool = False


DEFAULT_RULES: list[FileRule] = [
    FileRule(
        category="Images",
        extensions=[".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg", ".ico", ".heic", ".avif"],
        destination=Path.home() / "Pictures" / "Organized",
        priority=100
    ),
    FileRule(
        category="Videos",
        extensions=[".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"],
        destination=Path.home() / "Videos" / "Organized",
        priority=90
    ),
    FileRule(
        category="Documents",
        extensions=[".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
        destination=Path.home() / "Documents" / "Organized",
        priority=80
    ),
    FileRule(
        category="Audio",
        extensions=[".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus", ".aiff"],
        destination=Path.home() / "Music" / "Organized",
        priority=70
    ),
    FileRule(
        category="Archives",
        extensions=[".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"],
        destination=Path.home() / "Archives" / "Organized",
        priority=60
    ),
    FileRule(
        category="Code",
        extensions=[".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh", ".bat", ".ps1", ".sql", ".cs", ".java", ".cpp", ".c", ".h", ".rs", ".go", ".rb", ".php"],
        destination=Path.home() / "Code" / "Organized",
        priority=50
    ),
    FileRule(
        category="Executables",
        extensions=[".exe", ".msi", ".app", ".dmg", ".deb", ".rpm", ".apk", ".jar"],
        destination=Path.home() / "Software" / "Organized",
        priority=40
    ),
]