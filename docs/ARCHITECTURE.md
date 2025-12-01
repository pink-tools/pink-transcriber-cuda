# Architecture

CUDA-accelerated voice-to-text server using OpenAI Whisper Large-v3 with client-server architecture over Unix sockets (Linux) or TCP (Windows).

## Directory Structure

```
pink-transcriber-cuda/
├── src/pink_transcriber/
│   ├── __init__.py           # Package version info
│   ├── config.py             # Configuration and platform detection
│   ├── cli/
│   │   ├── __init__.py       # CLI module
│   │   ├── client.py         # Client CLI for transcription requests
│   │   └── server.py         # Server daemon entry point
│   ├── core/
│   │   ├── __init__.py       # Core module
│   │   └── model.py          # Whisper model loading and transcription logic
│   └── daemon/
│       ├── __init__.py       # Daemon module
│       ├── singleton.py      # Single instance enforcement (kills duplicates)
│       └── worker.py         # Async request handler and transcription queue
├── pyproject.toml            # Package config with CUDA dependencies
├── README.md                 # User documentation
└── docs/
    └── ARCHITECTURE.md       # This file
```

## Files

### `src/pink_transcriber/__init__.py`
Package metadata. Exports version string.

### `src/pink_transcriber/config.py`
Platform detection (Windows/Unix) and configuration constants including socket path, TCP port, supported audio formats, verbose mode flag, and model cache directory logic.

### `src/pink_transcriber/cli/client.py`
Client CLI command (`pink-transcriber`) that validates audio files, connects to server socket, sends file path, and receives transcription text.

### `src/pink_transcriber/cli/server.py`
Server daemon entry point (`pink-transcriber-server`) that sets up async server, loads Whisper model, creates transcription worker queue, and handles graceful shutdown.

### `src/pink_transcriber/core/model.py`
Whisper model loading and inference wrapper that loads faster-whisper Large-v3 with CUDA FP16 (fallback to CPU INT8) and handles CUDA library loading on Linux.

### `src/pink_transcriber/daemon/singleton.py`
Single instance enforcement that scans running processes, finds root of process trees, and kills duplicates to prevent port conflicts.

### `src/pink_transcriber/daemon/worker.py`
Async transcription worker that queues requests, processes them sequentially in background executor, handles health checks, and returns results over socket.

## Entry Points

```bash
# Start server daemon
uv run pink-transcriber-server

# Transcribe audio file
uv run pink-transcriber /path/to/audio.ogg

# Health check
uv run pink-transcriber --health
```

## Key Concepts

**Client-Server Architecture** — Server runs as daemon with loaded model in memory. Clients connect via socket, send file path, receive text. Eliminates model loading overhead (~5s → instant).

**Platform-Specific Transport** — Unix domain socket at `/tmp/pink-transcriber.sock` on Linux/macOS, TCP server on `127.0.0.1:19876` on Windows (Windows lacks reliable Unix sockets).

**Singleton Enforcement** — `daemon/singleton.py` ensures only one server instance runs by scanning all processes for project identifiers, climbing to root of process tree (handles wrappers like uv/caffeinate), and killing entire tree.

**Async Queue Processing** — Requests handled via `asyncio.Queue` with single worker task processing transcriptions sequentially (model not thread-safe). Client connections handled concurrently.

**Blocking Operations in Executor** — Model loading and transcription run in `loop.run_in_executor(None, ...)` to avoid blocking async event loop.

**CUDA Library Loading** — Linux version preloads nvidia-cudnn-cu12 and nvidia-cublas-cu12 with `ctypes.CDLL(..., RTLD_GLOBAL)` to make them available to faster-whisper.

**Model Caching** — Model downloaded to `PINK_TRANSCRIBER_MODEL_DIR` env var (if set), `./models/` in package directory (if writable), or `~/.local/share/pink-transcriber/models` (fallback).

**Protocol** — Client sends `/absolute/path/to/audio.ogg\n` for transcription or `HEALTH\n` for status check. Server responds with text, `OK`/`LOADING`, or `ERROR: message\n`. All UTF-8 encoded, newline terminated.

**Graceful Shutdown** — SIGINT/SIGTERM stops accepting connections, sends sentinel to worker queue, waits for current task (2s timeout), closes server, removes socket file.

**Performance** — ~5x faster than realtime on RTX 4060 with FP16 precision (10-second audio transcribed in ~2 seconds). Uses faster-whisper (CTranslate2-based) for speed.
