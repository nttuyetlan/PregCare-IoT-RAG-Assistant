"""
src/tts_service.py — Text-to-Speech Service (Piper TTS)

PURPOSE:
    Wraps Piper TTS for Vietnamese speech synthesis.
    Implements sentence-level streaming to reduce latency.

ARCHITECTURE DECISIONS:
    - Piper TTS: lightweight, offline, supports Vietnamese
    - Streaming at punctuation boundaries (not word-level)
    - Output format: 16kHz mono WAV for speaker playback
    - Sentence buffering reduces TTS calls while maintaining
      low time-to-first-audio
"""

import io
import subprocess
import wave
from pathlib import Path
from typing import Generator, Optional

import numpy as np
from loguru import logger

from src.config import get_settings, PROJECT_ROOT
from src.utils import Timer, split_at_punctuation


class TTSService:
    """
    Vietnamese Text-to-Speech using Piper.

    Supports two modes:
    1. Full synthesis: Convert complete text to audio
    2. Streaming synthesis: Convert text chunks as they arrive
       from the LLM, yielding audio segments at punctuation.
    """

    def __init__(self):
        self._settings = get_settings()
        self._model_path = None
        self._config_path = None
        self._sample_rate = 22050  # Piper default

    def _resolve_model(self):
        """Find Piper model files in the model directory."""
        if self._model_path is not None:
            return

        model_dir = self._settings.abs_piper_path

        if not model_dir.exists():
            raise FileNotFoundError(
                f"Piper model directory not found: {model_dir}"
            )

        # Look for .onnx model file
        onnx_files = list(model_dir.glob("*.onnx"))
        if not onnx_files:
            raise FileNotFoundError(
                f"No .onnx model found in {model_dir}"
            )

        self._model_path = onnx_files[0]

        # Look for config JSON
        config_files = list(model_dir.glob("*.json"))
        if config_files:
            self._config_path = config_files[0]

        logger.info(f"Piper model: {self._model_path}")

    def synthesize(self, text: str) -> bytes:
        """
        Synthesize full text to WAV audio bytes.
        Ưu tiên CLI (ổn định trên ARM64), fallback sang Python API.

        Args:
            text: Vietnamese text to speak

        Returns:
            WAV audio data as bytes
        """
        self._resolve_model()

        if not text.strip():
            return b""

        with Timer("TTS synthesis", log_level="INFO"):
            # Ưu tiên dùng CLI vì Python API trên ARM64 hay lỗi (WAV rỗng 44 bytes)
            audio = self._synthesize_cli(text)
            if audio and len(audio) > 44:
                return self._add_leading_silence(audio)

            # Fallback sang Python API nếu CLI không có
            logger.warning("CLI không tạo được audio, thử Python API...")
            try:
                from piper import PiperVoice

                voice = PiperVoice.load(
                    str(self._model_path),
                    config_path=(
                        str(self._config_path)
                        if self._config_path
                        else None
                    ),
                )

                wav_buffer = io.BytesIO()
                with wave.open(wav_buffer, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(self._sample_rate)
                    voice.synthesize(text, wav_file)

                audio_bytes = wav_buffer.getvalue()
                if len(audio_bytes) > 44:
                    return self._add_leading_silence(audio_bytes)
                    
                logger.error("Python API cũng tạo WAV rỗng!")
                return b""

            except Exception as e:
                logger.error(f"Cả CLI và Python API đều thất bại: {e}")
                return b""

    def _add_leading_silence(self, wav_data: bytes, silence_ms: int = 300) -> bytes:
        """
        Chèn khoảng im lặng vào đầu file WAV.
        Giúp loa/DAC có thời gian khởi động, tránh bị nuốt mất chữ đầu tiên.
        
        Args:
            wav_data: WAV bytes gốc từ TTS
            silence_ms: Độ dài im lặng cần chèn (mặc định 300ms)
        """
        try:
            src = io.BytesIO(wav_data)
            with wave.open(src, "rb") as wf:
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                pcm_data = wf.readframes(wf.getnframes())
            
            # Tạo silence: số frame = framerate * (ms / 1000)
            silence_frames = int(framerate * silence_ms / 1000)
            silence_bytes = b'\x00' * (silence_frames * channels * sampwidth)
            
            # Ghép silence + audio gốc
            dst = io.BytesIO()
            with wave.open(dst, "wb") as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(framerate)
                wf.writeframes(silence_bytes + pcm_data)
            
            return dst.getvalue()
        except Exception as e:
            logger.warning(f"Không thể thêm silence padding: {e}")
            return wav_data  # Trả về nguyên bản nếu lỗi

    def _synthesize_cli(self, text: str) -> bytes:
        """
        Fallback: synthesize using Piper CLI subprocess.

        Used when the piper Python package is not available.
        """
        self._resolve_model()

        import shutil
        import os
        
        # Thử tìm piper trong ~/.local/bin nếu chạy dưới dạng service ngầm
        cmd_path = shutil.which("piper")
        if not cmd_path:
            local_bin = os.path.expanduser("~/.local/bin/piper")
            if os.path.exists(local_bin):
                cmd_path = local_bin
            else:
                cmd_path = "piper" # Fallback

        cmd = [
            cmd_path,
            "--model", str(self._model_path),
            "-f", "-",
        ]

        if self._config_path:
            cmd.extend(["--config", str(self._config_path)])

        try:
            result = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.error(
                    f"Piper CLI error: {result.stderr.decode()}"
                )
                return b""

            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error("Piper CLI timed out")
            return b""
        except FileNotFoundError:
            logger.error("Piper CLI not found in PATH")
            return b""

    def synthesize_stream(
        self, text_chunks: Generator[str, None, None]
    ) -> Generator[bytes, None, None]:
        """
        Stream TTS synthesis from text chunks.

        Receives text chunks from the LLM streaming output
        and yields WAV audio chunks. This enables the speaker
        to start playing while the LLM is still generating.

        Args:
            text_chunks: Generator yielding text segments

        Yields:
            WAV audio bytes for each text segment
        """
        for chunk in text_chunks:
            if chunk.strip():
                audio = self.synthesize(chunk)
                if audio:
                    yield audio

    def get_sample_rate(self) -> int:
        """Return the audio sample rate for playback configuration."""
        return self._sample_rate
