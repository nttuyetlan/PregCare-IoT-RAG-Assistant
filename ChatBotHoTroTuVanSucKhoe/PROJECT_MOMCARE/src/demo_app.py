"""
src/demo_app.py — Gradio Web Demo for Voice Chatbot Testing

PURPOSE:
    Giao diện web cho phép test chatbot Mầm Nhỏ bằng:
    - 🎤 Giọng nói (Microphone → STT → RAG → TTS → Speaker)
    - ⌨️  Văn bản (Chat trực tiếp)

    Chạy trên trình duyệt, không cần phần cứng đặc biệt.

USAGE:
    python -m src.demo_app
    → Mở trình duyệt tại http://localhost:7860

ARCHITECTURE:
    - Gradio: Giao diện web với mic input + chat
    - Faster-Whisper: STT (mic → text)
    - RAG Engine: Xử lý câu hỏi (text → response)
    - gTTS fallback: TTS cho development (text → audio)
"""

import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr
import numpy as np
from loguru import logger

from src.config import get_settings, setup_logging, PROJECT_ROOT as PROJ_ROOT
from src.conversation_memory import ConversationMemory
from src.utils import Timer, get_memory_usage_mb


# ──────────────────────────────────────────────
# Global State
# ──────────────────────────────────────────────
_rag_engine = None
_stt_service = None
_memory = ConversationMemory()
_trimester = 0  # Mặc định: tất cả giai đoạn


def get_rag_engine():
    """Lazy-load RAG engine (tải mô hình khi cần)."""
    global _rag_engine
    if _rag_engine is None:
        logger.info("Đang khởi tạo RAG Engine...")
        from src.rag_engine import RAGEngine
        _rag_engine = RAGEngine()
        logger.info("RAG Engine sẵn sàng!")
    return _rag_engine


def get_stt():
    """Lazy-load STT service."""
    global _stt_service
    if _stt_service is None:
        logger.info("Đang khởi tạo STT (Faster-Whisper)...")
        from src.stt_service import STTService
        _stt_service = STTService()
        logger.info("STT sẵn sàng!")
    return _stt_service


def text_to_audio_response(text: str) -> str | None:
    """
    Chuyển text thành file audio để phát.
    Thử Piper TTS trước, fallback sang gTTS.

    Returns:
        Đường dẫn file audio tạm, hoặc None nếu thất bại
    """
    if not text:
        return None

    # Thử Piper TTS
    try:
        from src.tts_service import TTSService
        tts = TTSService()
        audio_bytes = tts.synthesize(text)
        if audio_bytes:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, dir=str(PROJ_ROOT / "logs")
            )
            tmp.write(audio_bytes)
            tmp.close()
            return tmp.name
    except Exception as e:
        logger.debug(f"Piper TTS không khả dụng: {e}")

    # Fallback: gTTS (cần internet)
    try:
        from gtts import gTTS
        tmp = tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False, dir=str(PROJ_ROOT / "logs")
        )
        tts = gTTS(text=text, lang="vi", slow=False)
        tts.save(tmp.name)
        logger.debug(f"gTTS audio saved: {tmp.name}")
        return tmp.name
    except Exception as e:
        logger.debug(f"gTTS fallback cũng thất bại: {e}")

    return None


# ──────────────────────────────────────────────
# Chat Handlers
# ──────────────────────────────────────────────

def handle_text_message(
    user_message: str,
    chat_history: list,
    trimester_choice: str,
) -> tuple:
    """
    Xử lý tin nhắn text từ người dùng.

    Returns:
        (updated_chat_history, audio_path, status_text)
    """
    global _memory, _trimester

    if not user_message.strip():
        return chat_history, None, "⚠️ Vui lòng nhập câu hỏi"

    # Parse trimester
    trimester_map = {
        "Tất cả giai đoạn": 0,
        "Tam cá nguyệt 1 (tuần 1-12)": 1,
        "Tam cá nguyệt 2 (tuần 13-26)": 2,
        "Tam cá nguyệt 3 (tuần 27-40)": 3,
    }
    _trimester = trimester_map.get(trimester_choice, 0)

    # Xử lý RAG
    start_time = time.perf_counter()

    try:
        rag = get_rag_engine()
        response, safety = rag.process_query(
            user_input=user_message,
            memory=_memory,
            trimester=_trimester if _trimester > 0 else None,
        )
    except Exception as e:
        logger.error(f"RAG error: {e}")
        response = f"Dạ, em gặp lỗi khi xử lý: {str(e)[:100]}"
        safety = None

    elapsed = time.perf_counter() - start_time

    # Cập nhật chat history (Gradio 5: messages format)
    chat_history.append({"role": "user", "content": user_message})

    # Thêm emoji cảnh báo nếu là emergency
    prefix = "🚨 " if (safety and safety.is_emergency) else ""
    chat_history.append({
        "role": "assistant",
        "content": f"{prefix}{response}",
    })

    # Tạo audio response
    audio_path = text_to_audio_response(response)

    # Status
    mem = get_memory_usage_mb()
    emergency_tag = " | ⚠️ EMERGENCY" if (safety and safety.is_emergency) else ""
    status = (
        f"⏱ {elapsed:.2f}s | 💾 RAM: {mem:.0f}MB | "
        f"🧠 Memory: {_memory.turn_count} turns{emergency_tag}"
    )

    return chat_history, audio_path, status


