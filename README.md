## Prerequisites

- Python 3.10+ installed
- Poetry installed (one-time global tool)

Installation (PowerShell, recommended):
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

## Secrets & Configuration

All sensitive values (API keys) are loaded from environment variables.

1. Create a `.env` file in the root (gitignore'd):
XAI_API_KEY=your-key-here
XAI_MODEL=default-model-here
ZOTERO_LIBRARY_ID=your-library-id
ZOTERO_API_KEY=your-zotero-key

2. The project auto-loads `.env` via `python-dotenv` in development.
3. For production / CI / packaged exe: set real system environment variables.