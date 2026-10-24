"""File Mover - Handles safe file relocation"""


from ..domain.models import DuplicateHandling, FileInfo, OrganizeResult
from ..infrastructure.filesystem import FileSystem
from ..infrastructure.logger import get_logger

logger = get_logger("mover")


class FileMover:
    """Moves files to their designated destinations"""

    def __init__(self, options: object | None = None):
        self.options = options
        self.filesystem = FileSystem()

    def move_file(self, file_info: FileInfo) -> bool:
        """Move a single file to its destination"""
        if not file_info.matched_rule or not file_info.destination_path:
            file_info.status = "error"
            file_info.error_message = "No destination rule matched"
            logger.warning(f"Cannot move {file_info.filename}: no rule matched")
            return False

        dest_dir = file_info.destination_path.parent
        filename = file_info.destination_path.name
        handling = DuplicateHandling.RENAME
        if self.options and hasattr(self.options, 'handle_duplicates'):
            handling = self.options.handle_duplicates

        try:
            # Get unique destination path
            unique_dest = self.filesystem.get_unique_destination(
                dest_dir, filename, handling
            )

            # Move the file
            dry_run = False
            if self.options and hasattr(self.options, 'dry_run'):
                dry_run = self.options.dry_run

            self.filesystem.move_file(
                file_info.source_path,
                unique_dest,
                dry_run=dry_run,
            )

            file_info.status = "moved"
            file_info.destination_path = unique_dest
            logger.info(f"Moved: {file_info.filename} -> {unique_dest}")
            return True

        except FileExistsError as e:
            file_info.status = "skipped"
            file_info.error_message = str(e)
            logger.info(f"Skipped (exists): {file_info.filename}")
            return False
        except OSError as e:
            file_info.status = "error"
            file_info.error_message = str(e)
            logger.error(f"Failed to move {file_info.filename}: {e}")
            return False

    def move_batch(self, files: list[FileInfo]) -> OrganizeResult:
        """Move multiple files and return aggregate result"""
        result = OrganizeResult(
            total_files=len(files),
            dry_run=self.options.dry_run if self.options and hasattr(self.options, 'dry_run') else False
        )

        for file_info in files:
            if file_info.status == "pending":
                success = self.move_file(file_info)
                if success:
                    result.moved_files += 1
                elif file_info.status == "skipped":
                    result.skipped_files += 1
                else:
                    result.error_files += 1
                    if file_info.error_message:
                        result.errors.append(f"{file_info.filename}: {file_info.error_message}")

        logger.info(
            f"Organize complete: {result.moved_files} moved, "
            f"{result.skipped_files} skipped, {result.error_files} errors"
        )
        return result