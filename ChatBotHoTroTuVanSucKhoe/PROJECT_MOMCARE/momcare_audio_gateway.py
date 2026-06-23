"""
momcare_audio_gateway.py — WebSocket Gateway kết nối ESP32-S3 với Chatbot Mầm Nhỏ

PURPOSE:
    Nhận audio stream trực tiếp từ ESP32-S3 qua mạng Wi-Fi (WebSocket), xử lý qua pipeline AI:
    Raw PCM (ESP32) → WAV → STT → RAG → TTS → WAV bytes → ESP32 (Speaker)

ARCHITECTURE:
    - Luồng 1 (Asyncio Thread): Chạy WebSocket Server lắng nghe kết nối từ ESP32
    - Luồng 2 (Main Thread):    Pipeline AI xử lý audio → text → audio đồng bộ
    - Queue kết nối:            event_queue chứa chunk âm thanh và lệnh điều khiển
"""

import os
import time
import wave
import queue
import threading
import asyncio
import websockets

from loguru import logger

# ── Import ChatBot Components ────────────────────
from src.config import get_settings, setup_logging, PROJECT_ROOT
from src.stt_service import STTService
from src.rag_engine import RAGEngine
from src.tts_service import TTSService
from src.conversation_memory import ConversationMemory
from src.utils import Timer, get_memory_usage_mb
from src.youtube_service import YouTubeService
from src.intent_classifier import IntentType

# ── Cấu hình audio từ ESP32 ─────────────────────
ESP32_SAMPLE_RATE = 16000
ESP32_CHANNELS = 1
ESP32_SAMPLE_WIDTH = 2  # 16-bit = 2 bytes

# Hàng đợi đa năng kết nối 2 luồng
event_queue = queue.Queue()

# Biến global lưu trữ event loop và danh sách client đang kết nối
ws_loop = asyncio.new_event_loop()
connected_clients = set()


def save_pcm_to_wav(pcm_data: bytes, wav_path: str) -> str:
    """Chuyển raw PCM bytes từ ESP32 thành file WAV chuẩn."""
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(ESP32_CHANNELS)
        wf.setsampwidth(ESP32_SAMPLE_WIDTH)
        wf.setframerate(ESP32_SAMPLE_RATE)
        wf.writeframes(pcm_data)
    return wav_path


# --- LUỒNG 1: MÁY CHỦ WEBSOCKET LẮNG NGHE ESP32 ---
async def ws_handler(websocket):
    """Xử lý từng kết nối client (ESP32) ném tới."""
    connected_clients.add(websocket)
    client_ip = websocket.remote_address[0]
    logger.info(f"🟢 ESP32 đã kết nối từ IP: {client_ip}")
    event_queue.put({"type": "command", "data": "CONNECTED"})
    
    is_recording = False
    
    try:
        async for message in websocket:
            # Nếu nhận được lệnh dạng Text ([WAKE] / [START] / [STOP])
            if isinstance(message, str):
                if message == "[WAKE]":
                    event_queue.put({"type": "command", "data": "WAKE"})
                elif message == "[START]":
                    event_queue.put({"type": "command", "data": "START"})
                    is_recording = True
                elif message == "[STOP]":
                    event_queue.put({"type": "command", "data": "STOP"})
                    is_recording = False
            
            # Nếu nhận được dữ liệu dạng Binary (Âm thanh thô)
            elif isinstance(message, bytes):
                if is_recording and len(message) > 0:
                    event_queue.put({"type": "audio", "data": message})
                    
    except websockets.exceptions.ConnectionClosed as e:
        logger.warning(f"🟡 Mất kết nối đột ngột với ESP32: {e}")
    finally:
        connected_clients.remove(websocket)
        logger.info(f"🔴 ESP32 ({client_ip}) đã ngắt kết nối")


async def start_ws_server():
    """Khởi động WebSocket Server tại cổng 8765"""
    async with websockets.serve(ws_handler, "0.0.0.0", 8765):
        logger.info("🌐 WebSocket Server đang chạy tại ws://0.0.0.0:8765")
        logger.info("   (Đang chờ ESP32 kết nối qua Wi-Fi...)")
        await asyncio.Future()  # Chạy mãi mãi


def run_asyncio_loop(loop):
    """Hàm cầu nối để chạy asyncio event loop bên trong một Thread riêng biệt"""
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_ws_server())


