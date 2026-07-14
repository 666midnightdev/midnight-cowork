# AGENTS.md - Midnight Cowork

## Project Overview

Midnight Cowork is a local AI desktop assistant wrapping Open Interpreter with a ChatGPT-style web UI and WhatsApp remote control. Built for Windows with FastAPI (Python) backend and vanilla JS frontend.

## Tech Stack

- **Backend**: Python, FastAPI, Uvicorn, open-interpreter, pyautogui, httpx, paramiko
- **Frontend**: HTML, Tailwind CSS (CDN), vanilla JavaScript, Marked.js, Highlight.js
- **WhatsApp Bridge**: Node.js, @whiskeysockets/baileys, Express, Axios
- **Storage**: JSON files with atomic writes (no database)
- **Platform**: Windows only

## Project Structure

```
├── main.py                 # Entry point (thin wrapper, creates app + uvicorn)
├── app/                    # Backend package
│   ├── __init__.py         # App factory (create_app) + WhatsApp auto-start
│   ├── config.py           # Paths, constants, interpreter import, defaults
│   ├── models.py           # Pydantic request/response models
│   ├── storage.py          # JSON file ops with atomic writes + thread lock
│   ├── services/
│   │   ├── interpreter.py  # Interpreter config + provider env setup
│   │   ├── whatsapp.py     # WhatsAppState class (replaces globals)
│   │   └── workflows.py    # Workflow manager + SSH remote execution (paramiko)
│   └── routes/
│       ├── system.py       # GET /, GET /api/status, POST /api/shutdown
│       ├── chat.py         # CRUD /api/chats, POST /api/chat (SSE streaming)
│       ├── settings.py     # GET/POST /api/settings
│       └── whatsapp.py     # All /api/whatsapp/* endpoints
├── templates/index.html    # Single-page frontend (558 lines)
├── static/js/app.js        # Frontend JS logic (846 lines)
├── static/css/style.css    # Custom CSS (180 lines)
├── whatsapp/index.js       # WhatsApp Baileys bridge (167 lines)
├── whatsapp_setup.py       # Downloads portable Node.js + npm install
├── stop_server.py          # Graceful shutdown via PID + taskkill
├── start.bat               # Launches pythonw.exe + opens browser
├── stop.bat                # Kills server processes
├── pyproject.toml          # Project config (ruff, mypy, pytest)
├── settings.json           # Runtime LLM config (model, API key, system message)
├── chats.json              # Chat session history
├── whatsapp_sessions.json  # WhatsApp phone-to-chat mapping
└── requirements.txt        # Python dependencies
```

## Build / Run / Test Commands

### Run
```bash
# Install dependencies first
pip install -r requirements.txt

# Start server (background, no console window)
start.bat

# Or run directly for development
py main.py
# Server at http://127.0.0.1:8000
```

### Stop
```bash
stop.bat
# Or POST /api/shutdown from the UI
```

### Test
```bash
pip install pytest pytest-asyncio httpx
py -m pytest tests/ -v
```

### Lint (requires ruff binary, not just Python package)
```bash
ruff check app/ main.py tests/
ruff format app/ main.py tests/
```

### Setup WhatsApp Bridge (first time)
```bash
py whatsapp_setup.py
# Downloads portable Node.js to node_bin/ and runs npm install in whatsapp/
```

### Testing
15 automated tests covering routes and storage. Run via `py -m pytest tests/ -v`.

## Code Conventions

### Python
- **snake_case** for functions and variables
- **camelCase** not used (Python convention)
- Type hints on all function signatures
- Pydantic models for request validation
- `threading.Lock` + atomic file writes (temp file + `os.replace`) for JSON persistence
- `WhatsAppState` class encapsulates all WhatsApp mutable state (no globals)
- `ThreadPoolExecutor` + `asyncio.Queue` for non-blocking interpreter execution with SSE streaming
- Graceful degradation: `INTERPRETER_AVAILABLE` flag allows server to run without open-interpreter
- Bare `except:` replaced with specific `except Exception:` with meaningful handling
- All imports at top of file (no lazy imports except in `_auto_start_whatsapp`)
- `if __name__ == "__main__"` guard in `main.py` only

