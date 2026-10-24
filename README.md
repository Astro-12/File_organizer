# File Organizer

A TUI-based file organizer that scans designated folders, classifies files by extension, and relocates them to customized destination folders. Supports both one-time scan and continuous watch modes.

## Features

- **TUI Interface**: Modern terminal UI built with Textual - runs in any terminal
- **File Classification**: Built-in rules for Images, Videos, Documents, Audio, Archives, Code, Executables
- **Custom Rules**: Add/edit/remove custom categories with your own extensions
- **Flexible Destinations**: Configure custom destination paths for each category
- **Two Modes**: One-time scan or continuous watch mode with debouncing
- **Safe Operations**: Dry-run preview, duplicate handling (rename/skip/overwrite)
- **Configuration**: Persistent JSON config with in-app editor
- **Cross-platform**: Works on Windows, Linux, macOS

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Usage

```bash
# Run the TUI
file-organizer

# Or run directly
python -m src.main
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F1 | Help |
| F2 | Config Screen |
| F3 | Logs Screen |
| F5 | Scan |
| F6 | Organize |
| F7 | Toggle Watch |
| Ctrl+C | Cancel Operation |
| Ctrl+Q | Quit |
| N | New Rule (in Config) |
| Ctrl+S | Save (in Config) |
| Esc | Back |

## Configuration

Configuration is stored in `~/.config/file-organizer/config.json` and includes:

- **Source Paths**: Folders/drives to scan
- **Rules**: Category → Extensions → Destination mappings
- **Options**: Date subfolders, duplicate handling, recursive scan, size filters
- **Watch**: Enable/disable continuous monitoring, debounce timing

## Project Structure

```
src/
├── main.py                 # Entry point
├── presentation/           # TUI Layer (Textual)
│   ├── app.py             # Main application
│   ├── screens/           # Dashboard, Config, Logs
│   └── widgets/           # Reusable UI components
├── application/           # Services
│   ├── organizer_service.py
│   ├── watch_service.py
│   └── config_service.py
├── domain/                # Business Logic
│   ├── models.py          # Pydantic models
│   ├── classifier.py      # Extension classification
│   ├── mover.py           # File moving
│   └── rules.py           # Rules engine
└── infrastructure/        # External Interfaces
    ├── config_store.py    # JSON persistence
    ├── filesystem.py      # File operations
    └── logger.py          # Logging
```

## Development

```bash
# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## Requirements

- Python 3.10+
- textual >= 0.50.0
- watchdog >= 3.0.0
- pydantic >= 2.0.0
- pydantic-settings >= 2.0.0

## License

MIT