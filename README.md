# Pink Transcriber CUDA

Fast voice-to-text with NVIDIA GPU acceleration.

~5x faster than realtime on RTX 4060.

## Quick Start

```bash
git clone https://github.com/pink-tools/pink-transcriber-cuda
cd pink-transcriber-cuda
uv sync
uv run pink-transcriber-server
```

First run downloads the model (~3GB).

## Requirements

- Windows or Linux
- NVIDIA GPU with CUDA
- Python 3.10–3.12
- [uv](https://docs.astral.sh/uv/)

**Windows:** Install NVIDIA drivers + CUDA Toolkit

**Linux:** Install NVIDIA drivers (CUDA libs installed automatically)

## Usage

**Start server:**
```bash
uv run pink-transcriber-server
```

**Transcribe:**
```bash
uv run pink-transcriber audio.ogg
```

**Check health:**
```bash
uv run pink-transcriber --health
```

Supports: wav, ogg, mp3, m4a, flac, opus, aiff

## Customization

Adjust format, speed, output and more:
```bash
uv run pink-transcriber --help
```

## License

MIT
