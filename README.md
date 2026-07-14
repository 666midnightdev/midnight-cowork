# Midnight Cowork

Local AI desktop assistant with ChatGPT-style web UI, WhatsApp integration, and Telegram bot control. Built for Windows with FastAPI backend and vanilla JS frontend.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows-0078d4?logo=windows)

## Features

- **AI Chat Interface** — ChatGPT-style UI with real-time SSE streaming, code blocks with syntax highlighting, and terminal output display
- **Multi-Session Chat** — Create, switch, and manage multiple conversation sessions with persistent history
- **WhatsApp Integration** — Control the assistant via WhatsApp using Baileys (QR code pairing)
- **Telegram Bot** — Full Telegram Bot integration with long-polling (no webhook needed)
- **Auto-Run Mode** — Execute code automatically without confirmation prompts
- **Desktop Automation** — pyautogui-powered GUI automation: open WSL, SSH to remote servers, run Claude CLI
- **Remote Claude Workflow** — Send "pola kerja" via WhatsApp/Telegram to execute Claude CLI on a remote server via SSH
- **Flexible LLM Config** — Support for GPT-4o, Claude, Ollama, Groq, and any LiteLLM-compatible model
- **Dark Theme UI** — Premium "Midnight Red" theme with glassmorphism effects and micro-animations
- **Background Server** — Runs silently via `pythonw.exe` (no terminal window)

## Project Structure

```
open_interpreter_ui/
├── main.py                  # Entry point
├── app/                     # Backend package
│   ├── __init__.py          # App factory + auto-start
│   ├── config.py            # Paths, constants, interpreter import
│   ├── models.py            # Pydantic request/response models
│   ├── storage.py           # JSON file ops with atomic writes
│   ├── services/
│   │   ├── interpreter.py   # Interpreter config + provider setup
│   │   ├── telegram.py      # Telegram state management
│   │   ├── whatsapp.py      # WhatsApp state management
│   │   └── workflows.py     # GUI automation + SSH remote execution
│   └── routes/
│       ├── chat.py          # CRUD /api/chats, POST /api/chat (SSE)
│       ├── settings.py      # GET/POST /api/settings
│       ├── system.py        # GET /, GET /api/status, POST /api/shutdown
│       ├── telegram.py      # Telegram bot endpoints
│       └── whatsapp.py      # WhatsApp integration endpoints
├── templates/
│   └── index.html           # Single-page frontend (Midnight Red theme)
├── static/
│   ├── css/style.css        # Custom CSS (glassmorphism, animations)
│   └── js/app.js            # Frontend JS (SSE streaming, chat logic)
├── whatsapp/                # WhatsApp Baileys bridge
│   ├── index.js             # Node.js bridge (ESM)
│   ├── package.json         # Node dependencies
│   └── auth_info/           # WhatsApp session (auto-generated, gitignored)
├── tests/                   # Automated tests (15 tests)
├── start.bat                # Launch server + open browser
├── stop.bat                 # Kill server
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Project config (ruff, mypy, pytest)
└── .gitignore
```

## Requirements

- **Windows 10/11** (required for pyautogui automation and .bat scripts)
- **Python 3.10+**
- **Node.js** (portable version bundled in `node_bin/` via `whatsapp_setup.py`)
- **Open Interpreter** (`pip install open-interpreter`)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

Edit `settings.json` and set your LLM provider:

```json
{
  "model": "groq/llama-3.3-70b-versatile",
  "api_key": "your-api-key-here",
  "auto_run": true
}
```

Or configure via the web UI after starting the server.

### 3. Start the Server

```bash
# Double-click start.bat, or:
py main.py
# Server runs at http://127.0.0.1:8000
```

### 4. Stop the Server

```bash
# Double-click stop.bat, or:
# Click "Matikan Server" in the web UI sidebar
```

## WhatsApp Integration

WhatsApp integration uses [Baileys](https://github.com/WhiskeySockets/Baileys) library via a Node.js bridge microservice.

### Setup

```bash
# First time only - downloads portable Node.js + installs dependencies
py whatsapp_setup.py
```

### Connect

1. Open the web UI → click **Integrasi WhatsApp** in the sidebar
2. Scan the QR code with your phone (WhatsApp → Linked Devices → Link a Device)
3. Once connected, send messages to the bot from any whitelisted number

### Commands

| Command | Description |
|---------|-------------|
| `/new` | Start a new conversation session |
| `/stop` | Stop the current session |
| `/help` | Show command list |
| `pola kerja` | Activate remote Claude workflow |
| *(any text)* | Execute via Open Interpreter |

## Telegram Bot Integration

Telegram integration uses long-polling — no webhook or public URL needed.

### Setup

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Get the bot token
3. Open the web UI → click **Integrasi Telegram** → paste token → click Hubungkan

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message |
| `/new` | Start a new conversation |
| `/stop` | Stop current session |
| `/help` | Show command list |
| `pola kerja` | Activate remote Claude workflow |
| *(any text)* | Execute via Open Interpreter |

## Remote Claude Workflow ("Pola Kerja")

This feature opens WSL, SSHs into a remote server, and executes Claude CLI via GUI automation (pyautogui).

### Configuration

Set environment variables before starting the server:

```bash
set MIDNIGHT_SSH_HOST=your-server-ip
set MIDNIGHT_SSH_USER=root
set MIDNIGHT_SSH_PASSWORD=your-password
set MIDNIGHT_SSH_DIR=/path/to/your/project
```

Or edit the defaults in `app/services/workflows.py`.

### Usage

1. Send `pola kerja` via WhatsApp or Telegram
2. Bot responds: `claude : (Ketik Prompt anda untuk Claude)`
3. Send your Claude prompt
4. Bot executes on the remote server and returns the output

## Supported LLM Providers

| Provider | Model Example | Notes |
|----------|--------------|-------|
| Groq | `groq/llama-3.3-70b-versatile` | Free tier available |
| OpenAI | `gpt-4o` | Requires API key |
| Anthropic | `claude-3-5-sonnet` | Requires API key |
| Ollama | `ollama/llama3` | Local, no API key |
| LiteLLM | Any [supported model](https://docs.litellm.ai/docs/providers) | Via LiteLLM proxy |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve frontend |
| `GET` | `/api/status` | Server status |
| `POST` | `/api/shutdown` | Shutdown server |
| `GET` | `/api/chats` | List all chats |
| `POST` | `/api/chats` | Create new chat |
| `DELETE` | `/api/chats/{id}` | Delete a chat |
| `POST` | `/api/chat` | Send message (SSE stream) |
| `GET` | `/api/settings` | Get settings |
| `POST` | `/api/settings` | Update settings |
| `GET` | `/api/whatsapp/status` | WhatsApp connection status |
| `POST` | `/api/whatsapp/start` | Start WhatsApp bridge |
| `POST` | `/api/whatsapp/stop` | Stop WhatsApp bridge |
| `GET` | `/api/telegram/status` | Telegram bot status |
| `POST` | `/api/telegram/start` | Start Telegram bot |
| `POST` | `/api/telegram/stop` | Stop Telegram bot |

## Testing

```bash
pip install pytest pytest-asyncio httpx
py -m pytest tests/ -v
```

15 automated tests covering routes and storage.

## Tech Stack

- **Backend**: Python, FastAPI, Uvicorn, open-interpreter, pyautogui, paramiko, httpx
- **Frontend**: HTML, Tailwind CSS (CDN), vanilla JavaScript, Marked.js, Highlight.js
- **WhatsApp**: Node.js, @whiskeysockets/baileys, Express, Axios
- **Storage**: JSON files with atomic writes (no database)

## License

MIT
