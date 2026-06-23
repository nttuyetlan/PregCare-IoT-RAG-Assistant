"""
src/intent_classifier.py — Few-Shot Intent Classification (Qwen 1.5B)

PURPOSE:
    Classifies user utterances into 3 categories using Qwen-2.5-1.5B
    with few-shot prompting. This is critical for preventing false
    red-flag alerts (e.g., "my neighbor had bleeding" ≠ emergency).

CATEGORIES:
    - STORY_TELLING: Telling stories about others' experiences
    - KNOWLEDGE_QUERY: Asking general medical knowledge questions
    - SELF_SYMPTOM: Describing their own current symptoms (→ red flag scan)

ARCHITECTURE DECISIONS:
    - Few-shot prompting (5 examples) instead of fine-tuning
    - Runs on Qwen 1.5B for speed (~20-30 tok/s on ARM64)
    - Falls back to KNOWLEDGE_QUERY if classification is ambiguous
    - Also handles query rewriting for context-dependent questions
"""

import re
from enum import Enum
from typing import Optional

from loguru import logger

from src.config import (
    get_settings,
    INTENT_CLASSIFICATION_PROMPT,
    QUERY_REWRITE_PROMPT,
)
from src.conversation_memory import ConversationMemory
from src.utils import Timer


class IntentType(str, Enum):
    """Four intent categories for obstetric conversation."""
    STORY_TELLING = "STORY_TELLING"
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    SELF_SYMPTOM = "SELF_SYMPTOM"
    HEALTH_DATA_QUERY = "HEALTH_DATA_QUERY"
    YOUTUBE_PLAY = "YOUTUBE_PLAY"


