#!/usr/bin/env python3
"""
Pink Transcriber CLI Client
Connects to pink-transcriber server and requests transcription.
"""

from __future__ import annotations

import argparse
import os
import sys
import socket
from pathlib import Path

from pink_transcriber import __version__
from pink_transcriber.config import (
    SUPPORTED_AUDIO_FORMATS, SOCKET_PATH, IS_WINDOWS, TCP_HOST, TCP_PORT
)


def validate_audio_file(file_path: str) -> None:
    """Validate audio file before sending to server."""
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(file_path):
        print(f"ERROR: Not a file: {file_path}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_AUDIO_FORMATS:
        print(f"ERROR: Unsupported format: {ext}", file=sys.stderr)
        supported_list = ', '.join(sorted(SUPPORTED_AUDIO_FORMATS))
        print(f"Supported formats: {supported_list}", file=sys.stderr)
        sys.exit(1)


def connect_to_server() -> socket.socket:
    """Create and connect socket to server (platform-specific)."""
    if IS_WINDOWS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((TCP_HOST, TCP_PORT))
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(SOCKET_PATH))
    return sock


def transcribe(audio_path: str) -> str:
    """Send audio file to server and receive transcription."""
    sock = connect_to_server()

    try:
        # Send audio path
        sock.sendall(audio_path.encode() + b'\n')

        # Receive transcription result
        response = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if response.endswith(b'\n'):
                break

        text = response.decode().strip()

        if text.startswith("ERROR:"):
            raise RuntimeError(text[7:])

        return text

    finally:
        sock.close()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='pink-transcriber',
        description='Voice transcription using faster-whisper',
        epilog='Supported formats: ' + ', '.join(sorted(SUPPORTED_AUDIO_FORMATS))
    )

    parser.add_argument(
        'audio_file',
        nargs='?',
        help='Audio file to transcribe'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        '--health',
        action='store_true',
        help='Check if transcription server is running'
    )

    args = parser.parse_args()

    # Health check
    if args.health:
        # On Unix, check socket file exists first
        if not IS_WINDOWS and SOCKET_PATH and not SOCKET_PATH.exists():
            print("ERROR: Server not running (socket not found)", file=sys.stderr)
            sys.exit(1)

        try:
            sock = connect_to_server()
            sock.settimeout(2)

            # Send HEALTH command
            sock.sendall(b"HEALTH\n")

            # Receive response
            response = sock.recv(1024).decode().strip()
            sock.close()

            if response == "OK":
                print("OK")
                sys.exit(0)
            elif response == "LOADING":
                print("ERROR: Model is loading", file=sys.stderr)
                sys.exit(1)
            else:
                print(f"ERROR: Unexpected response: {response}", file=sys.stderr)
                sys.exit(1)

        except socket.timeout:
            print("ERROR: Server timeout", file=sys.stderr)
            sys.exit(1)
        except ConnectionRefusedError:
            print("ERROR: Server not running", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Server not responding: {e}", file=sys.stderr)
            sys.exit(1)

    # Require audio file if not health check
    if not args.audio_file:
        parser.print_help()
        sys.exit(1)

    # Convert to absolute path
    audio_path = os.path.abspath(args.audio_file)

    # Validate audio file
    validate_audio_file(audio_path)

    # On Unix, check socket file exists
    if not IS_WINDOWS and SOCKET_PATH and not SOCKET_PATH.exists():
        print("ERROR: Server not running", file=sys.stderr)
        sys.exit(1)

    try:
        text = transcribe(audio_path)
        print(text)
    except ConnectionRefusedError:
        print("ERROR: Server not running", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
