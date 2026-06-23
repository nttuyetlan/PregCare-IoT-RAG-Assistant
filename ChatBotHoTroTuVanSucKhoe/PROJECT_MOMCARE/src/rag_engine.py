"""
src/rag_engine.py — RAG Engine with Dual LLM Architecture

PURPOSE:
    Core retrieval-augmented generation engine. Queries ChromaDB for
    relevant medical context, then generates responses using Qwen 7B.
    Integrates safety checker for emergency override.

ARCHITECTURE DECISIONS:
    - ChromaDB query with trimester filter for precision
    - Safety check BEFORE LLM generation (saves latency on emergencies)
    - Streaming token generation for TTS pipeline
    - Strict system prompt prevents hallucination
    - Regex cleanup of <think> tags before output
"""

import re
from typing import Generator, Optional

from loguru import logger

from src.config import (
    get_settings,
    MEDICAL_SYSTEM_PROMPT,
    PROJECT_ROOT,
)
from src.conversation_memory import ConversationMemory
from src.intent_classifier import IntentClassifier, IntentType
from src.safety_checker import SafetyChecker, SafetyResult
from src.firebase import FirebaseService
from src.utils import Timer, clean_llm_output


class RAGEngine:
    """
    The heart of Mầm Nhỏ: retrieval + generation pipeline.

    Flow:
    1. IntentClassifier (Qwen 1.5B) → rewrite + classify
    2. ChromaDB → retrieve relevant medical docs
    3. SafetyChecker → red flag detection
    4. If emergency → return hardcoded message (skip LLM)
    5. If normal → Qwen 7B generates response from context
    """

    def __init__(self):
        self._settings = get_settings()
        self._intent_classifier = None
        self._safety_checker = SafetyChecker()
        self._chroma_collection = None
        self._vectorizer = None
        self._bm25 = None
        self._corpus_ids = []
        self._corpus_docs = []
        self._corpus_metas = []
        self._llm_7b = None
        self._firebase = FirebaseService()

    # ── Lazy Initialization ──────────────────

    def _get_collection(self):
        """Lazy-load ChromaDB collection."""
        if self._chroma_collection is None:
            import chromadb
            from sklearn.feature_extraction.text import HashingVectorizer

            db_path = self._settings.abs_vector_db_path
            
            self._vectorizer = HashingVectorizer(
                n_features=768,
                analyzer='word',
                ngram_range=(1, 2),
                lowercase=True,
                norm='l2',
                alternate_sign=False,
            )

            client = chromadb.PersistentClient(path=str(db_path))
            self._chroma_collection = client.get_collection(
                name=self._settings.chroma_collection_name
            )
            logger.info(
                f"ChromaDB loaded: {self._chroma_collection.count()} docs"
            )

            # --- Build BM25 Index in memory ---
            all_data = self._chroma_collection.get()
            if all_data and all_data.get('documents'):
                from rank_bm25 import BM25Okapi
                self._corpus_ids = all_data['ids']
                self._corpus_docs = all_data['documents']
                self._corpus_metas = all_data['metadatas']
                
                # Tokenize simple
                tokenized_corpus = [doc.lower().split() for doc in self._corpus_docs]
                self._bm25 = BM25Okapi(tokenized_corpus)
                logger.info("BM25 index built successfully for Hybrid Search")

        return self._chroma_collection

    def _get_llm_7b(self):
        """Lazy-load Qwen 1.5B (Fast Mode) cho RAG generation."""
        if self._llm_7b is None:
            from llama_cpp import Llama

            # SỬ DỤNG BẢN 1.5B THAY VÌ 7B ĐỂ TĂNG TỐC ĐỘ CHẠY TRÊN CPU
            model_path = self._settings.abs_qwen_1_5b_path
            logger.info(f"Loading Qwen 1.5B for RAG from {model_path}")

            gguf_files = list(model_path.glob("*.gguf"))
            if not gguf_files:
                raise FileNotFoundError(
                    f"No .gguf file found in {model_path}"
                )

            self._llm_7b = Llama(
                model_path=str(gguf_files[0]),
                n_ctx=2048,        # Giảm context window để tiết kiệm RAM
                n_threads=4,       # Orange Pi 5 có 8 cores, dùng 4 cho LLM
                n_gpu_layers=0,    # CPU only
                verbose=False,
            )
            logger.info("Qwen 1.5B loaded successfully for RAG")

        return self._llm_7b

    def _get_intent_classifier(self):
        """Lazy-load IntentClassifier sharing the same LLM instance."""
        if self._intent_classifier is None:
            # Truyền chung một model Qwen 1.5B để tiết kiệm 50% RAM, chống Segfault
            self._intent_classifier = IntentClassifier(llm_client=self._get_llm_7b())
        return self._intent_classifier

    def preload(self):
        """Pre-load tất cả model nặng lúc khởi động để request đầu tiên nhanh."""
        logger.info("⏳ Đang pre-load models (ChromaDB, SBERT, Qwen 1.5B)...")
        with Timer("Pre-load all models", log_level="INFO"):
            self._get_collection()       # Load ChromaDB + SBERT embedding
            self._get_llm_7b()           # Load Qwen 1.5B
            self._get_intent_classifier()  # Init IntentClassifier
        logger.info("✅ Tất cả model đã sẵn sàng!")

    # ── ChromaDB Retrieval ───────────────────

    def retrieve(
        self,
        query: str,
        trimester: Optional[int] = None,
        top_k: Optional[int] = None,
    ) -> dict:
        """
        Query ChromaDB for relevant medical documents.

        Args:
            query: Search query (rewritten by Qwen 1.5B)
            trimester: Filter by pregnancy trimester (0=all, 1-3)
            top_k: Number of results to return

        Returns:
            ChromaDB query results dict with documents, metadatas,
            distances
        """
        if top_k is None:
            top_k = self._settings.top_k_results

        collection = self._get_collection()

        # Build where filter for trimester
        where_filter = None
        if trimester and trimester in (1, 2, 3):
            # Match specific trimester OR trimester=0 (applies to all)
            where_filter = {
                "$or": [
                    {"trimester": trimester},
                    {"trimester": 0},
                ]
            }

        with Timer("Hybrid retrieval (Vector + BM25)", log_level="INFO"):
            fetch_k = top_k * 2
            
            # 1. Vector Search (ChromaDB)
            q_emb = self._vectorizer.transform([query]).toarray().astype('float32').tolist()
            chroma_results = collection.query(
                query_embeddings=q_emb,
                n_results=fetch_k,
                where=where_filter,
            )
            
            chroma_ranks = {}
            if chroma_results.get("ids") and chroma_results["ids"][0]:
                for rank, doc_id in enumerate(chroma_results["ids"][0], start=1):
                    chroma_ranks[doc_id] = rank
            
            # 2. Lexical Search (BM25)
            bm25_ranks = {}
            if self._bm25:
                tokenized_query = query.lower().split()
                bm25_scores = self._bm25.get_scores(tokenized_query)
                
                import numpy as np
                bm25_top_indices = np.argsort(bm25_scores)[::-1][:fetch_k]
                
                bm25_rank = 1
                for idx in bm25_top_indices:
                    doc_id = self._corpus_ids[idx]
                    meta = self._corpus_metas[idx]
                    
                    # Manual filter for BM25
                    if trimester and trimester in (1, 2, 3):
                        t = meta.get("trimester", 0)
                        if t != 0 and t != trimester:
                            continue
                            
                    bm25_ranks[doc_id] = bm25_rank
                    bm25_rank += 1
            
            # 3. Reciprocal Rank Fusion (RRF)
            k_rrf = 60
            rrf_scores = {}
            all_candidate_ids = set(chroma_ranks.keys()).union(set(bm25_ranks.keys()))
            
            for doc_id in all_candidate_ids:
                score = 0.0
                if doc_id in chroma_ranks:
                    score += 1.0 / (k_rrf + chroma_ranks[doc_id])
                if doc_id in bm25_ranks:
                    score += 1.0 / (k_rrf + bm25_ranks[doc_id])
                rrf_scores[doc_id] = score
                
            # Sort and take top_k
            sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
            
            final_docs = []
            final_metas = []
            for doc_id, _ in sorted_candidates:
                idx = self._corpus_ids.index(doc_id)
                final_docs.append(self._corpus_docs[idx])
                final_metas.append(self._corpus_metas[idx])
                
            results = {
                "documents": [final_docs],
                "metadatas": [final_metas]
            }

        n_results = len(results["documents"][0]) if results["documents"] else 0
        logger.info(f"Retrieved {n_results} chunks via Hybrid Search")

        return results

    # ── LLM Generation ───────────────────────

    def generate(
        self,
        query: str,
        context_docs: list[str],
    ) -> str:
        """
        Generate a medical response using Qwen with RAG context.
        """
        # Build context section
        context = "\n\n---\n\n".join(context_docs)

        # Build the full prompt using ChatML format for Qwen
        full_prompt = (
            f"<|im_start|>system\n"
            f"{MEDICAL_SYSTEM_PROMPT}\n\n"
            f"TÀI LIỆU THAM KHẢO:\n{context}"
        )
        
        full_prompt += f"<|im_end|>\n<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"

        with Timer("Qwen generation", log_level="INFO"):
            llm = self._get_llm_7b()
            response = llm(
                full_prompt,
                max_tokens=150,       # Giảm để trả lời ngắn gọn, nhanh hơn cho TTS
                temperature=0.3,      # Low creativity, high factuality
                top_p=0.9,
                stop=["<|im_end|>", "<|im_start|>"],
            )

            raw_text = response["choices"][0]["text"]

        # Clean for TTS
        cleaned = clean_llm_output(raw_text)

        logger.bind(conversation=True).info(
            f"GENERATED | query='{query[:60]}' | "
            f"response='{cleaned[:100]}...'"
        )

        return cleaned

    def generate_stream(
        self,
        query: str,
        context_docs: list[str],
    ) -> Generator[str, None, None]:
        """
        Stream tokens from Qwen for real-time TTS.
        """
        context = "\n\n---\n\n".join(context_docs)

        full_prompt = (
            f"<|im_start|>system\n"
            f"{MEDICAL_SYSTEM_PROMPT}\n\n"
            f"TÀI LIỆU THAM KHẢO:\n{context}"
        )
            
        full_prompt += f"<|im_end|>\n<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"

        llm = self._get_llm_7b()
        buffer = ""
        in_think_tag = False

        for token_data in llm(
            full_prompt,
            max_tokens=150,
            temperature=0.3,
            top_p=0.9,
            stop=["<|im_end|>", "<|im_start|>"],
            stream=True,
        ):
            token = token_data["choices"][0]["text"]

            # Filter out <think> tags in streaming mode
            if "<think>" in token:
                in_think_tag = True
                continue
            if "</think>" in token:
                in_think_tag = False
                continue
            if in_think_tag:
                continue

            buffer += token

            # Yield at punctuation boundaries for streaming TTS
            if re.search(r"[.!?;,]\s*$", buffer):
                cleaned = clean_llm_output(buffer)
                if cleaned:
                    yield cleaned
                buffer = ""

        # Flush remaining buffer
        if buffer.strip():
            cleaned = clean_llm_output(buffer)
            if cleaned:
                yield cleaned

    # ── Main Pipeline ────────────────────────

    def process_query(
        self,
        user_input: str,
        memory: ConversationMemory,
        trimester: Optional[int] = None,
    ) -> tuple[str, SafetyResult]:
        """
        Complete query processing pipeline.
        """
        logger.bind(conversation=True).info(
            f"USER INPUT | '{user_input}'"
        )

        # QUAN TRỌNG: Tải ChromaDB (PyTorch) TRƯỚC Llama-cpp để tránh Segfault
        # trên Windows do đụng độ OpenMP runtime giữa 2 thư viện.
        self._get_collection()

        # Step 1: Preprocess (Qwen 1.5B)
        rewritten, intent = self._get_intent_classifier().process(
            user_input, memory
        )

        # Step 2: Check if this is a health data query
        if intent == IntentType.HEALTH_DATA_QUERY:
            logger.info("Intent=HEALTH_DATA_QUERY → Fetching Firebase data")
            with Timer("Firebase fetch", log_level="INFO"):
                health_summary = self._firebase.get_health_summary()
            
            if not health_summary or "KHÔNG THỂ" in health_summary:
                response = (
                    "Dạ, Mầm Nhỏ không thể lấy thông số sức khỏe lúc này. "
                    "Mẹ kiểm tra lại thiết bị đo nhé."
                )
            else:
                # Thay vì trả lời cứng, hãy dùng LLM để lọc thông tin mẹ cần
                health_context = [
                    f"DỮ LIỆU SỨC KHỎE THỰC TẾ TỪ THIẾT BỊ ĐO: {health_summary}\n"
                    f"YÊU CẦU BẮT BUỘC: Dựa vào số liệu trên, hãy trả lời câu hỏi của mẹ thành một câu nói hoàn chỉnh, tự nhiên. Bắt đầu bằng chữ 'Dạ', xưng 'em' hoặc 'Mầm Nhỏ' và gọi 'mẹ'. Tuyệt đối KHÔNG được chỉ đọc mỗi con số cộc lốc."
                ]
                response = self.generate(
                    query=user_input, 
                    context_docs=health_context
                )
            
            memory.add_user_message(user_input)
            memory.add_assistant_message(response)
            return response, SafetyResult(is_emergency=False)

        # Step 3: Retrieve from ChromaDB (for KNOWLEDGE_QUERY, SELF_SYMPTOM, STORY_TELLING)
        results = self.retrieve(rewritten, trimester=trimester)

        # Extract documents and metadatas
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []

        # Step 4: Safety check
        safety = self._safety_checker.check_rag_results(
            intent=intent,
            query=rewritten,
            rag_metadatas=metas,
        )

        # Step 5: Emergency override — SKIP Qwen 7B
        if safety.is_emergency:
            logger.bind(conversation=True).critical(
                f"EMERGENCY OVERRIDE | type={safety.emergency_type}"
            )
            # Update memory with the emergency exchange
            memory.add_user_message(user_input)
            memory.add_assistant_message(safety.emergency_message)
            return safety.emergency_message, safety

        # Step 6: Normal generation (Qwen 7B)
        if not docs:
            response = (
                "Dạ, Mầm Nhỏ chưa có thông tin về vấn đề này trong tài liệu. "
                "Mẹ nên hỏi bác sĩ sản khoa để được tư vấn chính xác "
                "nhất nhé."
            )
        else:
            response = self.generate(
                query=rewritten,
                context_docs=docs,
            )

        # Update conversation memory
        memory.add_user_message(user_input)
        memory.add_assistant_message(response)

        return response, safety

    def process_query_stream(
        self,
        user_input: str,
        memory: ConversationMemory,
        trimester: Optional[int] = None,
        kick_data: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Streaming version of process_query for real-time TTS.

        Yields text chunks at punctuation boundaries.
        Emergency messages are yielded as a single chunk.
        """
        logger.bind(conversation=True).info(
            f"USER INPUT (stream) | '{user_input}'"
        )

        # QUAN TRỌNG: Tải ChromaDB (PyTorch) TRƯỚC Llama-cpp để tránh Segfault
        self._get_collection()

        # Step 1: Preprocess
        rewritten, intent = self._get_intent_classifier().process(
            user_input, memory
        )

        # Step 2: Retrieve
        results = self.retrieve(rewritten, trimester=trimester)
        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []

        # Step 3: Safety check
        safety = self._safety_checker.check_rag_results(
            intent=intent, query=rewritten, rag_metadatas=metas
        )

        # Step 4: Emergency override
        if safety.is_emergency:
            memory.add_user_message(user_input)
            memory.add_assistant_message(safety.emergency_message)
            yield safety.emergency_message
            return

        # Step 5: Stream generation
        if not docs:
            fallback = (
                "Dạ, Mầm Nhỏ chưa có thông tin về vấn đề này trong tài liệu. "
                "Mẹ nên hỏi bác sĩ sản khoa để được tư vấn chính xác "
                "nhất nhé."
            )
            memory.add_user_message(user_input)
            memory.add_assistant_message(fallback)
            yield fallback
            return

        full_response = []
        for chunk in self.generate_stream(
            query=rewritten, context_docs=docs, kick_data=kick_data
        ):
            full_response.append(chunk)
            yield chunk

        # Update memory with full response
        memory.add_user_message(user_input)
        memory.add_assistant_message(" ".join(full_response))
