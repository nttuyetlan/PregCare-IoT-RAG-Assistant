"""
src/cli_voice_app.py — Giao diện dòng lệnh hỗ trợ giọng nói cho Mầm Nhỏ

PURPOSE:
    Cho phép kiểm thử chatbot bằng GIỌNG NÓI trực tiếp qua terminal.
    Tích hợp nút nhấn vật lý (Push-to-Talk) qua chân GPIO trên Orange Pi 5.
"""

import sys
import tempfile
import time
import argparse
from pathlib import Path
import os

# Ngăn chặn lỗi Segmentation Fault
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger

try:
    import torch
    torch.set_num_threads(1)
except ImportError:
    pass

# Hỗ trợ trực tiếp Sysfs GPIO cho Orange Pi 5 (Rockchip RK3588)
# Chân 15 vật lý = GPIO4_C5 = 149
SYSFS_PIN = 149
HAS_GPIO = False

def init_sysfs_gpio(pin):
    try:
        gpio_path = f"/sys/class/gpio/gpio{pin}"
        if not os.path.exists(gpio_path):
            with open("/sys/class/gpio/export", "w") as f:
                f.write(str(pin))
            time.sleep(0.2)  # Đợi OS cấp quyền
        
        with open(f"{gpio_path}/direction", "w") as f:
            f.write("in")
        return True
    except Exception as e:
        print(f"⚠️ Lỗi khởi tạo Sysfs GPIO: {e}")
        return False

def read_sysfs_gpio(pin):
    try:
        with open(f"/sys/class/gpio/gpio{pin}/value", "r") as f:
            return f.read().strip() == "1"
    except Exception:
        return True # Default to HIGH if error

# Tắt log quá mức của RAG
os.environ["LOGURU_LEVEL"] = "WARNING"

from src.config import get_settings, setup_logging, PROJECT_ROOT as PROJ_ROOT
from src.conversation_memory import ConversationMemory
from src.rag_engine import RAGEngine
from src.audio_transport import AudioTransport
from src.intent_classifier import IntentType
from src.youtube_service import YouTubeService

# CẤU HÌNH CHÂN NÚT NHẤN (Theo chuẩn Sysfs của OPi 5)
BUTTON_PIN = SYSFS_PIN

# ──────────────────────────────────────────────
# STT Backends
# ──────────────────────────────────────────────
def stt_google(audio_path: str) -> str:
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True

    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio, language="vi-VN")
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print(f"  ⚠️ Google STT lỗi mạng: {e}")
        return ""

def stt_whisper(audio_path: str) -> str:
    from src.stt_service import STTService
    stt = STTService()
    return stt.transcribe(audio_path, language="vi")

# ──────────────────────────────────────────────
# TTS Backends
# ──────────────────────────────────────────────
def tts_gtts(text: str, audio_transport: AudioTransport) -> None:
    if not text:
        return
    try:
        from gtts import gTTS
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        tts = gTTS(text=text, lang="vi", slow=False)
        tts.save(tmp.name)
        audio_transport.play_mp3_file(tmp.name)
        os.remove(tmp.name)
    except Exception as e:
        print(f"  [Lỗi gTTS: {e}]")

def tts_piper(text: str, audio_transport: AudioTransport) -> None:
    if not text:
        return
    try:
        from src.tts_service import TTSService
        tts = TTSService()
        wav_bytes = tts.synthesize(text)
        if wav_bytes:
            audio_transport.play_wav_bytes(wav_bytes)
    except Exception as e:
        print(f"  [Lỗi Piper TTS: {e}]")