def handle_voice_message(
    audio_data,
    chat_history: list,
    trimester_choice: str,
) -> tuple:
    """
    Xử lý tin nhắn giọng nói: Mic → STT → RAG → TTS.

    Args:
        audio_data: Tuple (sample_rate, numpy_array) từ Gradio mic
        chat_history: Lịch sử hội thoại
        trimester_choice: Lựa chọn tam cá nguyệt

    Returns:
        (updated_chat_history, audio_path, transcribed_text, status)
    """
    if audio_data is None:
        return chat_history, None, "", "⚠️ Không nhận được audio"

    sample_rate, audio_array = audio_data

    # Lưu audio tạm để STT xử lý
    import soundfile as sf
    tmp_audio = tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, dir=str(PROJ_ROOT / "logs")
    )
    # Normalize audio
    if audio_array.dtype != np.float32:
        audio_array = audio_array.astype(np.float32)
    if audio_array.max() > 1.0:
        audio_array = audio_array / 32768.0
    # Đảm bảo mono
    if len(audio_array.shape) > 1:
        audio_array = audio_array.mean(axis=1)

    sf.write(tmp_audio.name, audio_array, sample_rate)
    tmp_audio.close()

    # STT: Audio → Text
    try:
        stt = get_stt()
        transcribed = stt.transcribe(tmp_audio.name, language="vi")
    except Exception as e:
        logger.error(f"STT error: {e}")
        return (
            chat_history, None, "",
            f"❌ Lỗi nhận diện giọng nói: {str(e)[:80]}"
        )

    if not transcribed.strip():
        return (
            chat_history, None, "",
            "⚠️ Không nghe rõ, vui lòng nói lại"
        )

    # Chuyển tiếp cho xử lý text
    updated_history, audio_path, status = handle_text_message(
        transcribed, chat_history, trimester_choice
    )

    return updated_history, audio_path, transcribed, f"🎤 STT: \"{transcribed}\" | {status}"


def reset_conversation():
    """Xóa bộ nhớ hội thoại."""
    global _memory
    _memory = ConversationMemory()
    return [], None, "", "🔄 Đã xóa bộ nhớ hội thoại"


# ──────────────────────────────────────────────
# Gradio UI
# ──────────────────────────────────────────────
# CSS tùy chỉnh cho Gradio UI
CUSTOM_CSS = """
.gradio-container {
    max-width: 900px !important;
    margin: auto !important;
}
.header-text {
    text-align: center;
    padding: 20px;
}
.status-bar {
    font-family: monospace;
    font-size: 0.85em;
}
"""


