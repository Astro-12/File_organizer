"""Filesystem operations wrapper"""

import os
import shutil
from collections.abc import Generator
from pathlib import Path

from ..domain.models import DuplicateHandling, FileInfo


class FileSystem:
    """Wrapper for filesystem operations with safety checks"""

    @staticmethod
    def scan_files(
        source_paths: list[Path],
        recursive: bool = True,
        min_size: int = 0,
        max_size: int | None = None,
    ) -> Generator[FileInfo, None, None]:
        """Scan source paths for files matching criteria"""
        for source_path in source_paths:
            if not source_path.exists():
                continue

            if recursive:
                paths = source_path.rglob("*")
            else:
                paths = source_path.glob("*")

            for path in paths:
                if not path.is_file():
                    continue

                try:
                    stat = path.stat()
                except OSError:
                    continue

                if stat.st_size < min_size:
                    continue
                if max_size is not None and stat.st_size > max_size:
                    continue

                yield FileInfo(
                    source_path=path,
                    filename=path.name,
                    extension=path.suffix.lower(),
                    size=stat.st_size,
                )

    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Create directory if it doesn't exist"""
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_unique_destination(
        destination_dir: Path,
        filename: str,
        handling: DuplicateHandling,
    ) -> Path:
        """Get destination path handling duplicates according to strategy"""
        dest_path = destination_dir / filename

        if not dest_path.exists():
            return dest_path

        if handling == DuplicateHandling.SKIP:
            raise FileExistsError(f"File exists and skip mode: {dest_path}")

        if handling == DuplicateHandling.OVERWRITE:
            return dest_path

        # RENAME: Find unique name with counter
        stem = dest_path.stem
        suffix = dest_path.suffix
        counter = 1

        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = destination_dir / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    @staticmethod
    def move_file(
        source: Path,
        destination: Path,
        dry_run: bool = False,
    ) -> None:
        """Move file from source to destination"""
        if dry_run:
            return

        # Ensure destination directory exists
        FileSystem.ensure_directory(destination.parent)

        try:
            # Try atomic move first (same filesystem)
            shutil.move(str(source), str(destination))
        except OSError:
            # Cross-filesystem: copy then remove
            shutil.copy2(source, destination)
            source.unlink()

    @staticmethod
    def get_file_size(path: Path) -> int:
        """Get file size in bytes"""
        return path.stat().st_size

    @staticmethod
    def path_exists(path: Path) -> bool:
        """Check if path exists"""
        return path.exists()

    @staticmethod
    def is_directory(path: Path) -> bool:
        """Check if path is a directory"""
        return path.is_dir()

    @staticmethod
    def is_file(path: Path) -> bool:
        """Check if path is a file"""
        return path.is_file()

    @staticmethod
    def list_drives() -> list[Path]:
        """Get list of available drives (Windows) or mount points (Linux/macOS)"""
        drives = []
        if os.name == "nt":
            # Windows: check drive letters
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = Path(f"{letter}:\\")
                if drive.exists():
                    drives.append(drive)
        else:
            # Unix-like: common mount points
            for mount in [Path("/"), Path.home(), Path("/media"), Path("/mnt")]:
                if mount.exists():
                    drives.append(mount)
        return drives