class IntentClassifier:
    """
    Intent classification and query rewriting using Qwen-2.5-1.5B.

    This is the FIRST stage in the Dual LLM pipeline:
    1. Rewrite query with conversation context
    2. Classify intent (3-class)

    Both tasks use the lightweight 1.5B model for speed.
    """

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: Pre-initialized LLM client for Qwen 1.5B.
                        If None, will be initialized on first call.
        """
        self._llm = llm_client
        self._settings = get_settings()

    def _get_llm(self):
        """Lazy-load LLM client to avoid import-time overhead."""
        if self._llm is None:
            from llama_cpp import Llama

            model_path = self._settings.abs_qwen_1_5b_path
            logger.info(f"Loading Qwen 1.5B from {model_path}")

            # Find the GGUF file in the model directory
            gguf_files = list(model_path.glob("*.gguf"))
            if not gguf_files:
                raise FileNotFoundError(
                    f"No .gguf file found in {model_path}"
                )

            self._llm = Llama(
                model_path=str(gguf_files[0]),
                n_ctx=2048,       # Small context window (sufficient)
                n_threads=4,      # ARM64 multi-thread
                n_gpu_layers=0,   # CPU only on Orange Pi 5
                verbose=False,
            )
            logger.info("Qwen 1.5B loaded successfully")

        return self._llm

    def classify_intent(self, user_input: str) -> IntentType:
        """
        Classify user utterance into one of 3 intent categories.

        Uses few-shot prompting with 5 examples to guide the 1.5B
        model toward correct classification.

        Args:
            user_input: The user's transcribed speech

        Returns:
            IntentType enum value
        """
        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            user_input=user_input
        )

        with Timer("Intent classification", log_level="INFO"):
            try:
                llm = self._get_llm()
                response = llm(
                    prompt,
                    max_tokens=10,     # Only need one word
                    temperature=0.0,   # Deterministic
                    stop=["\n", " "],  # Stop at newline or space
                )

                raw_output = response["choices"][0]["text"].strip().upper()
                logger.debug(f"Raw intent output: '{raw_output}'")

                # Parse the classification
                return self._parse_intent(raw_output)

            except Exception as e:
                logger.error(f"Intent classification failed: {e}")
                # Safe fallback: treat as knowledge query (no red flag)
                return IntentType.KNOWLEDGE_QUERY

    def _parse_intent(self, raw_output: str) -> IntentType:
        """
        Parse LLM output into IntentType with fuzzy matching.

        Handles cases where the model outputs extra text.
        """
        raw = raw_output.upper().strip()

        # Direct match
        for intent in IntentType:
            if intent.value in raw:
                return intent

        # Fuzzy keyword matching
        if any(kw in raw for kw in ["YOUTUBE", "BÀI HÁT", "PHÁT NHẠC", "NGHE NHẠC", "MỞ NHẠC", "HÁT", "BẬT NHẠC"]):
            return IntentType.YOUTUBE_PLAY
        if any(kw in raw for kw in ["STORY", "KỂ", "HÀNG XÓM", "CHỊ GÁI"]):
            return IntentType.STORY_TELLING
        if any(kw in raw for kw in ["SELF", "TRIỆU CHỨNG", "EM BỊ", "EM ĐANG"]):
            return IntentType.SELF_SYMPTOM
        if any(kw in raw for kw in ["HEALTH", "DATA", "THÔNG SỐ", "NHIỆT ĐỘ", "NHỊP TIM", "SPO2", "CẢNH BÁO", "SỨC KHỎE"]):
            return IntentType.HEALTH_DATA_QUERY

        # Default fallback
        logger.warning(
            f"Could not parse intent from '{raw_output}', "
            f"defaulting to KNOWLEDGE_QUERY"
        )
        return IntentType.KNOWLEDGE_QUERY

    def rewrite_query(
        self,
        current_query: str,
        memory: ConversationMemory,
    ) -> str:
        """
        Rewrite user query with conversation context for better retrieval.

        Example:
            History: "Mẹ: Em có thai 3 tháng"
            Query: "Nên ăn gì?"
            Rewritten: "Mang thai 3 tháng đầu nên ăn gì?"

        Args:
            current_query: Latest user utterance
            memory: Conversation memory with recent history

        Returns:
            Rewritten query with full context, or original if
            no rewriting needed.
        """
        # Skip rewriting if no history or query is already self-contained
        if memory.is_empty or len(current_query) > 15:
            return current_query

        history_text = memory.get_history_text()
        prompt = QUERY_REWRITE_PROMPT.format(
            history=history_text,
            current_query=current_query,
        )

        with Timer("Query rewriting", log_level="INFO"):
            try:
                llm = self._get_llm()
                response = llm(
                    prompt,
                    max_tokens=100,
                    temperature=0.0,
                    stop=["\n"],
                )

                rewritten = response["choices"][0]["text"].strip()

                # Sanity check — don't use if output is garbage
                if len(rewritten) < 3 or len(rewritten) > 500:
                    logger.warning(
                        f"Rewrite output suspicious (len={len(rewritten)}), "
                        f"using original query"
                    )
                    return current_query

                logger.info(
                    f"Query rewritten: '{current_query}' → '{rewritten}'"
                )
                return rewritten

            except Exception as e:
                logger.error(f"Query rewriting failed: {e}")
                return current_query

    def process(
        self,
        user_input: str,
        memory: ConversationMemory,
    ) -> tuple[str, IntentType]:
        """
        Full preprocessing pipeline: rewrite + classify.

        This is the main entry point called by the voice pipeline.

        Args:
            user_input: Raw transcribed user speech
            memory: Conversation memory

        Returns:
            Tuple of (rewritten_query, intent_type)
        """
        # FAST PATH: Bỏ qua LLM hoàn toàn nếu có keyword đặc trưng (tiết kiệm 0.7s)
        user_lower = user_input.lower()
        if any(kw in user_lower for kw in ["mở nhạc", "phát nhạc", "bài hát", "nghe nhạc", "mở bài", "hát", "bật nhạc", "youtube"]):
            logger.info(f"⚡ Fast path: YOUTUBE_PLAY → '{user_input}'")
            return user_input, IntentType.YOUTUBE_PLAY
            
        if any(kw in user_lower for kw in ["nhiệt độ", "nhịp tim", "spo2", "oxy", "chỉ số", "đo sức"]):
            logger.info(f"⚡ Fast path: HEALTH_DATA_QUERY → '{user_input}'")
            return user_input, IntentType.HEALTH_DATA_QUERY
            
        if any(kw in user_lower for kw in ["kể chuyện", "đọc truyện", "ru ngủ"]):
            logger.info(f"⚡ Fast path: STORY_TELLING → '{user_input}'")
            return user_input, IntentType.STORY_TELLING
            
        if any(kw in user_lower for kw in ["đau", "sốt", "khó thở", "chảy máu", "ra máu", "chóng mặt", "mệt"]):
            logger.info(f"⚡ Fast path: SELF_SYMPTOM → '{user_input}'")
            return user_input, IntentType.SELF_SYMPTOM

        # Step 1: Rewrite query with context
        rewritten = self.rewrite_query(user_input, memory)

        # Step 2: Classify intent
        intent = self.classify_intent(rewritten)

        logger.info(
            f"Preprocessed: intent={intent.value}, "
            f"query='{rewritten[:80]}...'"
        )

        return rewritten, intent
