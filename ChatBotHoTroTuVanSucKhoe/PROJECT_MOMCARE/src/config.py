"""
src/config.py — Centralized Configuration for Mầm Nhỏ

PURPOSE:
    Single source of truth for all environment variables, file paths,
    model names, and logging configuration. Every module imports from
    here instead of hardcoding values.

ARCHITECTURE DECISION:
    - Uses pydantic-settings for type-safe env var parsing
    - Loguru replaces stdlib logging for structured audit trails
    - All paths are resolved relative to PROJECT_ROOT for portability
"""

import os
import sys
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from loguru import logger


# ──────────────────────────────────────────────
# 1. Resolve project root (one level up from src/)
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ──────────────────────────────────────────────
# 2. Settings class — parsed from .env or env vars
# ──────────────────────────────────────────────
class AppSettings(BaseSettings):
    """
    All configurable parameters for the Mầm Nhỏ system.
    Values are read from .env file or environment variables.
    """

    # --- Model Paths ---
    qwen_1_5b_model_path: str = Field(
        default="models/qwen2.5-1.5b",
        description="Path to Qwen-2.5-1.5B weights (relative to PROJECT_ROOT)"
    )
    qwen_7b_model_path: str = Field(
        default="models/qwen2.5-7b-instruct",
        description="Path to Qwen-2.5-7B-Instruct weights (relative to PROJECT_ROOT)"
    )
    whisper_model_path: str = Field(
        default="models/faster-whisper-small",
        description="Path to Faster-Whisper small model"
    )
    piper_model_path: str = Field(
        default="models/piper-vi",
        description="Path to Piper TTS Vietnamese model"
    )
    sbert_model_path: str = Field(
        default="models/vietnamese-sbert",
        description="Path to Vietnamese-SBERT embedding model"
    )

    # --- Database ---
    vector_db_path: str = Field(
        default="data/chroma_db",
        description="ChromaDB persistent storage directory"
    )
    sqlite_db_path: str = Field(
        default="data/kick_counter.db",
        description="SQLite database for kick counter time-series"
    )
    data_jsonl_path: str = Field(
        default="data/thai_ky_data.jsonl",
        description="Path to curated medical JSONL data"
    )

    # --- Server ---
    kick_counter_port: int = Field(
        default=8001,
        description="FastAPI port for ESP32 kick counter"
    )
    voice_pipeline_port: int = Field(
        default=8000,
        description="Voice pipeline WebSocket port"
    )

    # --- Voice Pipeline ---
    vad_silence_timeout_ms: int = Field(
        default=1800,
        description="SileroVAD silence timeout in ms (long for pregnant women breathing)"
    )
    whisper_compute_type: str = Field(
        default="int8",
        description="CTranslate2 compute type for Faster-Whisper"
    )
    whisper_num_threads: int = Field(
        default=4,
        description="Number of CPU threads for Whisper inference"
    )

    # --- Audio Hardware (Orange Pi 5 / es8388) ---
    audio_input_device_index: int = Field(
        default=-1,
        description="PyAudio input device index (-1 = system default). Run scripts/check_audio.py to find."
    )
    audio_output_device_index: int = Field(
        default=-1,
        description="PyAudio output device index (-1 = system default). Run scripts/check_audio.py to find."
    )
    audio_stt_sample_rate: int = Field(
        default=16000,
        description="Sample rate for STT recording (Whisper requires 16kHz)"
    )
    audio_silence_timeout: float = Field(
        default=2.5,
        description="Seconds of silence before auto-stop recording"
    )
    audio_silence_threshold: int = Field(
        default=500,
        description="Amplitude threshold for silence detection (lower = more sensitive)"
    )

    # --- RAG ---
    chroma_collection_name: str = Field(
        default="momcare_knowledge_hashing",
        description="ChromaDB collection name"
    )
    top_k_results: int = Field(
        default=3,
        description="Number of top results to retrieve from vector DB"
    )
    memory_window_size: int = Field(
        default=3,
        description="Conversation memory sliding window size (turns)"
    )

    # --- Firebase Realtime Database ---
    firebase_db_url: str = Field(
        default="",
        description="Firebase Realtime Database URL"
    )
    firebase_device_id: str = Field(
        default="demo_device_001",
        description="Device ID trong Firebase để lấy thông số sức khỏe"
    )
    firebase_secret: str = Field(
        default="",
        description="Firebase Database Secret (Dùng để vượt qua lỗi 401 Permission Denied)"
    )

    # --- YouTube ---
    youtube_api_key: str = Field(
        default="",
        description="YouTube Data API v3 key cho tính năng mở nhạc"
    )

    # --- Logging ---
    log_dir: str = Field(
        default="logs",
        description="Directory for audit log files"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_rotation: str = Field(
        default="10 MB",
        description="Log file rotation size"
    )

    model_config = ConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars
    )

    # --- Resolved Absolute Paths ---
    def get_abs_path(self, relative_path: str) -> Path:
        """Resolve a relative path against PROJECT_ROOT."""
        return PROJECT_ROOT / relative_path

    @property
    def abs_vector_db_path(self) -> Path:
        return self.get_abs_path(self.vector_db_path)

    @property
    def abs_data_jsonl_path(self) -> Path:
        return self.get_abs_path(self.data_jsonl_path)

    @property
    def abs_sqlite_db_path(self) -> Path:
        return self.get_abs_path(self.sqlite_db_path)

    @property
    def abs_log_dir(self) -> Path:
        return self.get_abs_path(self.log_dir)

    @property
    def abs_qwen_1_5b_path(self) -> Path:
        return self.get_abs_path(self.qwen_1_5b_model_path)

    @property
    def abs_qwen_7b_path(self) -> Path:
        return self.get_abs_path(self.qwen_7b_model_path)

    @property
    def abs_whisper_path(self) -> Path:
        return self.get_abs_path(self.whisper_model_path)

    @property
    def abs_piper_path(self) -> Path:
        return self.get_abs_path(self.piper_model_path)

    @property
    def abs_sbert_path(self) -> Path:
        return self.get_abs_path(self.sbert_model_path)


