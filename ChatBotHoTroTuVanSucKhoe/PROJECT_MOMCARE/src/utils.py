"""
src/utils.py — Shared Utility Functions for Mầm Nhỏ

PURPOSE:
    Reusable helper functions used across multiple modules.
    Includes text cleaning, timing decorators, JSONL parsing,
    and medical text sanitization.
"""

import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Generator

from loguru import logger


# ── 1. JSONL File Operations ─────────────────

def load_jsonl(file_path: str | Path) -> list[dict[str, Any]]:
    """Load a JSONL file and return list of parsed dicts."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {file_path}")

    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON at line {line_num}: {e}")

    logger.info(f"Loaded {len(records)} records from {file_path}")
    return records


def stream_jsonl(file_path: str | Path) -> Generator[dict[str, Any], None, None]:
    """Stream JSONL records one at a time (memory-efficient)."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def validate_jsonl_schema(record: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate a single JSONL record against the required schema.
    Required: text (str), metadata (dict with trimester, topic, red_flag).
    """
    if "text" not in record or not isinstance(record["text"], str):
        return False, "Missing or invalid 'text' field"
    if not record["text"].strip():
        return False, "'text' must be non-empty"

    meta = record.get("metadata")
    if not isinstance(meta, dict):
        return False, "Missing or invalid 'metadata' dict"

    required = {"trimester": int, "topic": str, "red_flag": bool}
    for field, ftype in required.items():
        if field not in meta:
            return False, f"Missing metadata.{field}"
        if not isinstance(meta[field], ftype):
            return False, f"metadata.{field} must be {ftype.__name__}"

    if meta["trimester"] not in (0, 1, 2, 3):
        return False, f"Invalid trimester: {meta['trimester']}"
    return True, ""


# ── 2. Text Processing ───────────────────────

def clean_llm_output(text: str) -> str:
    """
    Clean LLM output for TTS consumption.
    Removes markdown, emoji, XML tags, excess whitespace.
    """
    if not text:
        return ""
    # Remove <think>...</think> tags
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"</?think>", "", text)
    # Remove markdown
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove emoji
    emoji_pat = re.compile(
        "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0\U000024C2-\U0001F251]+",
        flags=re.UNICODE,
    )
    text = emoji_pat.sub("", text)
    # Remove list markers
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-•*]\s+", "", text, flags=re.MULTILINE)
    # Normalize whitespace
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def validate_response_content(text: str) -> str:
    """
    Validate and sanitize LLM output to prevent hallucinated responses.
    
    This catches known problematic outputs like:
    - Video creation offers (not related to obstetric care)
    - Channel subscriptions (off-topic)
    - Malformed or nonsensical responses
    
    Returns the cleaned response or replacement if hallucination detected.
    """
    if not text:
        return text
    
    # List of problematic patterns that indicate hallucination
    bad_patterns = [
        # Video creation / channel subscription nonsense
        r"tạo.*video.*kênh",  # "create video for channel"
        r"subscribe.*ghiền",  # YouTube channel name
        r"ghiền mì gõ",  # Specific YouTube channel
        r"rất tiếc.*không thể tiếp tục.*video",  # "sorry can't continue... video"
        r"đoạn video hấp dẫn",  # "attractive video segment"
        r"mầm nhỏ.*giúp.*video",  # "Mầm Nhỏ help create video"
        # Other clearly off-topic
        r"dự án.*không.*liên quan",  # "unrelated project"
        r"đã lâu.*mọi người.*subscribe",  # "long time... everyone subscribe"
    ]
    
    text_lower = text.lower()
    for pattern in bad_patterns:
        if re.search(pattern, text_lower):
            logger.warning(
                f"Detected hallucinated response pattern: {pattern[:50]}... "
                f"Text: {text[:100]}..."
            )
            # Return the proper "no information" message
            return (
                "Dạ, Mầm Nhỏ chưa có thông tin về vấn đề này trong tài liệu. "
                "Mẹ nên hỏi bác sĩ sản khoa để được tư vấn chính xác nhất nhé."
            )
    
    return text


def split_at_punctuation(text: str) -> list[str]:
    """Split text at sentence boundaries for streaming TTS."""
    if not text:
        return []
    segments = re.split(r"(?<=[.!?;,])\s+", text)
    return [s.strip() for s in segments if s.strip() and len(s.strip()) > 1]


def normalize_vietnamese(text: str) -> str:
    """Normalize Vietnamese text (NFC, remove BOM/zero-width)."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    return text.strip()


# ── 3. Performance Utilities ─────────────────

class Timer:
    """Context manager for timing code blocks with auto-logging."""

    def __init__(self, operation_name: str, log_level: str = "DEBUG"):
        self.operation_name = operation_name
        self.log_level = log_level
        self.elapsed = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self._start
        getattr(logger, self.log_level.lower())(
            f"⏱ {self.operation_name}: {self.elapsed:.3f}s"
        )


def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except ImportError:
        try:
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024
        except (FileNotFoundError, ValueError):
            return 0.0
    return 0.0
