"""
tests/test_rag.py — RAG Engine Unit Tests

Tests data validation, text processing, and conversation memory.
These tests run WITHOUT models (no LLM/GPU required).
"""

import pytest
from src.utils import (
    validate_jsonl_schema,
    clean_llm_output,
    split_at_punctuation,
    normalize_vietnamese,
)
from src.conversation_memory import ConversationMemory


class TestJSONLValidation:
    """Test JSONL schema validation."""

    def test_valid_record(self):
        record = {
            "text": "CẨM NANG THAI KỲ: THEO DÕI CỬ ĐỘNG THAI. Thai máy xuất hiện vào khoảng tháng thứ 5.",
            "metadata": {
                "trimester": 0,
                "topic": "thai_may",
                "red_flag": True,
            },
        }
        is_valid, error = validate_jsonl_schema(record)
        assert is_valid is True
        assert error == ""

    def test_missing_text(self):
        record = {"metadata": {"trimester": 1, "topic": "dinh_duong", "red_flag": False}}
        is_valid, _ = validate_jsonl_schema(record)
        assert is_valid is False

    def test_missing_metadata(self):
        record = {"text": "Hello"}
        is_valid, _ = validate_jsonl_schema(record)
        assert is_valid is False

    def test_invalid_trimester(self):
        record = {
            "text": "Test",
            "metadata": {"trimester": 5, "topic": "dinh_duong", "red_flag": False},
        }
        is_valid, error = validate_jsonl_schema(record)
        assert is_valid is False
        assert "trimester" in error.lower()

    def test_red_flag_record(self):
        record = {
            "text": "CẨM NANG THAI KỲ: RA MÁU ÂM ĐẠO TRONG THAI KỲ. Ra máu âm đạo trong thời gian mang thai.",
            "metadata": {
                "trimester": 0,
                "topic": "ra_mau_am_dao",
                "red_flag": True,
            },
        }
        is_valid, _ = validate_jsonl_schema(record)
        assert is_valid is True

    def test_trimester_zero_valid(self):
        """trimester=0 means applies to all trimesters."""
        record = {
            "text": "CẨM NANG THAI KỲ: DINH DƯỠNG CHO BÀ BẦU.",
            "metadata": {
                "trimester": 0,
                "topic": "dinh_duong",
                "red_flag": False,
            },
        }
        is_valid, _ = validate_jsonl_schema(record)
        assert is_valid is True


class TestTextCleaning:
    """Test LLM output cleaning for TTS."""

    def test_remove_think_tags(self):
        text = "<think>Let me think...</think>Dạ, chị ơi."
        assert clean_llm_output(text) == "Dạ, chị ơi."

    def test_remove_markdown_bold(self):
        text = "Chị nên **uống nước** nhiều hơn."
        assert "**" not in clean_llm_output(text)

    def test_remove_numbered_lists(self):
        text = "1. Uống nước\n2. Ăn rau\n3. Nghỉ ngơi"
        cleaned = clean_llm_output(text)
        assert "1." not in cleaned

    def test_empty_input(self):
        assert clean_llm_output("") == ""
        assert clean_llm_output(None) == ""


class TestPunctuationSplit:
    """Test text splitting for streaming TTS."""

    def test_split_at_period(self):
        text = "Câu một. Câu hai. Câu ba."
        segments = split_at_punctuation(text)
        assert len(segments) >= 2

    def test_split_at_comma(self):
        text = "Đầu tiên, chị nên nghỉ ngơi. Sau đó, uống nước."
        segments = split_at_punctuation(text)
        assert len(segments) >= 2

    def test_empty_input(self):
        assert split_at_punctuation("") == []


class TestConversationMemory:
    """Test sliding window conversation memory."""

    def test_basic_add_and_retrieve(self):
        mem = ConversationMemory(window_size=3)
        mem.add_user_message("Xin chào")
        mem.add_assistant_message("Dạ, chị ơi!")
        assert mem.turn_count == 1
        assert len(mem) == 2

    def test_window_overflow(self):
        mem = ConversationMemory(window_size=2)
        # Add 3 turns (exceeds window of 2)
        for i in range(3):
            mem.add_user_message(f"Câu hỏi {i}")
            mem.add_assistant_message(f"Trả lời {i}")
        # Should only keep last 2 turns (4 messages)
        assert len(mem) == 4
        history = mem.get_history_text()
        assert "Câu hỏi 0" not in history
        assert "Câu hỏi 2" in history

    def test_clear(self):
        mem = ConversationMemory(window_size=3)
        mem.add_user_message("Test")
        mem.clear()
        assert mem.is_empty

    def test_history_format(self):
        mem = ConversationMemory(window_size=3)
        mem.add_user_message("Xin chào")
        mem.add_assistant_message("Dạ, chào chị!")
        history = mem.get_history_text()
        assert "Mẹ: Xin chào" in history
        assert "Mầm Nhỏ: Dạ, chào chị!" in history


class TestVietnameseNormalization:
    """Test Vietnamese text normalization."""

    def test_nfc_normalization(self):
        text = "Xin chào"  # Already NFC
        assert normalize_vietnamese(text) == "Xin chào"

    def test_remove_bom(self):
        text = "\ufeffXin chào"
        assert normalize_vietnamese(text) == "Xin chào"

    def test_empty(self):
        assert normalize_vietnamese("") == ""