# ──────────────────────────────────────────────
# 3. Singleton settings instance
# ──────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached singleton settings instance."""
    return AppSettings()


# ──────────────────────────────────────────────
# 4. Logging setup
# ──────────────────────────────────────────────
def setup_logging(settings: AppSettings | None = None) -> None:
    """
    Configure Loguru for structured audit logging.

    Creates two sinks:
    - Console: colored, human-readable
    - File: JSON-structured, rotated, for legal audit trail

    This is critical for medical AI systems where every conversation
    must be traceable for legal compliance.
    """
    if settings is None:
        settings = get_settings()

    log_dir = settings.abs_log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    # Remove default stderr handler
    logger.remove()

    # Console sink — human-readable
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "{message}"
        ),
        colorize=True,
    )

    # File sink — JSON structured for audit trail
    logger.add(
        str(log_dir / "momcare_{time:YYYY-MM-DD}.log"),
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation=settings.log_rotation,
        retention="30 days",
        compression="gz",
        encoding="utf-8",
        serialize=False,  # Set True for pure JSON logs
    )

    # Conversation audit log — separate file for medical traceability
    logger.add(
        str(log_dir / "conversations_{time:YYYY-MM-DD}.log"),
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
        rotation=settings.log_rotation,
        retention="90 days",  # Medical records retention
        compression="gz",
        encoding="utf-8",
        filter=lambda record: "conversation" in record["extra"],
    )

    logger.info("Logging initialized", log_dir=str(log_dir))


# ──────────────────────────────────────────────
# 5. Medical safety constants (NOT configurable via env)
# ──────────────────────────────────────────────

# Emergency override message — hardcoded, NEVER generated by LLM
EMERGENCY_MESSAGES = {
    "default": (
        "Dạ, Mẹ ơi! Đây là dấu hiệu nguy hiểm cần được cấp cứu ngay. "
        "Mẹ tuyệt đối không tự ý uống thuốc. "
        "Xin Mẹ hãy gọi xe cấp cứu 115 hoặc đến bệnh viện sản khoa gần nhất ngay lập tức. "
        "Em rất lo cho Mẹ và bé."
    ),
    "bleeding": (
        "Dạ, Mẹ ơi! Chảy máu âm đạo trong thai kỳ là dấu hiệu rất nguy hiểm, "
        "có thể là dấu hiệu thai ngoài tử cung, sảy thai, rau tiền đạo hoặc rau bong non. "
        "Mẹ cần nằm nghỉ ngay ở tư thế đầu thấp, không đi lại nhiều, và gọi 115 hoặc nhờ người thân "
        "đưa đến bệnh viện sản khoa gần nhất ngay bây giờ. "
        "Tuyệt đối không tự ý uống thuốc nhé Mẹ."
    ),
    "no_movement": (
        "Dạ, Mẹ ơi! Nếu em bé giảm cử động đột ngột hoặc ít hơn 4 lần trong 2 giờ, "
        "Mẹ cần đến bệnh viện ngay để được theo dõi monitor thai. "
        "Trong lúc chờ, Mẹ hãy nằm nghiêng trái và uống một ly nước mát nhé. "
        "Em rất lo cho Mẹ và bé."
    ),
    "severe_pain": (
        "Dạ, Mẹ ơi! Đau bụng dữ dội trong thai kỳ có thể là dấu hiệu của "
        "thai ngoài tử cung, rau bong non, dọa sảy thai hoặc dọa sinh non. "
        "Mẹ cần đến cơ sở y tế ngay lập tức bằng phương tiện nhanh nhất. "
        "Tuyệt đối không tự ý uống thuốc giảm đau nhé Mẹ."
    ),
    "water_break": (
        "Dạ, Mẹ ơi! Ra nước âm đạo có thể là rỉ ối hoặc vỡ ối. "
        "Mẹ cần nằm ở tư thế đầu thấp để tránh sa dây rau, "
        "và đến cơ sở y tế ngay bằng phương tiện nhanh nhất. "
        "Em rất lo cho Mẹ và bé."
    ),
    "preeclampsia": (
        "Dạ, Mẹ ơi! Đau đầu dữ dội kèm nhìn mờ hoặc phù nặng "
        "có thể là dấu hiệu của tiền sản giật, một biến chứng rất nguy hiểm. "
        "Mẹ cần đến cơ sở y tế ngay để được đo huyết áp và xét nghiệm kịp thời. "
        "Tuyệt đối không chủ quan nhé Mẹ."
    ),
}