def create_demo():
    """Tạo giao diện Gradio cho demo chatbot."""

    with gr.Blocks(
        title="🌱 Mầm Nhỏ — Trợ lý Sản khoa AI",
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(
            primary_hue="green",
            secondary_hue="emerald",
        ),
    ) as demo:

        # ── Header ──
        gr.Markdown(
            """
            # 🌱 Mầm Nhỏ — Trợ lý Sản khoa AI
            ### Edge AI Obstetric Virtual Assistant

            Chào Mẹ! Em là Mầm Nhỏ, trợ lý sản khoa AI.
            Mẹ có thể hỏi em bằng **giọng nói** 🎤 hoặc **văn bản** ⌨️

            ---
            """,
            elem_classes="header-text",
        )

        with gr.Row():
            # ── Cột trái: Settings ──
            with gr.Column(scale=1):
                trimester = gr.Dropdown(
                    choices=[
                        "Tất cả giai đoạn",
                        "Tam cá nguyệt 1 (tuần 1-12)",
                        "Tam cá nguyệt 2 (tuần 13-26)",
                        "Tam cá nguyệt 3 (tuần 27-40)",
                    ],
                    value="Tất cả giai đoạn",
                    label="🤰 Giai đoạn thai kỳ",
                    info="Chọn để lọc thông tin phù hợp",
                )

                reset_btn = gr.Button(
                    "🔄 Xóa hội thoại",
                    variant="secondary",
                    size="sm",
                )

                status_text = gr.Textbox(
                    label="📊 Trạng thái",
                    interactive=False,
                    elem_classes="status-bar",
                    lines=2,
                )

                audio_output = gr.Audio(
                    label="🔊 Phản hồi giọng nói",
                    type="filepath",
                    autoplay=True,
                )

            # ── Cột phải: Chat ──
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="💬 Hội thoại với Mầm Nhỏ",
                    height=450,
                    type="messages",
                    show_copy_button=True,
                )

                # Tab cho Text và Voice input
                with gr.Tabs():
                    with gr.Tab("⌨️ Văn bản"):
                        with gr.Row():
                            text_input = gr.Textbox(
                                placeholder="Nhập câu hỏi... (VD: Mang thai 3 tháng đầu nên ăn gì?)",
                                label="",
                                lines=1,
                                scale=4,
                            )
                            send_btn = gr.Button(
                                "Gửi 📤",
                                variant="primary",
                                scale=1,
                            )

                    with gr.Tab("🎤 Giọng nói"):
                        mic_input = gr.Audio(
                            sources=["microphone"],
                            type="numpy",
                            label="Nhấn nút 🎤 để thu âm, nói xong nhấn lại để dừng",
                        )
                        voice_btn = gr.Button(
                            "Gửi giọng nói 🎤",
                            variant="primary",
                        )
                        transcribed_text = gr.Textbox(
                            label="📝 Văn bản nhận diện được",
                            interactive=False,
                            lines=1,
                        )

        # ── Ví dụ câu hỏi ──
        gr.Markdown("### 💡 Ví dụ câu hỏi")
        gr.Examples(
            examples=[
                ["Mang thai 3 tháng đầu nên ăn gì?"],
                ["Lịch khám thai định kỳ như thế nào?"],
                ["Siêu âm thai lần đầu nên làm khi nào?"],
                ["Bổ sung sắt và axit folic quan trọng thế nào?"],
                ["Dấu hiệu tiền sản giật là gì?"],
                ["Em đang bị đau bụng dưới dữ dội"],
                ["Hàng xóm em bị ra máu phải đi cấp cứu, sao vậy ạ?"],
                ["Cách đếm cử động thai như thế nào?"],
            ],
            inputs=text_input,
            label="",
        )

        # ── Footer ──
        gr.Markdown(
            """
            ---
            > ⚠️ **Lưu ý**: Mầm Nhỏ chỉ cung cấp thông tin tham khảo,
            > không thay thế tư vấn y khoa chuyên nghiệp.
            > Nếu có bất kỳ lo lắng nào, hãy liên hệ bác sĩ.

            > 🔒 Mọi hội thoại được ghi log phục vụ audit y tế.
            """
        )

        # ── Event Handlers ──

        # Text input
        send_btn.click(
            fn=handle_text_message,
            inputs=[text_input, chatbot, trimester],
            outputs=[chatbot, audio_output, status_text],
        ).then(
            fn=lambda: "",
            outputs=text_input,
        )

        text_input.submit(
            fn=handle_text_message,
            inputs=[text_input, chatbot, trimester],
            outputs=[chatbot, audio_output, status_text],
        ).then(
            fn=lambda: "",
            outputs=text_input,
        )

        # Voice input
        voice_btn.click(
            fn=handle_voice_message,
            inputs=[mic_input, chatbot, trimester],
            outputs=[chatbot, audio_output, transcribed_text, status_text],
        )

        # Reset
        reset_btn.click(
            fn=reset_conversation,
            outputs=[chatbot, audio_output, transcribed_text, status_text],
        )

    return demo


# ── Entry Point ──────────────────────────────

if __name__ == "__main__":
    setup_logging()

    logger.info("=" * 60)
    logger.info("🌱 Mầm Nhỏ — Khởi động Demo Gradio")
    logger.info("=" * 60)

    # Tạo thư mục logs nếu chưa có
    (PROJ_ROOT / "logs").mkdir(exist_ok=True)

    demo = create_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,       # Set True để tạo public URL
        show_error=True,
    )
