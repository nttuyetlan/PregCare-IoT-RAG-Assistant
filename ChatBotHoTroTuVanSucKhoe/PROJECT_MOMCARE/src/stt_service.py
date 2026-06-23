"""
src/stt_service.py — Speech-to-Text Service (Faster-Whisper)

PURPOSE:
    Wraps Faster-Whisper for Vietnamese speech recognition.
    Optimized for ARM64 CPU with int8 quantization.

ARCHITECTURE DECISIONS:
    - Faster-Whisper (CTranslate2) over original Whisper for speed
    - Model size 'small' (not tiny) for Vietnamese medical accuracy
    - int8 compute type for ARM64 optimization
    - Multi-threaded CPU inference
    - Language forced to Vietnamese (no auto-detect overhead)
"""

from pathlib import Path
from typing import Optional

from loguru import logger

from src.config import get_settings, PROJECT_ROOT
from src.utils import Timer


class STTService:
    """
    Vietnamese Speech-to-Text using Faster-Whisper.

    Optimized for Orange Pi 5 ARM64:
    - compute_type="int8" via CTranslate2
    - Multi-threaded CPU inference
    - Target latency: < 1.5s for typical utterances
    """

    def __init__(self):
        self._model = None
        self._settings = get_settings()

    def _load_model(self):
        """Lazy-load Whisper model to avoid import-time memory usage."""
        if self._model is not None:
            return

        from faster_whisper import WhisperModel

        model_path = self._settings.abs_whisper_path

        # Use local model if available, else download
        if model_path.exists():
            model_source = str(model_path)
            logger.info(f"Loading local Whisper model: {model_path}")
        else:
            model_source = "small"
            logger.warning(
                f"Local model not found at {model_path}. "
                f"Downloading 'small' model..."
            )

        with Timer("Whisper model loading", log_level="INFO"):
            self._model = WhisperModel(
                model_source,
                device="cpu",
                compute_type=self._settings.whisper_compute_type,
                cpu_threads=self._settings.whisper_num_threads,
            )

        logger.info(
            f"Whisper loaded: compute={self._settings.whisper_compute_type}, "
            f"threads={self._settings.whisper_num_threads}"
        )

    def transcribe(
        self,
        audio_path: str | Path,
        language: str = "vi",
    ) -> str:
        """
        Transcribe an audio file to Vietnamese text.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            language: Language code (forced to 'vi' for accuracy)

        Returns:
            Transcribed text string
        """
        self._load_model()

        with Timer("STT transcription", log_level="INFO"):
            segments, info = self._model.transcribe(
                str(audio_path),
                language=language,
                beam_size=5,           # Tăng lên 5 để so sánh ngữ cảnh tốt hơn
                best_of=5,             # Tăng lên 5 để chọn kết quả mượt nhất
                vad_filter=True,       # Sử dụng Silero VAD để lọc tiếng ồn
                vad_parameters=dict(
                    min_silence_duration_ms=1200, # Cho phép ngập ngừng 1.2s
                ),
            )

            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

        full_text = " ".join(text_parts)

        logger.bind(conversation=True).info(
            f"STT | lang={info.language} | prob={info.language_probability:.2f} | "
            f"text='{full_text[:80]}...'"
        )

        return full_text

    def transcribe_audio_data(
        self,
        audio_data,
        language: str = "vi",
    ) -> str:
        """
        Transcribe raw audio data (numpy array or bytes).

        Used by the pipecat pipeline for real-time transcription.

        Args:
            audio_data: Audio as numpy array (float32, 16kHz mono)
            language: Language code

        Returns:
            Transcribed text
        """
        self._load_model()

        with Timer("STT transcription (buffer)", log_level="INFO"):
            segments, info = self._model.transcribe(
                audio_data,
                language=language,
                beam_size=5,
                best_of=5,
                temperature=[0.0, 0.2, 0.4],
                condition_on_previous_text=False,
                vad_filter=False,
            )

            text_parts = [seg.text.strip() for seg in segments]

        full_text = " ".join(text_parts)

        logger.debug(f"STT buffer: '{full_text[:80]}...'")
        return full_text
