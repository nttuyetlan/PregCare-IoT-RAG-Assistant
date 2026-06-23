"""
src/safety_checker.py — Medical Safety & Red Flag Override

PURPOSE:
    Implements the critical safety layer that detects dangerous
    symptoms and overrides LLM generation with hardcoded emergency
    messages. This ensures NO hallucination in life-threatening cases.

ARCHITECTURE DECISIONS:
    - Emergency messages are loaded from safety_rules.json.
    - Only triggers for SELF_SYMPTOM intent (not STORY_TELLING).
    - Python code override — bypasses Qwen 7B entirely.
"""

import json
from dataclasses import dataclass
from typing import Optional

from loguru import logger

from src.config import PROJECT_ROOT
from src.intent_classifier import IntentType


@dataclass
class SafetyResult:
    """Result of a safety check on user input + retrieved context."""
    is_emergency: bool
    emergency_message: Optional[str] = None
    emergency_type: Optional[str] = None
    matched_keywords: list[str] = None

    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []


class SafetyChecker:
    """
    Medical safety layer.
    
    Reads `data/extracted/safety_rules.json` to detect keywords
    such as 'chảy máu', 'đau bụng dữ dội', etc.
    """

    def __init__(self):
        rules_path = PROJECT_ROOT / 'data' / 'extracted' / 'safety_rules.json'
        if rules_path.exists():
            self.rules = json.loads(rules_path.read_text(encoding='utf-8')).get('rules', [])
            logger.info(f"Loaded {len(self.rules)} safety rules from {rules_path.name}")
        else:
            self.rules = []
            logger.warning(f"Safety rules file not found at {rules_path}")

    def check_rag_results(
        self,
        intent: IntentType,
        query: str,
        rag_metadatas: list[dict] | None = None,
    ) -> SafetyResult:
        """
        Check if RAG results + user intent indicate an emergency.

        Args:
            intent: Classified intent from Qwen 1.5B
            query: The user's (possibly rewritten) query
            rag_metadatas: Metadata dicts from ChromaDB results (ignored in new logic, but kept for compatibility)

        Returns:
            SafetyResult with is_emergency flag and message if needed
        """
        # Only trigger emergency for SELF_SYMPTOM intent
        if intent != IntentType.SELF_SYMPTOM:
            logger.debug(
                f"Intent is {intent.value}, skipping emergency check"
            )
            return SafetyResult(is_emergency=False)

        low = query.lower()
        matches = []
        for r in self.rules:
            if any(k.lower() in low for k in r['keywords']):
                matches.append(r)
        
        if not matches:
            logger.debug("Safety check passed — no emergency detected")
            return SafetyResult(is_emergency=False)

        # Sort matches by severity (emergency > urgent > warning)
        order = {'emergency': 0, 'urgent': 1, 'warning': 2}
        matches.sort(key=lambda x: order.get(x['level'], 9))

        best_match = matches[0]
        
        logger.bind(conversation=True).critical(
            f"🚨 SAFETY RULE TRIGGERED | "
            f"level={best_match['level']} | "
            f"id={best_match['id']} | "
            f"query='{query[:100]}'"
        )

        return SafetyResult(
            is_emergency=True,
            emergency_message=best_match['response_template'],
            emergency_type=best_match['id'],
            matched_keywords=best_match['keywords'],
        )

    @staticmethod
    def get_emergency_disclaimer() -> str:
        """
        Return a standard medical disclaimer to append to normal
        (non-emergency) responses.
        """
        return (
            "Lưu ý: Mầm Nhỏ chỉ cung cấp thông tin tham khảo, "
            "không thay thế tư vấn y khoa chuyên nghiệp. "
            "Nếu có bất kỳ lo lắng nào, Mẹ hãy liên hệ bác sĩ nhé."
        )
