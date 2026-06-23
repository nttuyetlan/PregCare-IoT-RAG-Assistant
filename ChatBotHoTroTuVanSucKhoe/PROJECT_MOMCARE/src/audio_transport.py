"""
src/audio_transport.py — Hardware Audio Transport cho Orange Pi 5

PURPOSE:
    Quản lý luồng âm thanh phần cứng (PyAudio) cho pipeline giọng nói.
    Hỗ trợ es8388 sound card trên Orange Pi 5 (hw:2,0) và USB Audio.
    Cung cấp interface thống nhất cho thu âm (record) và phát âm (play).

ARCHITECTURE DECISIONS:
    - PyAudio cho giao tiếp ALSA trực tiếp (không qua PulseAudio)
    - Device index cấu hình qua .env (AUDIO_INPUT_DEVICE_INDEX)
    - 16kHz mono cho STT (Faster-Whisper yêu cầu)
    - 22050Hz mono cho TTS playback (Piper output)
    - Hỗ trợ Push-to-talk thông qua tham số stop_condition
"""

import io
import os
import sys
import time
import wave
import tempfile
import threading
import ctypes
import contextlib
from pathlib import Path
from typing import Optional, Callable

import numpy as np
from loguru import logger

from src.config import get_settings, PROJECT_ROOT


# ── Audio Constants ──────────────────────────────
STT_SAMPLE_RATE = 16000      # Faster-Whisper yêu cầu 16kHz
STT_CHANNELS = 1             # Mono
STT_FORMAT_BITS = 16         # 16-bit PCM (paInt16)
STT_CHUNK_SIZE = 1024        # Frames per buffer

TTS_SAMPLE_RATE = 22050      # Piper TTS output mặc định
TTS_CHANNELS = 1
FALLBACK_SAMPLE_RATES = (16000, 48000, 44100, 32000, 24000, 22050, 11025, 8000)