### JavaScript (app.js)
- **camelCase** for functions and variables
- Vanilla JS — no framework
- Global state variables for chat management
- Direct DOM manipulation
- Manual SSE streaming via `ReadableStream` reader + JSON chunk parsing
- Markdown rendering via marked.js + highlight.js

### HTML (index.html)
- Single-page application — all UI in one file
- Tailwind CSS utility classes
- Dark mode by default (`class="dark"` on `<html>`)
- Indonesian language for UI text and labels

### CSS (style.css)
- CSS custom properties for color palette (zinc/red tones)
- Glassmorphism effects (`backdrop-filter: blur()`)
- Glow effects via box-shadow
- Custom animations via `@keyframes`
- Google Fonts: Outfit (body) + Fira Code (monospace)

### WhatsApp Bridge (whatsapp/index.js)
- ESM modules (`"type": "module"` in package.json)
- Security whitelist: only authorized phone numbers can interact
- Message deduplication via `sentMessageIds` Set to prevent echo loops
- Auto-reconnect on disconnect
- Inter-service HTTP via axios between Node.js bridge and FastAPI

## Architecture

### Dual-Service Architecture
```
Browser (port 8000) ──SSE/REST──> FastAPI (app/)
WhatsApp (port 8001) ──REST────> FastAPI (app/)
FastAPI ──threaded──> open-interpreter.chat()
```

### Data Flow (Chat Message)
1. User types message in browser textarea
2. `app.js` sends POST /api/chat with {message, chat_id}
3. `app/routes/chat.py` loads chat history into interpreter.messages
4. ThreadPoolExecutor runs interpreter.chat() in background thread
5. Chunks pushed to asyncio.Queue via loop.call_soon_threadsafe
6. SSE generator yields chunks as `data: {json}\n\n`
7. `app.js` processChunk() renders markdown, code windows, terminal output
8. Updated messages saved back to chats.json (atomic write)

### WhatsApp Workflow: Pola Kerja (Remote Claude)
Trigger phrase: "pola kerja" (case-insensitive) via WhatsApp.
1. User sends "oi lakukan pola kerja saya" → workflow activated
2. AI responds: `claude : (Ketik Prompt anda untuk Claude)`
3. User sends their Claude prompt
4. AI executes via SSH (paramiko): `cd $REMOTE_DIR && claude -p 'PROMPT'`
5. AI sends the Claude output back via WhatsApp
- Server config via env vars: `MIDNIGHT_SSH_HOST`, `MIDNIGHT_SSH_USER`, `MIDNIGHT_SSH_PASSWORD`, `MIDNIGHT_SSH_DIR`
- State managed per-sender via `WorkflowManager` class
- `/stop` cancels active workflow

## Important Files for Editing

| Task | File(s) |
|------|---------|
| Backend API changes | `app/routes/*.py` |
| Backend services | `app/services/*.py` |
| Backend config | `app/config.py`, `app/models.py` |
| Backend storage | `app/storage.py` |
| UI layout/styling | `templates/index.html`, `static/css/style.css` |
| Chat logic / streaming | `static/js/app.js` |
| WhatsApp features | `whatsapp/index.js`, `app/routes/whatsapp.py`, `app/services/workflows.py` |
| LLM config defaults | `settings.json`, `app/config.py` |
| Dependencies | `requirements.txt`, `whatsapp/package.json` |
| Tests | `tests/` |
| Project config | `pyproject.toml` |

## Language

The project UI, comments, and documentation are primarily in **Bahasa Indonesia**. Maintain this convention when modifying UI text.

## Platform Notes

- Windows-only: hardcoded paths (`pythonw.exe`), `CREATE_NO_WINDOW`, `taskkill` commands, `.bat` scripts
- No `.env` file — settings live in `settings.json`
- No bundler — all static files served directly by FastAPI
- Portable Node.js bundled in `node_bin/` for WhatsApp bridge
