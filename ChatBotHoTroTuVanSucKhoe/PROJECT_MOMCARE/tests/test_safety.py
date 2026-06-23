"""
tests/test_safety.py — Safety Checker Unit Tests

Tests the critical medical safety layer:
- Red flag detection from ChromaDB metadata
- Keyword-based emergency detection
- Intent-based filtering (STORY vs SELF_SYMPTOM)
- Emergency message selection
"""

import pytest
from src.safety_checker import SafetyChecker, SafetyResult
from src.intent_classifier import IntentType


@pytest.fixture
def checker():
    return SafetyChecker()


class TestRedFlagDetection:
    """Test ChromaDB metadata-based red flag detection."""

    def test_self_symptom_with_red_flag_triggers_emergency(self, checker):
        """SELF_SYMPTOM + red_flag=true → emergency override."""
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Em đang bị chảy máu âm đạo",
            rag_metadatas=[{"red_flag": True, "trimester": 0}],
        )
        assert result.is_emergency is True
        assert result.emergency_message is not None
        assert len(result.emergency_message) > 0

    def test_story_telling_with_red_flag_no_emergency(self, checker):
        """STORY_TELLING + red_flag=true → NOT emergency (telling others' story)."""
        result = checker.check_rag_results(
            intent=IntentType.STORY_TELLING,
            query="Hàng xóm em bị ra máu phải đi cấp cứu",
            rag_metadatas=[{"red_flag": True, "trimester": 0}],
        )
        assert result.is_emergency is False

    def test_knowledge_query_with_red_flag_no_emergency(self, checker):
        """KNOWLEDGE_QUERY + red_flag=true → NOT emergency."""
        result = checker.check_rag_results(
            intent=IntentType.KNOWLEDGE_QUERY,
            query="Dấu hiệu chảy máu âm đạo nguy hiểm thế nào",
            rag_metadatas=[{"red_flag": True, "trimester": 0}],
        )
        assert result.is_emergency is False

    def test_self_symptom_no_red_flag_safe(self, checker):
        """SELF_SYMPTOM but no red_flag → normal processing."""
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Em bị ốm nghén nhẹ",
            rag_metadatas=[{"red_flag": False, "trimester": 1}],
        )
        assert result.is_emergency is False


class TestKeywordDetection:
    """Test keyword-based fallback emergency detection."""

    def test_bleeding_keywords(self, checker):
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Em đang bị chảy máu nhiều quá",
            rag_metadatas=[],  # No ChromaDB results
        )
        assert result.is_emergency is True
        assert result.emergency_type == "bleeding"

    def test_no_movement_keywords(self, checker):
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Bé không đạp gì cả từ sáng tới giờ",
            rag_metadatas=[],
        )
        assert result.is_emergency is True
        assert result.emergency_type == "no_movement"

    def test_severe_pain_keywords(self, checker):
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Em bị đau bụng dữ dội không chịu nổi",
            rag_metadatas=[],
        )
        assert result.is_emergency is True
        assert result.emergency_type == "severe_pain"

    def test_normal_symptom_no_emergency(self, checker):
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Em bị ốm nghén buồn nôn buổi sáng",
            rag_metadatas=[],
        )
        assert result.is_emergency is False

    def test_water_break_keywords(self, checker):
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Em bị ra nước âm đạo nhiều lắm",
            rag_metadatas=[],
        )
        assert result.is_emergency is True
        assert result.emergency_type == "water_break"

    def test_preeclampsia_keywords(self, checker):
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Em bị đau đầu dữ dội và nhìn mờ",
            rag_metadatas=[],
        )
        assert result.is_emergency is True
        assert result.emergency_type == "preeclampsia"


class TestEmergencyMessages:
    """Test that emergency messages are hardcoded, not generated."""

    def test_emergency_message_contains_115(self, checker):
        """Emergency messages must include emergency number."""
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Em đang bị chảy máu âm đạo",
            rag_metadatas=[{"red_flag": True, "trimester": 0}],
        )
        assert "115" in result.emergency_message or "bệnh viện" in result.emergency_message

    def test_emergency_message_warns_no_self_medication(self, checker):
        """Emergency messages must warn against self-medication."""
        result = checker.check_rag_results(
            intent=IntentType.SELF_SYMPTOM,
            query="Em đang bị chảy máu",
            rag_metadatas=[{"red_flag": True, "trimester": 0}],
        )
        assert "không" in result.emergency_message.lower() and "thuốc" in result.emergency_message.lower()
