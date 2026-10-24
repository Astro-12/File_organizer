"""File Organizer - Main Entry Point"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.presentation.app import FileOrganizerApp


def main():
    """Main entry point"""
    try:
        app = FileOrganizerApp()
        app.run()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()