# System prompt for Qwen 7B — strict medical RAG behavior
MEDICAL_SYSTEM_PROMPT = """Bạn là "Mầm Nhỏ", trợ lý sản khoa AI ấm áp và đáng tin cậy.

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời dựa trên TÀI LIỆU THAM KHẢO được cung cấp bên dưới. Tuyệt đối KHÔNG bịa thông tin.
2. Nếu tài liệu không chứa câu trả lời, nói: "Dạ, Mầm Nhỏ chưa có thông tin về vấn đề này trong tài liệu. Mẹ nên hỏi bác sĩ sản khoa để được tư vấn chính xác nhất nhé."
3. Xưng hô: gọi thai phụ là "Mẹ", xưng "em" (Mầm Nhỏ). Giọng điệu ấm áp, nhẹ nhàng, quan tâm.
4. Không bao giờ chẩn đoán bệnh. Không bao giờ kê đơn thuốc. Luôn khuyên gặp bác sĩ khi cần.
5. Trả lời ngắn gọn, dễ hiểu, phù hợp nghe bằng tai (vì sẽ được đọc thành tiếng).
6. KHÔNG sử dụng markdown, emoji, hoặc ký tự đặc biệt trong câu trả lời.
7. Ưu tiên an toàn mẹ và bé trên hết."""

# Intent classification prompt for Qwen 1.5B
INTENT_CLASSIFICATION_PROMPT = """Phân loại câu nói của người dùng vào MỘT trong 4 nhóm sau.
Chỉ trả lời ĐÚNG MỘT từ: STORY_TELLING, KNOWLEDGE_QUERY, SELF_SYMPTOM, hoặc HEALTH_DATA_QUERY.

VÍ DỤ:
- "Hàng xóm em bị ra máu phải đi cấp cứu" -> STORY_TELLING
- "Mang thai 3 tháng đầu nên ăn gì?" -> KNOWLEDGE_QUERY
- "Em đang bị đau bụng dưới dữ dội quá" -> SELF_SYMPTOM
- "Mẹ gái em nói bị tiểu đường thai kỳ" -> STORY_TELLING
- "Thai nhi tuần 28 máy bao nhiêu lần là bình thường?" -> KNOWLEDGE_QUERY
- "Em bị chảy máu âm đạo" -> SELF_SYMPTOM
- "Lịch khám thai định kỳ như thế nào?" -> KNOWLEDGE_QUERY
- "Chị em bị tiền sản giật phải nhập viện" -> STORY_TELLING
- "Em thấy đau đầu và nhìn mờ" -> SELF_SYMPTOM
- "Siêu âm thai lần đầu nên làm khi nào?" -> KNOWLEDGE_QUERY
- "Nhiệt độ của em bao nhiêu?" -> HEALTH_DATA_QUERY
- "Nhịp tim em hôm nay thế nào?" -> HEALTH_DATA_QUERY
- "SpO2 có bình thường không?" -> HEALTH_DATA_QUERY
- "Sức khỏe em hôm nay ra sao?" -> HEALTH_DATA_QUERY
- "Có cảnh báo gì không?" -> HEALTH_DATA_QUERY
- "Thông số đo của em thế nào?" -> HEALTH_DATA_QUERY

CÂU NÓI CẦN PHÂN LOẠI: "{user_input}"

PHÂN LOẠI:"""

# Query rewrite prompt for Qwen 1.5B
QUERY_REWRITE_PROMPT = """Dựa vào lịch sử hội thoại dưới đây, viết lại câu hỏi cuối cùng thành câu đầy đủ chủ ngữ vị ngữ.
Chỉ trả lời câu đã viết lại, không giải thích.

LỊCH SỬ:
{history}

CÂU HỎI CUỐI: "{current_query}"

CÂU VIẾT LẠI:"""
