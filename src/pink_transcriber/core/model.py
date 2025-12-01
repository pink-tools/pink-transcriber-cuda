"""
Model loading and transcription logic using faster-whisper.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from pink_transcriber.config import VERBOSE_MODE, get_model_cache_dir, IS_WINDOWS

_model: Optional[any] = None
_device: str = "cuda"
_compute_type: str = "float16"


def load_model() -> None:
    """Load Whisper Large-v3 model with CUDA FP16 support."""
    global _model, _device, _compute_type

    # Set cache directory
    model_cache_dir = get_model_cache_dir()
    model_cache_dir.mkdir(exist_ok=True, parents=True)

    # Configure cache paths
    os.environ['HF_HOME'] = str(model_cache_dir / "huggingface")
    os.environ['XDG_CACHE_HOME'] = str(model_cache_dir)

    # Load CUDA libraries (Linux only - on Windows CUDA is installed system-wide)
    if not IS_WINDOWS:
        try:
            import ctypes
            import nvidia.cudnn, nvidia.cublas
            for m in [nvidia.cudnn, nvidia.cublas]:
                lib_dir = os.path.join(m.__path__[0], "lib")
                for f in os.listdir(lib_dir):
                    if '.so' in f:
                        try:
                            ctypes.CDLL(os.path.join(lib_dir, f), mode=ctypes.RTLD_GLOBAL)
                        except:
                            pass
        except:
            pass

    try:
        from faster_whisper import WhisperModel
        import torch

        if VERBOSE_MODE:
            print("Loading Whisper Large-v3 model with faster-whisper...", flush=True)

        # Check CUDA availability
        if not torch.cuda.is_available():
            _device = "cpu"
            _compute_type = "int8"
            if VERBOSE_MODE:
                print("WARNING: CUDA not available, using CPU", flush=True)
        else:
            _device = "cuda"
            _compute_type = "float16"
            if VERBOSE_MODE:
                gpu_name = torch.cuda.get_device_name(0)
                print(f"✓ GPU: {gpu_name}", flush=True)

        # Load the model on GPU with FP16 precision
        _model = WhisperModel(
            "large-v3",
            device=_device,
            compute_type=_compute_type,
            download_root=str(model_cache_dir),
        )

        if VERBOSE_MODE:
            print(f"✓ Model loaded on {_device.upper()} ({_compute_type.upper()})", flush=True)

    except Exception as e:
        print(f"\nERROR: {e}\n", file=sys.stderr)
        sys.exit(1)


def transcribe(audio_path: str) -> str:
    """Transcribe audio file to text using faster-whisper."""
    if _model is None:
        raise RuntimeError("Model not loaded")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        segments, info = _model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=False,
            language=None,
        )

        # Collect all segments
        text_segments = []
        for segment in segments:
            text_segments.append(segment.text)

        result = " ".join(text_segments).strip()

        if VERBOSE_MODE:
            print(f"  Language: {info.language} ({info.language_probability:.2f})", flush=True)

        return result if result else ""

    except Exception as e:
        raise RuntimeError(f"Transcription failed: {e}")


def get_device() -> str:
    """Get current device name."""
    return f"{_device.upper()} ({_compute_type.upper()})"


def is_loaded() -> bool:
    """Check if model is loaded and ready."""
    return _model is not None