class AudioTransport:
    """
    Hardware audio transport cho Orange Pi 5.
    """

    def __init__(
        self,
        input_device_index: Optional[int] = None,
        output_device_index: Optional[int] = None,
    ):
        self._settings = get_settings()
        self._pyaudio = None
        self._is_recording = False
        self._playback_lock = threading.Lock()

        self._input_device_index = input_device_index
        self._output_device_index = output_device_index

        if self._input_device_index is None:
            self._input_device_index = self._settings.audio_input_device_index
        if self._output_device_index is None:
            self._output_device_index = self._settings.audio_output_device_index

        if self._input_device_index == -1:
            self._input_device_index = None
        if self._output_device_index == -1:
            self._output_device_index = None

        self._input_sample_rate: Optional[int] = None
        self._output_sample_rate: Optional[int] = None

    @contextlib.contextmanager
    def _suppress_alsa_warnings(self):
        asound = None
        handler = None
        try:
            asound = ctypes.cdll.LoadLibrary("libasound.so.2")
            ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(
                None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                ctypes.c_int, ctypes.c_char_p,
            )
            def _alsa_noop(filename, line, function, err, fmt):
                return
            handler = ERROR_HANDLER_FUNC(_alsa_noop)
            asound.snd_lib_error_set_handler(handler)
            yield
        except Exception:
            yield
        finally:
            if asound is not None:
                try:
                    asound.snd_lib_error_set_handler(None)
                except Exception:
                    pass

    def _get_pyaudio(self):
        if self._pyaudio is None:
            import pyaudio
            with self._suppress_alsa_warnings():
                self._pyaudio = pyaudio.PyAudio()

            if self._input_device_index is not None:
                try:
                    info = self._pyaudio.get_device_info_by_index(self._input_device_index)
                    logger.info(f"🎤 Audio Input: Index {self._input_device_index} — {info['name']}")
                except Exception:
                    logger.warning(f"🎤 Audio Input Index {self._input_device_index} không hợp lệ, dùng default")
                    self._input_device_index = None
            else:
                logger.info("🎤 Audio Input: default system device")

            if self._output_device_index is not None:
                try:
                    info = self._pyaudio.get_device_info_by_index(self._output_device_index)
                    logger.info(f"🔊 Audio Output: Index {self._output_device_index} — {info['name']}")
                except Exception:
                    if self._input_device_index is not None:
                        logger.warning(f"🔊 Audio Output Index {self._output_device_index} không hợp lệ, fallback sang Input Index {self._input_device_index}")
                        self._output_device_index = self._input_device_index
                    else:
                        logger.warning(f"🔊 Audio Output Index {self._output_device_index} không hợp lệ, dùng default")
                        self._output_device_index = None
            else:
                logger.info("🔊 Audio Output: default system device")

        return self._pyaudio

    def _candidate_rates(self, preferred_rate: int):
        rates = [preferred_rate]
        for r in FALLBACK_SAMPLE_RATES:
            if r not in rates:
                rates.append(r)
        return rates

    def _resolve_input_sample_rate(self, pa, channels: int = STT_CHANNELS) -> int:
        if self._input_sample_rate is not None:
            return self._input_sample_rate

        for rate in self._candidate_rates(STT_SAMPLE_RATE):
            try:
                with self._suppress_alsa_warnings():
                    supported = pa.is_format_supported(
                        rate,
                        input_device=self._input_device_index,
                        input_channels=channels,
                        input_format=pa.get_format_from_width(2),
                    )
                if supported:
                    self._input_sample_rate = int(rate)
                    if rate != STT_SAMPLE_RATE:
                        logger.warning(f"Mic không hỗ trợ {STT_SAMPLE_RATE}Hz, fallback sang {rate}Hz")
                    else:
                        logger.info(f"Mic sample rate: {rate}Hz")
                    return self._input_sample_rate
            except Exception:
                continue

        self._input_sample_rate = STT_SAMPLE_RATE
        logger.warning(f"Không dò được sample rate tương thích, thử dùng mặc định {STT_SAMPLE_RATE}Hz")
        return self._input_sample_rate

    def _resolve_output_sample_rate(self, pa, preferred_rate: int, channels: int) -> int:
        for rate in self._candidate_rates(preferred_rate):
            try:
                with self._suppress_alsa_warnings():
                    supported = pa.is_format_supported(
                        rate,
                        output_device=self._output_device_index,
                        output_channels=channels,
                        output_format=pa.get_format_from_width(2),
                    )
                if supported:
                    if rate != preferred_rate:
                        logger.warning(f"Loa không hỗ trợ {preferred_rate}Hz, fallback sang {rate}Hz")
                    return int(rate)
            except Exception:
                continue
        return int(preferred_rate)

    @staticmethod
    def _resample_int16(audio_int16: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        if src_rate == dst_rate or audio_int16.size == 0:
            return audio_int16
        try:
            import audioop
            # Dùng thư viện audioop (viết bằng C) để resample chất lượng cao
            raw_bytes = audio_int16.tobytes()
            resampled_bytes, _ = audioop.ratecv(raw_bytes, 2, 1, src_rate, dst_rate, None)
            return np.frombuffer(resampled_bytes, dtype=np.int16)
        except ImportError:
            # Fallback nếu dùng Python 3.13+ (audioop bị loại bỏ)
            src = audio_int16.astype(np.float32)
            src_len = src.shape[0]
            dst_len = max(1, int(round(src_len * float(dst_rate) / float(src_rate))))
            src_x = np.linspace(0.0, 1.0, num=src_len, endpoint=False)
            dst_x = np.linspace(0.0, 1.0, num=dst_len, endpoint=False)
            dst = np.interp(dst_x, src_x, src)
            return np.clip(dst, -32768, 32767).astype(np.int16)

    # ── Recording (Mic → WAV) ─────────────────────

    def record_to_file(
        self,
        duration: float = 10.0,
        silence_timeout: float = 2.5,
        silence_threshold: int = 500,
        output_dir: Optional[Path] = None,
        stop_condition: Optional[Callable[[], bool]] = None,
    ) -> str:
        """
        Thu âm từ mic và lưu thành file WAV.
        Hỗ trợ ngắt thu âm sớm bằng nút cứng (Push-to-Talk) thông qua stop_condition.
        """
        import pyaudio
        import subprocess
        import re

        pa = self._get_pyaudio()
        input_rate = self._resolve_input_sample_rate(pa)

        if output_dir is None:
            output_dir = PROJECT_ROOT / "logs"
        output_dir.mkdir(parents=True, exist_ok=True)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=str(output_dir))
        tmp.close()

        stream = None
        arecord_proc = None
        
        try:
            with self._suppress_alsa_warnings():
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=STT_CHANNELS,
                    rate=input_rate,
                    input=True,
                    input_device_index=self._input_device_index,
                    frames_per_buffer=STT_CHUNK_SIZE,
                )
            logger.debug(f"Recording started with PyAudio | max_duration={duration}s")
        except Exception as e:
            logger.warning(f"PyAudio mic failed: {e}. Falling back to arecord...")
            alsa_device = "default"
            if self._input_device_index is not None:
                try:
                    info = pa.get_device_info_by_index(self._input_device_index)
                    match = re.search(r'(hw:\d+,\d+)', info.get("name", ""))
                    if match:
                        alsa_device = match.group(1).replace("hw:", "plughw:")
                except Exception:
                    pass
            
            input_rate = STT_SAMPLE_RATE 
            cmd = [
                "arecord", "-D", alsa_device,
                "-c", str(STT_CHANNELS),
                "-r", str(input_rate),
                "-f", "S16_LE", "-t", "raw"
            ]
            arecord_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            logger.debug(f"Recording started with arecord ({alsa_device})")

        frames = []
        silence_frames = 0
        max_silence_frames = int(silence_timeout * input_rate / STT_CHUNK_SIZE)
        max_total_frames = int(duration * input_rate / STT_CHUNK_SIZE)
        chunk_bytes = STT_CHUNK_SIZE * 2 

        self._is_recording = True
        try:
            for _ in range(max_total_frames):
                # 1. KIỂM TRA NÚT NHẤN PUSH-TO-TALK
                if stop_condition is not None and stop_condition():
                    logger.debug("Stop condition met (Button released).")
                    break

                if not self._is_recording:
                    break
                
                # 2. ĐỌC DỮ LIỆU ÂM THANH
                if stream:
                    data = stream.read(STT_CHUNK_SIZE, exception_on_overflow=False)
                elif arecord_proc:
                    data = arecord_proc.stdout.read(chunk_bytes)
                    if not data or len(data) < chunk_bytes:
                        break
                else:
                    break

                frames.append(data)

                # 3. KIỂM TRA IM LẶNG (VAD cơ bản - có thể bỏ qua nếu dùng nút nhấn)
                # Nếu có dùng nút nhấn (stop_condition != None), ta có thể lờ đi khoảng lặng
                if stop_condition is None:
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    amplitude = np.abs(audio_data).mean()

                    if amplitude < silence_threshold:
                        silence_frames += 1
                        if silence_frames >= max_silence_frames and len(frames) > 10:
                            logger.debug(f"Silence detected after {len(frames)} frames, stopping")
                            break
                    else:
                        silence_frames = 0

        finally:
            self._is_recording = False
            if stream:
                stream.stop_stream()
                stream.close()
            if arecord_proc:
                arecord_proc.terminate()
                arecord_proc.wait()

        raw = b"".join(frames)
        audio_int16 = np.frombuffer(raw, dtype=np.int16)
        if input_rate != STT_SAMPLE_RATE:
            audio_int16 = self._resample_int16(audio_int16, input_rate, STT_SAMPLE_RATE)

        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(STT_CHANNELS)
            wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
            wf.setframerate(STT_SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

        logger.debug(f"Recording saved: {tmp.name} ({len(frames)} frames)")
        return tmp.name

    def record_to_buffer(
        self,
        duration: float = 10.0,
        silence_timeout: float = 2.5,
        silence_threshold: int = 500,
        stop_condition: Optional[Callable[[], bool]] = None,
    ) -> np.ndarray:
        """
        Thu âm từ mic và trả về numpy array. Hỗ trợ stop_condition (Push-to-Talk).
        """
        import pyaudio
        pa = self._get_pyaudio()
        input_rate = self._resolve_input_sample_rate(pa)

        with self._suppress_alsa_warnings():
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=STT_CHANNELS,
                rate=input_rate,
                input=True,
                input_device_index=self._input_device_index,
                frames_per_buffer=STT_CHUNK_SIZE,
            )

        frames = []
        silence_frames = 0
        max_silence_frames = int(silence_timeout * input_rate / STT_CHUNK_SIZE)
        max_total_frames = int(duration * input_rate / STT_CHUNK_SIZE)

        self._is_recording = True
        try:
            for _ in range(max_total_frames):
                if stop_condition is not None and stop_condition():
                    break
                if not self._is_recording:
                    break

                data = stream.read(STT_CHUNK_SIZE, exception_on_overflow=False)
                frames.append(data)

                if stop_condition is None:
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    amplitude = np.abs(audio_data).mean()

                    if amplitude < silence_threshold:
                        silence_frames += 1
                        if silence_frames >= max_silence_frames and len(frames) > 10:
                            break
                    else:
                        silence_frames = 0
        finally:
            self._is_recording = False
            stream.stop_stream()
            stream.close()

        raw = b"".join(frames)
        audio_int16 = np.frombuffer(raw, dtype=np.int16)
        if input_rate != STT_SAMPLE_RATE:
            audio_int16 = self._resample_int16(audio_int16, input_rate, STT_SAMPLE_RATE)
        audio = audio_int16.astype(np.float32) / 32768.0
        return audio

    def stop_recording(self):
        self._is_recording = False

    # ── Playback (WAV bytes → Speaker) ────────────

    def play_wav_bytes(self, wav_bytes: bytes):
        if not wav_bytes:
            return
        with self._playback_lock:
            self._play_wav_internal(wav_bytes)

    def play_wav_bytes_async(self, wav_bytes: bytes):
        if not wav_bytes:
            return
        t = threading.Thread(target=self.play_wav_bytes, args=(wav_bytes,), daemon=True)
        t.start()
        return t

    def play_wav_file(self, file_path: str):
        with open(file_path, "rb") as f:
            wav_bytes = f.read()
        self.play_wav_bytes(wav_bytes)

    def _play_wav_internal(self, wav_bytes: bytes):
        import subprocess
        import tempfile
        import os
        import re
        try:
            alsa_device = "default"
            if self._output_device_index is not None:
                import pyaudio
                pa = self._get_pyaudio()
                try:
                    info = pa.get_device_info_by_index(self._output_device_index)
                    match = re.search(r'(hw:\d+,\d+)', info.get("name", ""))
                    if match:
                        alsa_device = match.group(1).replace("hw:", "plughw:")
                except Exception:
                    pass
            
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(wav_bytes)
            tmp.close()
            
            cmd = ["aplay"]
            if alsa_device != "default":
                cmd.extend(["-D", alsa_device])
            cmd.append(tmp.name)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"aplay failed (code {result.returncode}). Stderr: {result.stderr}")
            os.remove(tmp.name)
            
        except Exception as e:
            logger.error(f"Playback error: {e}")

    def play_mp3_file(self, file_path: str):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
        except Exception as e:
            logger.error(f"MP3 playback error: {e}")

    # ── Cleanup ───────────────────────────────────

    def close(self):
        if self._pyaudio is not None:
            self._pyaudio.terminate()
            self._pyaudio = None
            logger.debug("AudioTransport closed")

    def __del__(self):
        self.close()