# ──────────────────────────────────────────────
# Main Application
# ──────────────────────────────────────────────
def main():
    global HAS_GPIO
    
    parser = argparse.ArgumentParser(description="Mầm Nhỏ — CLI Voice Assistant")
    parser.add_argument("--offline", action="store_true", help="Chế độ offline (Faster-Whisper + Piper TTS)")
    parser.add_argument("--input-device", type=int, default=None, help="PyAudio input device index")
    parser.add_argument("--output-device", type=int, default=None, help="PyAudio output device index")
    args = parser.parse_args()

    settings = get_settings()
    is_offline = args.offline
    stt_func = stt_whisper if is_offline else stt_google
    mode_name = "Offline (Whisper + Piper)" if is_offline else "Online (Google STT + gTTS)"

    audio = AudioTransport(
        input_device_index=args.input_device,
        output_device_index=args.output_device,
    )

    def speak(text):
        print(f"\n🔊 Mầm Nhỏ: {text}\n")
        if is_offline:
            tts_piper(text, audio)
        else:
            tts_gtts(text, audio)

    memory = ConversationMemory()
    rag = RAGEngine()
    youtube = YouTubeService()

    print("=" * 60)
    print("🌱 MẦM NHỎ — TRỢ LÝ SẢN KHOA AI (Push-To-Talk Mode)")
    print(f"📡 Chế độ: {mode_name}")
    print("=" * 60)
    print("Hệ thống đang tải mô hình, vui lòng đợi giây lát...\n")

    memory.add_user_message("Xin chào")
    memory.add_assistant_message("Chào Mẹ, em là Mầm Nhỏ, trợ lý sản khoa AI. Em rất vui được hỗ trợ Mẹ ạ.")

    # ── KHỞI TẠO NÚT NHẤN ──
    HAS_GPIO = init_sysfs_gpio(BUTTON_PIN)
    if HAS_GPIO:
        print(f"🟢 Đã kích hoạt Nút bấm vật lý (Sysfs Pin {BUTTON_PIN}).")
    else:
        print("❌ Lỗi khởi tạo nút bấm GPIO qua Sysfs. Đảm bảo chạy với quyền root!")

    def wait_for_button_press():
        if not HAS_GPIO:
            try:
                input("\n👉 [Không có GPIO] Nhấn phím ENTER để thu âm...")
            except EOFError:
                print("\n⚠️ [LỖI KHUẤT TẤT] Không tìm thấy TTY và nút bấm GPIO lỗi.")
                print("Hệ thống sẽ bị treo ở đây để tránh ghi âm liên tục. Vui lòng cấp quyền GPIO:")
                print("👉 sudo usermod -aG gpio $USER")
                print("Sau đó khởi động lại thiết bị hoặc dịch vụ.")
                while True:
                    time.sleep(3600)
            return
        print("\n👉 Đang chờ Mẹ nhấn và GIỮ NÚT để nói...")
        while read_sysfs_gpio(BUTTON_PIN):
            time.sleep(0.05)

    def is_button_released():
        if not HAS_GPIO:
            return False # Luôn thu âm theo duration nếu dùng PC
        return read_sysfs_gpio(BUTTON_PIN)

    print("\n✅ Đã sẵn sàng!")
    print("👉 Đang chờ nhấn nút lần đầu tiên để khởi động...")
    
    if HAS_GPIO:
        wait_for_button_press()
        # Đợi người dùng nhả nút ra sau cú click đầu tiên
        while not is_button_released():
            time.sleep(0.05)

    speak("Chào Mẹ, Mầm Nhỏ đã sẵn sàng. Hãy nhấn giữ nút để nói chuyện nhé.")

    try:
        while True:
            print("\n" + "=" * 40)
            text_to_process = ""

            # 1. Block hệ thống cho đến khi nút được nhấn
            wait_for_button_press()

            # NẾU ĐANG PHÁT NHẠC -> NHẤN NÚT LÀ TẮT NHẠC
            if youtube.is_playing():
                youtube.stop_video()
                print(">> 🛑 Đã tắt nhạc YouTube.")
                # Đợi người dùng nhả nút rồi quay lại vòng lặp chờ
                while not is_button_released():
                    time.sleep(0.05)
                continue

            print("\n>> 🔴 ĐANG THU ÂM... (Hãy nói, buông nút để kết thúc)")

            try:
                # 2. Bắt đầu thu âm và truyền hàm kiểm tra nút nhả vào
                wav_path = audio.record_to_file(
                    duration=60.0, # Giới hạn tối đa 60s để tránh dính nút
                    stop_condition=is_button_released # <--- YÊU CẦU CẬP NHẬT TRONG AUDIO_TRANSPORT
                )
                print(">> ⏳ Bạn đã buông nút. Đang nhận diện...")

                text = stt_func(wav_path)

                try:
                    if os.path.exists(wav_path):
                        os.remove(wav_path)
                except OSError:
                    pass

                if text:
                    print(f"🗣️ Bạn nói: '{text}'")
                    if text.lower() in ['exit', 'quit', 'thoát', 'tạm biệt']:
                        print("Tạm biệt! Hệ thống đang tắt...")
                        break
                    text_to_process = text
                else:
                    print(">> ⚠️ Không nghe thấy chữ nào. Đang quay lại trạng thái chờ...")
                    time.sleep(0.5)
                    continue 

            except Exception as e:
                print(f">> ❌ Lỗi thu âm: {e}")
                time.sleep(1)
                continue

            # 3. Xử lý AI
            if text_to_process:
                print("🧠 Đang suy nghĩ...")
                start = time.time()
                
                # Check nhanh Intent trước khi chạy Full RAG
                rewritten, intent = rag._get_intent_classifier().process(text_to_process, memory)
                
                if intent == IntentType.YOUTUBE_PLAY:
                    speak("Dạ, Mẹ đợi em một chút để mở nhạc nhé.")
                    video_id, title = youtube.search_video(rewritten)
                    if video_id:
                        youtube.play_video(video_id)
                        print(f"🎵 Đang phát: {title}")
                    else:
                        speak("Dạ, em không tìm thấy bài hát này ạ.")
                    continue

                response, safety = rag.process_query(text_to_process, memory)
                elapsed = time.time() - start

                if safety and safety.is_emergency:
                    print("\n🚨 [CẢNH BÁO KHẨN CẤP] 🚨")

                speak(response)
                print(f"[⏱️ Thời gian xử lý: {elapsed:.2f}s]")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nTạm biệt!")
    except Exception as e:
        print(f"\n❌ Đã xảy ra lỗi hệ thống: {e}")
    finally:
        audio.close()

if __name__ == "__main__":
    setup_logging()
    main()
    os._exit(0)