def send_audio_to_esp32(audio_bytes: bytes):
    """
    Hàm gọi từ luồng Main AI để ném âm thanh về lại ESP32.
    Sử dụng threadsafe để giao tiếp ngược với luồng Asyncio.
    """
    if not connected_clients:
        logger.warning("⚠️ Không có ESP32 nào đang kết nối để gửi audio!")
        return

    async def broadcast_audio(data):
        # Gửi file nhị phân đồng loạt cho các client (thường chỉ có 1 ESP32)
        await asyncio.gather(*[client.send(data) for client in connected_clients])

    # Ném tác vụ gửi mạng vào luồng asyncio
    asyncio.run_coroutine_threadsafe(broadcast_audio(audio_bytes), ws_loop)
    logger.info(f"📤 Đã bắn {len(audio_bytes)} bytes audio về ESP32 qua Wi-Fi")


# --- LUỒNG 2: XỬ LÝ CHATBOT (Giữ nguyên kiến trúc của bạn) ---
def chatbot_pipeline():
    try:
        setup_logging()
    except PermissionError:
        print("⚠️ Không có quyền ghi log file. Chạy với console logging...\n")
    
    logger.info("=" * 60)
    logger.info("🌱 Mầm Nhỏ — Wi-Fi WebSocket Audio Gateway + ChatBot Pipeline")
    logger.info(f"📊 RAM ban đầu: {get_memory_usage_mb():.1f}MB")
    logger.info("=" * 60)
    
    stt = STTService()
    rag = RAGEngine()
    tts = TTSService()
    memory = ConversationMemory()
    youtube = YouTubeService()
    
    # Pre-load tất cả model nặng lúc khởi động
    rag.preload()
    tts._resolve_model()  # Pre-load Piper TTS model
    
    # Google Speech Recognition (Online - Chính xác cao cho tiếng Việt)
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    
    def stt_google_from_wav(wav_path: str) -> str:
        """Dùng Google Speech Recognition (miễn phí) để nhận diện giọng nói."""
        try:
            with sr.AudioFile(wav_path) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="vi-VN")
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            logger.warning(f"Google STT lỗi mạng ({e}), chuyển sang Whisper offline...")
            return None  # None = cần fallback sang Whisper
    
    tmp_dir = PROJECT_ROOT / "logs"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    audio_buffer = bytearray()
    ignore_current_session = False
    
    def play_audio_sync(wav_file: str):
        """Hàm dùng chung để đảm bảo phát âm thanh luôn thành công ra loa."""
        import subprocess
        played = False
        for dev in ["default", "plughw:2,0"]:
            if subprocess.run(["aplay", "-D", dev, wav_file], capture_output=True).returncode == 0:
                played = True
                break
        if not played:
            if subprocess.run(["paplay", wav_file], capture_output=True).returncode == 0:
                played = True
        return played
    
    print("📡 STT: Google Speech Recognition (Online) + Whisper (Fallback)\n")
    
    # Bỏ thông báo ở đây, chuyển xuống chờ ESP32 kết nối
    
    last_wake_time = 0
    
    while True:
        event = event_queue.get()
        
        if event["type"] == "audio":
            audio_buffer.extend(event["data"])
            
        elif event["type"] == "command":
            cmd = event["data"]
            if cmd == "CONNECTED":
                # PHÁT ÂM THANH THÔNG BÁO KHI ESP32 KẾT NỐI
                try:
                    ready_text = "Mầm Nhỏ đã kết nối thành công, sẵn sàng lắng nghe."
                    print(f"  🔊 Đang phát thông báo: '{ready_text}'")
                    ready_audio = tts.synthesize(ready_text)
                    if ready_audio and len(ready_audio) > 44:
                        ready_wav = os.path.join(str(tmp_dir), "ready.wav")
                        with open(ready_wav, "wb") as f:
                            f.write(ready_audio)
                        play_audio_sync(ready_wav)
                except Exception as e:
                    logger.error(f"Lỗi phát thông báo sẵn sàng: {e}")
                    print(f"  ⚠️ Lỗi phát thông báo sẵn sàng: {e}")
            elif cmd == "WAKE":
                if youtube.is_playing():
                    youtube.stop_video()
                    print(">> 🛑 Đã tắt nhạc YouTube.")
                    ignore_current_session = True
                    continue
                    
                # KIỂM TRA THỜI GIAN ĐỂ TÁCH BIỆT "CHÀO" VÀ "GHI ÂM"
                current_time = time.time()
                if current_time - last_wake_time < 10:
                    # Mẹ đang bấm lần 2 để ghi âm -> Bỏ qua lời chào để khỏi đè giọng
                    continue
                    
                print("\n👋 Mẹ vừa nhấn nút! Phát lời chào...")
                try:
                    greeting = "Chào mẹ, Mầm Nhỏ sẵn sàng lắng nghe."
                    greeting_audio = tts.synthesize(greeting)
                    if greeting_audio and len(greeting_audio) > 44:
                        tts_wav = os.path.join(str(tmp_dir), "greeting.wav")
                        with open(tts_wav, "wb") as f:
                            f.write(greeting_audio)
                        play_audio_sync(tts_wav)
                        print("  🌱 Mầm Nhỏ: Chào mẹ! Nhấn nút lần nữa rồi nói nhé.")
                    else:
                        print("  ⚠️ Không tạo được lời chào.")
                        
                    # Cập nhật thời gian chào
                    last_wake_time = time.time()
                    
                    # Dọn dẹp Hàng đợi (Queue) để vứt bỏ lệnh START/STOP rác sinh ra lúc mẹ thả nút lần 1
                    while not event_queue.empty():
                        try:
                            event_queue.get_nowait()
                        except queue.Empty:
                            break
                            
                except Exception as e:
                    logger.error(f"Greeting error: {e}")
                    print(f"  ⚠️ Lỗi phát lời chào: {e}")
            
            elif cmd == "START":
                if youtube.is_playing():
                    youtube.stop_video()
                    print(">> 🛑 Đã tắt nhạc YouTube.")
                    ignore_current_session = True
                    continue
                
                # Nếu vừa tắt nhạc ở WAKE, bỏ qua phiên ghi âm này
                if ignore_current_session:
                    continue
                    
                print("\n🎤 [Mẹ đang nói...]")
                audio_buffer.clear()
                
            elif cmd == "STOP":
                if ignore_current_session:
                    print("⏹️  [Đã thả nút] (Bỏ qua xử lý âm thanh vì vừa bấm tắt nhạc)")
                    ignore_current_session = False
                    audio_buffer.clear()
                    continue
                    
                pcm_size = len(audio_buffer)
                duration_sec = pcm_size / (ESP32_SAMPLE_RATE * ESP32_SAMPLE_WIDTH * ESP32_CHANNELS)
                print(f"⏹️  [Đã thả nút] Nhận {pcm_size} bytes ({duration_sec:.1f}s) qua Wi-Fi")
                
                if pcm_size < 3200:
                    print("  ⚠️ Audio quá ngắn, bỏ qua.")
                    try:
                        short_msg = "Dạ âm thanh hơi ngắn, mẹ vui lòng ấn giữ nút để nói lại nhé."
                        short_audio = tts.synthesize(short_msg)
                        if short_audio and len(short_audio) > 44:
                            short_wav = os.path.join(str(tmp_dir), "short.wav")
                            with open(short_wav, "wb") as f:
                                f.write(short_audio)
                            play_audio_sync(short_wav)
                    except Exception as e:
                        print(f"  ⚠️ Lỗi phát thông báo audio ngắn: {e}")
                    
                    audio_buffer.clear()
                    continue
                
                mem_before = get_memory_usage_mb()
                
                try:
                    # ── Step 1: Lưu PCM → WAV ────────────────────────
                    wav_path = os.path.join(str(tmp_dir), "esp32_input.wav")
                    save_pcm_to_wav(bytes(audio_buffer), wav_path)
                    print(f"  💾 Đã lưu WAV: {wav_path}")
                    
                    # ── Step 2: STT (Google Online → Whisper Fallback) ─
                    print("  ⏳ Đang nhận diện giọng nói (Google Online)...")
                    with Timer("STT", log_level="INFO"):
                        user_text = stt_google_from_wav(wav_path)
                        
                        # Nếu Google lỗi mạng (trả về None), dùng Whisper offline
                        if user_text is None:
                            print("  🔄 Chuyển sang Whisper offline...")
                            user_text = stt.transcribe(wav_path)
                    
                    try:
                        os.remove(wav_path)
                    except OSError:
                        pass
                    
                    if not user_text.strip():
                        print("  ⚠️ Không nghe rõ, Mẹ nói lại nhé.")
                        fallback_audio = tts.synthesize("Dạ, em không nghe rõ, Mẹ nói lại giúp em nhé.")
                        if fallback_audio:
                            fallback_wav = os.path.join(str(tmp_dir), "fallback.wav")
                            with open(fallback_wav, "wb") as f:
                                f.write(fallback_audio)
                            play_audio_sync(fallback_wav)
                        audio_buffer.clear()
                        continue
                    
                    print(f"  🗣️ Mẹ nói: \"{user_text}\"")
                    
                    # ── Step 3: Intent Check & RAG ───────────────────
                    print("  🧠 Đang suy nghĩ...")
                    
                    rewritten, intent = rag._get_intent_classifier().process(user_text, memory)
                    
                    if intent == IntentType.YOUTUBE_PLAY:
                        tts_text = "Dạ, Mẹ đợi em một chút để mở nhạc nhé."
                        print(f"  🌱 Mầm Nhỏ: \"{tts_text}\"")
                        
                        # TRẢ LỜI NGAY LẬP TỨC (Đồng bộ)
                        # Phải phát xong câu này mới mở Chromium, vì ALSA card không cho chạy đè 2 âm thanh cùng lúc
                        tts_wav = os.path.join(str(tmp_dir), "ack_music.wav")
                        if not os.path.exists(tts_wav):
                            resp_audio = tts.synthesize(tts_text)
                            if resp_audio:
                                with open(tts_wav, "wb") as f:
                                    f.write(resp_audio)
                        
                        if os.path.exists(tts_wav):
                            play_audio_sync(tts_wav)
                        
                        # TÌM VÀ PHÁT YOUTUBE
                        video_id, title = youtube.search_video(rewritten)
                        if video_id:
                            youtube.play_video(video_id)
                            print(f"  🎵 Đang phát: {title}")
                        else:
                            not_found_text = "Dạ, em không tìm thấy bài hát này. Mẹ thử nói lại tên bài khác nhé."
                            print(f"  ⚠️ {not_found_text}")
                            not_found_audio = tts.synthesize(not_found_text)
                            if not_found_audio:
                                tts_wav2 = os.path.join(str(tmp_dir), "not_found.wav")
                                with open(tts_wav2, "wb") as f:
                                    f.write(not_found_audio)
                                play_audio_sync(tts_wav2)
                            
                        audio_buffer.clear()
                        continue

                    with Timer("RAG pipeline", log_level="INFO"):
                        response, safety = rag.process_query(
                            user_input=user_text,
                            memory=memory,
                            trimester=None,
                        )
                    
                    if safety and safety.is_emergency:
                        print("  🚨 [CẢNH BÁO KHẨN CẤP]")
                    
                    print(f"  🌱 Mầm Nhỏ: \"{response}\"")
                    
                    # ── Step 4: TTS ──────────────────────────────────
                    print("  🔊 Đang tổng hợp giọng nói...")
                    with Timer("TTS synthesis", log_level="INFO"):
                        response_audio = tts.synthesize(response)
                    
                    if response_audio and len(response_audio) > 44:
                        # 1. Lưu audio ra file
                        tts_wav = os.path.join(str(tmp_dir), "output_tts.wav")
                        with open(tts_wav, "wb") as f:
                            f.write(response_audio)
                        
                        # 2. Phát ra loa/tai nghe qua cổng 3.5mm (Card 2: es8388)
                        print(f"  📤 Đang phát ({len(response_audio)} bytes)...")
                        
                        played = play_audio_sync(tts_wav)
                        
                        if played:
                            print("  ✅ Hoàn tất!")
                        else:
                            print("  ❌ Không phát được audio qua bất kỳ thiết bị nào.")
                    else:
                        print("  ❌ TTS không tạo được audio.")
                    
                    mem_after = get_memory_usage_mb()
                    print(f"  [RAM: {mem_after:.1f}MB (Δ{mem_after - mem_before:+.1f}MB) | Memory: {memory.turn_count} turns]\n")
                
                except Exception as e:
                    logger.error(f"Pipeline error: {e}")
                    print(f"  ❌ Lỗi pipeline: {e}\n")
                
                finally:
                    audio_buffer.clear()


if __name__ == "__main__":
    # Khởi chạy luồng 1 (WebSocket Server) ở chế độ chạy ngầm
    ws_thread = threading.Thread(target=run_asyncio_loop, args=(ws_loop,), daemon=True)
    ws_thread.start()

    # Khởi chạy luồng 2 (AI Pipeline) trên luồng chính
    chatbot_pipeline()